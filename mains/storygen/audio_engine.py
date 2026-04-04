import os
import re
import asyncio
import hashlib
import requests
import base64
import json
from gtts import gTTS
from django.conf import settings
from langdetect import detect
from moviepy.editor import AudioFileClip, concatenate_audioclips
from google import genai
from dotenv import load_dotenv
import edge_tts

load_dotenv()

# ---------------- CONFIG ---------------- #

BASE_AUDIO = os.path.join(settings.MEDIA_ROOT, "audio")
os.makedirs(BASE_AUDIO, exist_ok=True)

ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

# ---------------- VOICE MAP ---------------- #

VOICE_IDS = {
    "narrator": "Rachel",
    "male": "pNInz6obpgnuM0sLNojD",
    "female": "EXAVITQu4vr4xnSDxMaL",
}

#  FULL MULTILINGUAL SUPPORT
EDGE_VOICE_MAP = {
    "en": {"male": "en-IN-PrabhatNeural", "female": "en-IN-NeerjaNeural"},
    "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
    "mr": {"male": "mr-IN-ManoharNeural", "female": "mr-IN-AarohiNeural"},
    "ta": {"male": "ta-IN-ValluvarNeural", "female": "ta-IN-PallaviNeural"},
    "te": {"male": "te-IN-MohanNeural", "female": "te-IN-ShrutiNeural"},
    "bn": {"male": "bn-IN-BashkarNeural", "female": "bn-IN-TanishaaNeural"},
    "gu": {"male": "gu-IN-NiranjanNeural", "female": "gu-IN-DhwaniNeural"},
    "pa": {"male": "pa-IN-HarishNeural", "female": "pa-IN-GurleenNeural"},
}

# ---------------- LANGUAGE DETECTION ---------------- #

def detect_lang_safe(text):
    try:
        lang = detect(text)
        return lang
    except:
        pass

    if re.search(r"[ऀ-ॿ]", text): return "hi"
    if re.search(r"[অ-৿]", text): return "bn"
    if re.search(r"[அ-௿]", text): return "ta"
    if re.search(r"[అ-౿]", text): return "te"
    if re.search(r"[઀-૿]", text): return "gu"
    if re.search(r"[਀-੿]", text): return "pa"

    return "en"

# ---------------- AI STORY SPLIT ---------------- #

def is_valid_audio(path):
    try:
        if not os.path.exists(path):
            return False

        # size check
        if os.path.getsize(path) < 5000:
            return False

        # try opening file (REAL validation)
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        clip = AudioFileClip(path)
        duration = clip.duration
        clip.close()

        return duration > 0

    except Exception:
        return False

def simple_split(text):
    sentences = re.split(r'(?<=[.!?]) +', text)

    parts = []
    for s in sentences:
        if '"' in s:
            parts.append({
                "type": "dialogue",
                "role": "child",
                "gender": "female",
                "text": s
            })
        else:
            parts.append({
                "type": "narrator",
                "role": "narrator",
                "gender": "female",
                "text": s
            })
    return parts
# ---------------- VOICE SELECT ---------------- #

def get_voice(role, gender):

    if role == "narrator":
        return VOICE_IDS["narrator"]

    if role == "child":
        return VOICE_IDS["female"] if gender == "female" else VOICE_IDS["male"]

    if role == "old":
        return VOICE_IDS["male"] if gender == "male" else VOICE_IDS["female"]

    if gender == "male":
        return VOICE_IDS["male"]

    if gender == "female":
        return VOICE_IDS["female"]

    return VOICE_IDS["narrator"]


def detect_emotion(text):

    prompt = f"""
Analyze the emotion of this sentence.

Return ONLY one word:
happy / sad / angry / funny / neutral

Text:
{text}
"""

    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        ).text.strip().lower()

        if res in ["happy", "sad", "angry", "funny"]:
            return res

    except:
        pass

    return "neutral"

# ---------------- ELEVENLABS ---------------- #

def elevenlabs_tts(text, filepath, voice_id, emotion="neutral"):

    if not ELEVEN_KEY:
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": ELEVEN_KEY,
        "Content-Type": "application/json"
    }

    emotion_settings = {
    "happy": {"stability": 0.3, "style": 0.7},
    "sad": {"stability": 0.6, "style": 0.2},
    "angry": {"stability": 0.2, "style": 0.9},
    "funny": {"stability": 0.4, "style": 0.8},
    "neutral": {"stability": 0.4, "style": 0.3}
    }
    
    settings = emotion_settings.get(emotion, emotion_settings["neutral"])

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": settings["stability"],
            "similarity_boost": 0.85,
            "style": settings["style"]
}
    }

    try:
        res = requests.post(url, json=data, headers=headers)

        if res.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(res.content)
            if os.path.getsize(filepath) > 4000:
                return filepath
    except Exception as e:
        print("ElevenLabs error:", e)

    return None

