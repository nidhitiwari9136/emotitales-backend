import os
import uuid
import asyncio
import re
import requests
import edge_tts
import pyttsx3
from gtts import gTTS
from langdetect import detect
from moviepy.editor import AudioFileClip, concatenate_audioclips
from dotenv import load_dotenv
import hashlib
import spacy
from transformers import pipeline
import random
import gender_guesser.detector as gender
nlp = spacy.load("en_core_web_trf")

character_voice_memory = {}
CHARACTER_MEMORY = {}
LAST_GENDER = None

load_dotenv()

BASE_AUDIO = "media/audio"
os.makedirs(BASE_AUDIO, exist_ok=True)

ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def get_audio_cache_filename(text):
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    return f"story_{text_hash}.mp3"

# =====================================================
# 🎭 CHARACTER + VOICE SETTINGS
# =====================================================

CHARACTER_VOICES = {
    "narrator": {"gender": "female"},
    "dad": {"gender": "male"},
    "mother": {"gender": "female"},
    "boy": {"gender": "male"},
    "girl": {"gender": "female"},
}

EDGE_VOICE_MAP = {
    "English": {
        "female": "en-IN-NeerjaNeural",
        "male": "en-IN-PrabhatNeural",
    },
    "Hindi": {
        "female": "hi-IN-SwaraNeural",
        "male": "hi-IN-MadhurNeural",
    },
    "Marathi": {
        "female": "mr-IN-AarohiNeural",
        "male": "mr-IN-ManoharNeural",
    },
    "Gujarati": {
        "female": "gu-IN-DhwaniNeural",
        "male": "gu-IN-NiranjanNeural",
    },
    "Tamil": {
        "female": "ta-IN-PallaviNeural",
        "male": "ta-IN-ValluvarNeural",
    },
    "Telugu": {
        "female": "te-IN-ShrutiNeural",
        "male": "te-IN-MohanNeural",
    },
    "Bengali": {
        "female": "bn-IN-TanishaaNeural",
        "male": "bn-IN-BashkarNeural",
    },
    "Punjabi": {
        "female": "pa-IN-GurleenNeural",
        "male": "pa-IN-HarishNeural",
    },
    "Hinglish": {
        "female": "en-IN-NeerjaNeural",
        "male": "en-IN-PrabhatNeural",
    }
}

EMOTION_SETTINGS = {
    "happy": {"rate": "+20%", "pitch": "+5Hz"},
    "sad": {"rate": "-20%", "pitch": "-5Hz"},
    "funny": {"rate": "+25%", "pitch": "+8Hz"},
    "neutral": {"rate": "+0%", "pitch": "+0Hz"},
}

# =====================================================
# 🔎 HELPERS
# =====================================================

def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

def detect_emotion(text):
    t = text.lower()

    if any(w in t for w in ["cry", "sad", "दुख", "रो", "आँसू"]):
        return "sad"

    if any(w in t for w in ["laugh", "happy", "खुश", "आनंद"]):
        return "happy"

    if any(w in t for w in ["funny", "joke", "हँसी", "मजेदार"]):
        return "funny"

    return "neutral"

# -----------------------------
# Extract PERSON names using NER
# -----------------------------
def extract_character_names(text):
    doc = nlp(text)
    names = set()

    # 1️⃣ Named Entities
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "ORG"]:
            if ent.text[0].isupper():
                names.add(ent.text)

    # 2️⃣ Proper noun fallback
    for token in doc:
        if token.pos_ == "PROPN" and token.text[0].isupper():
            names.add(token.text)

    return list(names)

# -----------------------------
# Detect gender from name using AI
# -----------------------------
gender_detector = gender.Detector()

def detect_gender_from_name(name):
    try:
        first_name = name.split()[0]
        result = gender_detector.get_gender(first_name)

        if result in ["male", "mostly_male"]:
            return "male"

        if result in ["female", "mostly_female"]:
            return "female"

    except:
        pass

    return "unknown"


# -----------------------------
# Assign voices to characters
# -----------------------------
def assign_character_voices(text):
    doc = nlp(text)

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text
            if name not in character_voice_memory:
                gender = detect_gender_from_name(name)
                if gender == "unknown":
                    gender = random.choice(["male", "female"])
                character_voice_memory[name] = gender
# =====================================================
# 1️⃣ ELEVENLABS
# =====================================================

