import os
import re
from google import genai  # New SDK (v2)
from langdetect import detect
from transformers import pipeline
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from .storygen.audio_engine import generate_full_audio_sync

# Load .env variables
load_dotenv()

# Setup Client using the new SDK pattern
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_KEY)

# Use one of your available models
# Gemini 2.0 Flash is balanced for speed and long context
CURRENT_MODEL = "gemini-flash-latest" 

# Global local model placeholder (Lazy loading to save RAM)
en_summarizer = None

def load_local_model():
    global en_summarizer
    if en_summarizer is None:
        try:
            print("Loading local BART model for fallback...")
            en_summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=-1)
        except Exception as e:
            print(f"Local model error: {e}")

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

def chunk_text(text, max_words=450):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i + max_words])

# --- CORE LOGIC ---

def local_fallback_summary(text, target_lang):
    """Fallback using BART if Gemini API fails"""
    load_local_model()
    if not en_summarizer:
        return text[:500] + "..."

    working_text = text
    if target_lang != "en":
        working_text = GoogleTranslator(source=target_lang, target="en").translate(text)

    parts = []
    for c in chunk_text(working_text):
        out = en_summarizer(c, max_length=130, min_length=40, do_sample=False)
        parts.append(out[0]["summary_text"])
    
    combined = " ".join(parts)
    if target_lang == "en":
        return combined
    return GoogleTranslator(source="en", target=target_lang).translate(combined)

def multilingual_summarize(text):
    """Main summarization function with Gemini primary logic"""
    if not text or len(text.strip()) < 50:
        raise Exception("Text too short for processing")

    safe_text = text[:30000]

    lang = detect_language(text)
    lang_name = LANG_MAP.get(lang, "English")

    # Strategy 1: Gemini (New SDK syntax)
    try:
        print(f"🚀 Summarizing with {CURRENT_MODEL} ({lang_name})...")
        prompt = f"Summarize this content in {lang_name}. Make it professional and concise: {text}"
        
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=prompt
        )
        
        if response.text:
            return response.text.strip(), lang
    except Exception as e:
        print(f"❌ Gemini Error: {e}")

    # Strategy 2: Local Fallback
    summary = local_fallback_summary(text, lang)
    return summary.strip(), lang

def generate_summary_audio(summary_text):
    """Your original audio logic - Do not change"""
    if not summary_text or not summary_text.strip():
        raise Exception("Summary text empty")
    
    # Calls your main story audio engine
    audio_path = generate_full_audio_sync(summary_text)
    return audio_path

def detect_emotion(text):
    """Detect tone for audio engine using Gemini"""
    try:
        response = client.models.generate_content(
            model=CURRENT_MODEL,
            contents=f"Output only one word (happy/sad/neutral) for this tone: {text[:500]}"
        )
        return response.text.strip().lower()
    except:
        return "neutral"