# ---------------- GEMINI AUDIO ---------------- #

def gemini_audio(text, filepath):

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-preview-tts",
            contents=text,
            config={"response_modalities": ["AUDIO"]}
        )

        part = response.candidates[0].content.parts[0]

        if part.inline_data:
            audio_data = base64.b64decode(part.inline_data.data)

            with open(filepath, "wb") as f:
                f.write(audio_data)

            if os.path.getsize(filepath) > 2000:
                return filepath

    except Exception as e:
        print("Gemini error:", e)

    return None

# ---------------- EDGE TTS ---------------- #

async def edge_generate(text, filepath, gender="female", emotion="neutral"):

    lang = detect_lang_safe(text)
    voice_map = EDGE_VOICE_MAP.get(lang, EDGE_VOICE_MAP["en"])

    voice = voice_map.get(gender, voice_map["female"])

    # 🎭 FAKE EMOTION CONTROL
    rate_map = {
        "happy": "+10%",
        "sad": "-10%",
        "angry": "+15%",
        "funny": "+12%",
        "neutral": "0%"
    }

    pitch_map = {
        "happy": "+5Hz",
        "sad": "-5Hz",
        "angry": "+10Hz",
        "funny": "+8Hz",
        "neutral": "0Hz"
    }

    rate = rate_map.get(emotion, "0%")
    pitch = pitch_map.get(emotion, "0Hz")

    comm = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch
    )

    await comm.save(filepath)

    return filepath

# ---------------- gTTS ---------------- #

def gtts_generate(text, filepath):
    try:
        lang = detect_lang_safe(text)
        gTTS(text=text, lang=lang).save(filepath)
        return filepath
    except Exception as e:
        print("gTTS error:", e)
        return None

# ---------------- MAIN ENGINE ---------------- #

def generate_full_audio_sync(text):

    filename = f"story_{hashlib.md5(text.encode()).hexdigest()}.mp3"
    final_path = os.path.join(BASE_AUDIO, filename)

    if os.path.exists(final_path):
        return final_path

    print("🧠 AI splitting story...")
    parts = simple_split(text)

    temp_files = []

    for i, part in enumerate(parts):

        role = part.get("role", "narrator")
        content = part.get("text", "")
        gender = part.get("gender", "female")
        emotion = detect_emotion(content)

        voice_id = get_voice(role, gender)

        temp_path = os.path.join(BASE_AUDIO, f"seg_{i}.mp3")

        print(f"🎙️ Segment {i+1}: {role} | {gender} | {emotion}")

        # 1. ElevenLabs
        audio = elevenlabs_tts(content, temp_path, voice_id, emotion)

        # 2. Edge fallback (MULTILINGUAL)
        if not audio:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio = loop.run_until_complete(
                    edge_generate(content, temp_path, gender, emotion)
                    )
            except:
                audio = None

        if not audio:
            audio = gemini_audio(content, temp_path)


        # 4. gTTS fallback
        if not audio:
            audio = gtts_generate(content, temp_path)

        if is_valid_audio(temp_path):
            temp_files.append(temp_path)
        else:
            print("❌ Invalid audio deleted")
            try:
                os.remove(temp_path)
            except:
                pass

        print(f"📁 File size: {os.path.getsize(temp_path) if os.path.exists(temp_path) else 0}")  
    # -------- MERGE AUDIO -------- #

    valid_files = [f for f in temp_files if is_valid_audio(f)]

    if not valid_files:
        print("⚠️ No valid audio generated → using fallback")

        fallback_path = os.path.join(BASE_AUDIO, "fallback.mp3")

        # Simple narration fallback
        gtts_generate(text, fallback_path)

        return fallback_path

    clips = []

    for f in valid_files:
        try:
            clips.append(AudioFileClip(f))
        except:
            print(f"❌ Skipping corrupted file: {f}")
    final = concatenate_audioclips(clips)
    final.write_audiofile(final_path, logger=None)

    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass

    print("✅ Final audio ready")

    return final_path