def elevenlabs_generate(text, filename):

    if not ELEVEN_KEY:
        return None

    try:
        path = f"{BASE_AUDIO}/{filename}"

        emotion = detect_emotion(text)

        emotion_settings = {
            "happy":  {"stability": 0.3, "style": 0.9},
            "sad":    {"stability": 0.6, "style": 0.5},
            "funny":  {"stability": 0.2, "style": 1.0},
            "neutral":{"stability": 0.45,"style": 0.7},
        }

        settings = emotion_settings.get(emotion, emotion_settings["neutral"])

        url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"

        headers = {
            "xi-api-key": ELEVEN_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": settings["stability"],
                "similarity_boost": 0.85,
                "style": settings["style"],
                "use_speaker_boost": True
            }
        }

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200 and response.content:
            with open(path, "wb") as f:
                f.write(response.content)

            if os.path.getsize(path) > 10000:
                print("🎬 ElevenLabs Cinematic Voice Used")
                return path

        print("❌ ElevenLabs failed or small audio")
        return None

    except Exception as e:
        print("ElevenLabs Error:", e)
        return None
# =====================================================
# 2️⃣ GEMINI PRO PREVIEW TTS
# =====================================================

def gemini_pro_tts(text, filename):

    if not GEMINI_KEY:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-pro-preview-tts",
            contents=text
        )

        audio_bytes = response.candidates[0].content.parts[0].inline_data.data

        path = f"{BASE_AUDIO}/{filename}"
        with open(path, "wb") as f:
            f.write(audio_bytes)

        print("✅ Gemini Pro TTS used")
        return path

    except:
        return None

# =====================================================
# 3️⃣ GEMINI FLASH PREVIEW TTS
# =====================================================

def gemini_flash_tts(text, filename):

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text
        )

        audio_bytes = response.candidates[0].content.parts[0].inline_data.data

        path = f"{BASE_AUDIO}/{filename}"
        with open(path, "wb") as f:
            f.write(audio_bytes)

        print("✅ Gemini Flash TTS used")
        return path

    except:
        return None

# =====================================================
# 4️⃣ GEMINI NATIVE AUDIO
# =====================================================

def gemini_native_audio(text, filename):

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-flash-native-audio-latest",
            contents=text
        )

        audio_bytes = response.candidates[0].content.parts[0].inline_data.data

        path = f"{BASE_AUDIO}/{filename}"
        with open(path, "wb") as f:
            f.write(audio_bytes)

        print("✅ Gemini Native Audio used")
        return path

    except:
        return None

# =====================================================
# 5️⃣ EDGE TTS
# =====================================================

import random

# -----------------------------
# Language Mapping
# -----------------------------
def map_language_code(code):
    if code.startswith("hi"): return "Hindi"
    if code.startswith("mr"): return "Marathi"
    if code.startswith("gu"): return "Gujarati"
    if code.startswith("ta"): return "Tamil"
    if code.startswith("te"): return "Telugu"
    if code.startswith("bn"): return "Bengali"
    if code.startswith("pa"): return "Punjabi"
    return "English"

# -----------------------------
# Grammar-based Gender Detection
# -----------------------------
def detect_gender_from_context(sentence):

    global LAST_GENDER

    doc = nlp(sentence)

    # 1️⃣ PERSON entity detection
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text
            gender = detect_gender_from_name(name)
            CHARACTER_MEMORY[name] = gender
            LAST_GENDER = gender
            return gender

    lower = sentence.lower()

    # 2️⃣ Pronoun detection
    for token in doc:
        if token.lower_ == "he":
            LAST_GENDER = "male"
            return "male"
        if token.lower_ == "she":
            LAST_GENDER = "female"
            return "female"

    # 3️⃣ Use previous speaker memory
    if LAST_GENDER:
        return LAST_GENDER

    return "unknown"

# -----------------------------
# Age-based pitch control
# -----------------------------
def age_pitch_modifier(sentence):
    lower = sentence.lower()
    if any(w in lower for w in ["dada", "grandfather", "old"]):
        return "-10%"
    if any(w in lower for w in ["boy", "girl", "child"]):
        return "+20%"
    return "+3%"

