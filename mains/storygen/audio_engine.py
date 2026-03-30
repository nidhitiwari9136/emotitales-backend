import os
import asyncio
import re
import requests
import edge_tts
import hashlib
import random
import base64
from gtts import gTTS
from django.conf import settings
from langdetect import detect
from moviepy.editor import AudioFileClip, concatenate_audioclips
from google import genai
from dotenv import load_dotenv
import imageio_ffmpeg
import os
if os.name == 'nt': 
    os.environ["IMAGEIO_FFMPEG_EXE"] = r"C:\Users\Nidhi Tiwari\Downloads\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
else:
    os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

load_dotenv()

character_voice_memory = {}
BASE_AUDIO = os.path.join(settings.MEDIA_ROOT, "audio")
os.makedirs(BASE_AUDIO, exist_ok=True)

ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

# =====================================================
# 🎭 VOICE MAPS
# =====================================================

VOICE_IDS = {
    "narrator": "Rachel",         # Standard Narrator
    "male": "pNInz6obpgnuM0sLNojD",   # 'Liam' - Deep & Clear (Rahul ke liye)
    "female": "EXAVITQu4vr4xnSDxMaL", # 'Bella' - Soft & Emotional (Anjali ke liye)
}

EDGE_VOICE_MAP = {
    "English": {"female": "en-IN-NeerjaNeural", "male": "en-IN-PrabhatNeural"},
    "Hindi": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"},
    "Marathi": {"female": "mr-IN-AarohiNeural", "male": "mr-IN-ManoharNeural"},
    "Gujarati": {"female": "gu-IN-DhwaniNeural", "male": "gu-IN-NiranjanNeural"},
    "Tamil": {"female": "ta-IN-PallaviNeural", "male": "ta-IN-ValluvarNeural"},
    "Telugu": {"female": "te-IN-ShrutiNeural", "male": "te-IN-MohanNeural"},
    "Bengali": {"female": "bn-IN-TanishaaNeural", "male": "bn-IN-BashkarNeural"},
    "Punjabi": {"female": "pa-IN-GurleenNeural", "male": "pa-IN-HarishNeural"},
}

# =====================================================
# 🔎 SMART MAPPING (Hamesha pehle chalega)
# =====================================================

def assign_character_voices(text):
    global character_voice_memory
    character_voice_memory.clear()
    prompt = (
        "Identify person names in this story and their gender (male/female). "
        "Output ONLY as: Name:gender, Name:gender. "
        f"Story: {text[:1000]}"
    )
    
    try:
        # Priority 1: Groq (Fastest)
        if GROQ_KEY:
            from groq import Groq
            g_client = Groq(api_key=GROQ_KEY)
            resp = g_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile"
            ).choices[0].message.content
        # Priority 2: Gemini
        else:
            resp = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt).text
        
        if resp:
            for item in resp.strip().split(','):
                if ':' in item:
                    name, g = item.split(':')
                    character_voice_memory[name.strip()] = g.strip().lower()
        print(f"🎭 Characters: {character_voice_memory}")
    except Exception as e:
        print(f"⚠️ Mapping failed, using narrator only: {e}")

# =====================================================
# 🎙️ ENGINES
# =====================================================

