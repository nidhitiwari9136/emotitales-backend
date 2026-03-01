import os
import re
from google import genai  
from langdetect import detect
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from .storygen.audio_engine import generate_full_audio_sync

# Load .env variables
load_dotenv()

# --- CONFIG ---
# Gemini-flash-latest is now #1, followed by Pro for deep analysis
MODEL_PRIORITY = [
    "gemini-flash-latest",      # Sabse fast aur reliable (Priority 1)
    "gemini-2.5-pro",           # Best for very long docs (20+ pages)
    "gemini-2.0-flash-lite",    # Solid secondary fallback
    "gemini-1.5-flash"          # Final Gemini safety net
]

# Current active model for simpler tasks (Emotion detection etc)
CURRENT_MODEL = "gemini-flash-latest"

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"), 
    http_options={'api_version': 'v1beta'}
)

LANG_MAP = {
    "hi": "Hindi", "mr": "Marathi", "ta": "Tamil", 
    "te": "Telugu", "bn": "Bengali", "gu": "Gujarati", 
    "pa": "Punjabi", "en": "English"
}

# --- HELPERS ---

def detect_language(text):
    try:
        lang = detect(text[:1000])
        return lang if lang in LANG_MAP else "en"
    except:
        return "hi" if re.search(r"[ऀ-ॿ]", text) else "en"

# --- CORE FUNCTIONS ---

def multilingual_summarize(text):
    """Summarizes long content (20+ pages) using Priority Models"""
    if not text or len(text.strip()) < 100:
        raise Exception("Content too short for summarization.")

    lang_code = detect_language(text)
    lang_name = LANG_MAP.get(lang_code, "English")

    for model_id in MODEL_PRIORITY:
        try:
            print(f"🚀 Summarizing with {model_id} ({lang_name})...")
            
            prompt = (
                f"Summarize the following content in {lang_name}. "
                "Provide a comprehensive yet concise summary with key highlights. "
                f"\n\nContent:\n{text[:50000]}" # Supports approx 30+ pages
            )
            
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            
            if response.text:
                return response.text.strip(), lang_code
                
        except Exception as e:
            print(f"⚠️ {model_id} failed: {e}")
            continue 

    print("🔄 All Gemini models failed. Using Local Fallback...")
    return local_fallback_summary(text, lang_code), lang_code

def detect_emotion(text):
    """Detect tone for audio engine using Gemini"""
    try:
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=f"Output only one word (happy/sad/neutral/scary) for this tone: {text[:500]}"
        )
        return response.text.strip().lower()
    except:
        return "neutral"

def generate_summary_audio(summary_text):
    """Generates audio for the summary using your existing engine"""
    if not summary_text or not summary_text.strip():
        raise Exception("Summary text empty")
    return generate_full_audio_sync(summary_text)

# Note: local_fallback_summary aur load_local_model niche waise hi rahenge jaise pehle the.