def edge_generate_sync(text, filename):

    global LAST_GENDER
    character_voice_memory.clear()
    CHARACTER_MEMORY.clear()
    LAST_GENDER = None

    assign_character_voices(text)

    lang_detected = detect_language(text)
    language = map_language_code(lang_detected)  # simplify for test

    # Stable narrator
    if character_voice_memory:
        narrator_gender = list(character_voice_memory.values())[0]
    else:
        narrator_gender = "female"

    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    temp_files = []

    async def generate_clip(sentence, index):

        gender = None

        # 1️⃣ Character memory check
        for name, g in character_voice_memory.items():
            if name.lower() in sentence.lower():
                gender = g
                break

        # 2️⃣ Context detection
        if not gender:
            gender = detect_gender_from_context(sentence)

        # 3️⃣ Final fallback
        if not gender or gender == "unknown":
            gender = narrator_gender

        voice = EDGE_VOICE_MAP.get(language, EDGE_VOICE_MAP["English"])[gender]

        print(f"🎙 Sentence: {sentence}")
        print(f"   → Detected Gender: {gender}")
        print(f"   → Voice Used: {voice}")

        communicate = edge_tts.Communicate(
            sentence,
            voice,
            rate="+10%",
            pitch="+3Hz"
        )

        temp_file = f"media/audio/seg_{index}.mp3"
        await communicate.save(temp_file)
        return temp_file

    async def process():
        tasks = []
        for i, s in enumerate(sentences):
            tasks.append(generate_clip(s, i))
        return await asyncio.gather(*tasks)

    temp_files = asyncio.run(process())

    clips = [AudioFileClip(f) for f in temp_files]
    final_audio = concatenate_audioclips(clips)

    final_path = f"media/audio/{filename}"
    final_audio.write_audiofile(final_path)

    for f in temp_files:
        os.remove(f)

    print("🎭 Edge Cinematic Voice OK")
    return final_path
# =====================================================
# 6️⃣ gTTS
# =====================================================

def gtts_generate(text, filename):

    try:
        lang = detect_language(text)
        path = f"{BASE_AUDIO}/{filename}"

        tts = gTTS(text=text, lang=lang)
        tts.save(path)

        if os.path.getsize(path) > 5000:
            print("⚠ gTTS used")
            return path

    except Exception as e:
        print("gTTS Error:", e)

    return None

# =====================================================
# 7️⃣ OFFLINE
# =====================================================

def offline_generate(text, filename):

    try:
        engine = pyttsx3.init()
        path = f"{BASE_AUDIO}/{filename}"

        engine.setProperty('rate', 170)
        engine.setProperty('volume', 1.0)

        engine.save_to_file(text, path)
        engine.runAndWait()

        if os.path.exists(path) and os.path.getsize(path) > 3000:
            print("⚠ Offline used")
            return path

    except Exception as e:
        print("Offline Error:", e)

    return None

def generate_full_audio_sync(story_text):

    filename = get_audio_cache_filename(story_text)
    path = f"{BASE_AUDIO}/{filename}"

    # 🔥 1️⃣ CACHE CHECK
    if os.path.exists(path) and os.path.getsize(path) > 5000:
        print("⚡ Using Cached Audio")
        return path

    # 🔥 2️⃣ ELEVENLABS
    path = elevenlabs_generate(story_text, filename)
    if path:
        return path

    
    # 🔥 4️⃣ EDGE
    path = edge_generate_sync(story_text, filename)
    if path:
        return path

    # 🔥 3️⃣ GEMINI (Retry Logic)
        # 🔥 3️⃣ GEMINI FLASH
    for attempt in range(2):
        path = gemini_tts_generate(
            story_text,
            filename,
            "gemini-2.5-flash-preview-tts"
        )
        if path:
            return path

        print(f"⚠ Gemini Flash retry {attempt+1}")
        import time
        time.sleep(2)

    # 🔥 4️⃣ GEMINI NATIVE AUDIO
    path = gemini_tts_generate(
        story_text,
        filename,
        "gemini-2.5-flash-native-audio-latest"
    )
    if path:
        return path

    
    # 🔥 5️⃣ gTTS
    path = gtts_generate(story_text, filename)
    if path:
        return path

    # 🔥 6️⃣ Offline
    path = offline_generate(story_text, filename)
    if path:
        return path

    raise Exception("All TTS engines failed")

def gemini_tts_generate(text, filename, model_name):

    try:
        from google import genai
        import base64

        client = genai.Client(api_key=GEMINI_KEY)

        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config={
                "response_modalities": ["AUDIO"]
            }
        )

        if not response.candidates:
            return None

        parts = response.candidates[0].content.parts
        if not parts or not parts[0].inline_data:
            return None

        audio_bytes = base64.b64decode(parts[0].inline_data.data)

        path = f"{BASE_AUDIO}/{filename}"

        with open(path, "wb") as f:
            f.write(audio_bytes)

        size = os.path.getsize(path)

        if size > 10000:
            print(f"🎧 Gemini Success: {model_name}")
            return path

        print("❌ Gemini audio too small")
        return None

    except Exception as e:
        print(f"Gemini Failed ({model_name}):", e)
        return None