# 1. ElevenLabs (Ab ye character emotions ko handle karega)
def elevenlabs_generate_pro(text, filename, character_name=None):
    """
    ElevenLabs Pro Engine: Multi-language + Emotions
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ ElevenLabs API Key missing!")
        return None

    # 1. Voice selection based on character mapping
    gender = character_voice_memory.get(character_name, "narrator")
    voice_id = VOICE_IDS.get(gender, VOICE_IDS["narrator"])

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    # 2. Emotion & Quality Settings
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2", # Best for Hindi, Marathi, etc.
        "voice_settings": {
            "stability": 0.45,       # Thoda kam taaki emotions (uthaar-chadhau) zyada aayein
            "similarity_boost": 0.8,  # Awaaz ekdam real lagegi
            "style": 0.15,            # Thoda expressive style
            "use_speaker_boost": True
        }
    }

    try:
        print(f"🎙️ ElevenLabs: Generating audio for {character_name or 'Narrator'}...")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            path = f"media/audio/{filename}"
            with open(path, "wb") as f:
                f.write(response.content)
            
            # Size check (to ensure it's not empty)
            if os.path.getsize(path) > 5000:
                return path
        else:
            print(f"❌ ElevenLabs Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"💥 ElevenLabs Critical Error: {e}")
        return None

def gemini_native_audio_generate(text, filename, model_id):
    """Gemini Native Audio Engine - Fixed Model Paths"""
    try:
        # Aapki list ke mutabiq models/ prefix zaroori ho sakta hai
        full_model_name = f"models/{model_id}" if not model_id.startswith("models/") else model_id
        
        print(f"🎙️ Sending request to: {full_model_name}")
        
        response = client.models.generate_content(
            model=full_model_name,
            contents=text,
            config={
                "response_modalities": ["AUDIO"],
            }
        )
        
        if response.candidates and response.candidates[0].content.parts:
            # Inline data check
            part = response.candidates[0].content.parts[0]
            if part.inline_data:
                audio_data = base64.b64decode(part.inline_data.data)
                path = f"{BASE_AUDIO}/{filename}"
                with open(path, "wb") as f:
                    f.write(audio_data)
                
                # Check if file is actually audio (minimum size check)
                if os.path.getsize(path) > 2000: # 2KB se badi honi chahiye
                    return path
                else:
                    print("⚠️ Audio too short/empty, skipping...")
                    return None
        return None
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return None

# 2. Edge TTS (Multi-Voice fallback)
async def edge_generate_async(text, filename):
    lang_code = detect(text)[:2]
    inv_map = {"hi": "Hindi", "mr": "Marathi", "gu": "Gujarati", "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "pa": "Punjabi"}
    language = inv_map.get(lang_code, "English")
    
    sentences = re.split(r'(?<=[.!?]) +', text)
    temp_files = []
    
    for i, s in enumerate(sentences):
        if not s.strip(): continue
        gender = "female" # default
        for name, g in character_voice_memory.items():
            if name.lower() in s.lower():
                gender = g
                break
        
        voice = EDGE_VOICE_MAP.get(language, EDGE_VOICE_MAP["English"]).get(gender)
        comm = edge_tts.Communicate(s, voice)
        t_path = f"{BASE_AUDIO}/seg_{i}.mp3"
        await comm.save(t_path)
        temp_files.append(t_path)

    clips = [AudioFileClip(f) for f in temp_files]
    final_path = f"{BASE_AUDIO}/{filename}"
    concatenate_audioclips(clips).write_audiofile(final_path, logger=None)
    for f in temp_files: os.remove(f)
    return final_path

def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

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

# =====================================================
# 🚀 MAIN FLOW (PRO FALLBACK)
# =====================================================

def generate_full_audio_sync(story_text):
    filename = f"story_{hashlib.md5(story_text.encode()).hexdigest()}.mp3"
    path = f"media/audio/{filename}"
    
    if os.path.exists(path): return path

    # STEP 0: Pehle characters map kar lo (Taaki Edge TTS ko pata ho)
    assign_character_voices(story_text)

    # STEP 1: ElevenLabs (Aapka Main Hero - Exam ke liye)
    res = elevenlabs_generate_pro(story_text, filename)
    if res: 
        print("✅ ElevenLabs Success!")
        return res

    # STEP 2: Gemini Native Audio (Best quality from your list)
    # Hum 2.5 Flash Native Audio ko use karenge, ye sabse natural hai.
    audio_models = [
        "gemini-2.5-flash-native-audio-latest", 
        "gemini-2.5-flash-native-audio-preview-12-2025",
        "gemini-2.5-flash-preview-tts" # Ye dedicated TTS model hai
    ]

    for model_id in audio_models:
        print(f"🎙️ Trying Gemini Audio Model: {model_id}")
        res = gemini_native_audio_generate(story_text, filename, model_id)
        if res: return res

    # STEP 3: Edge TTS (Multi-character/Multilingual Fallback)
    # Agar Gemini ki quota limit (429) hit ho jati hai.
    try:
        print("🎙️ Trying Edge TTS (Fallback)...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(edge_generate_async(story_text, filename))
        if res: return res
    except: pass

    # STEP 4: gTTS (The Final Safety Net)
    print("🎙️ Trying gTTS (Last Resort)...")
    return gtts_generate(story_text, filename)
    filename = f"story_{hashlib.md5(story_text.encode()).hexdigest()}.mp3"
    path = f"media/audio/{filename}"
    
    