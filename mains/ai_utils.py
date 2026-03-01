# import os
# import re
# from google import genai  # New SDK (v2)
# from langdetect import detect
# from transformers import pipeline
# from deep_translator import GoogleTranslator
# from dotenv import load_dotenv
# from .storygen.audio_engine import generate_full_audio_sync

# # # Load .env variables
# load_dotenv()





# # Aapki available list ke best models
# MODEL_PRIORITY = [
#     "gemini-flash-latest" 
#     "gemini-2.5-pro",           # Deep analysis for 20+ pages
#     "gemini-3-pro-preview",      # Next-gen reasoning
#     "gemini-2.5-flash"    # Newest: High capacity
# ]

# # Client setup (v1beta for best compatibility with your list)
# client = genai.Client(
#     api_key=os.getenv("GEMINI_API_KEY"), 
#     http_options={'api_version': 'v1beta'}
# )

# LANG_MAP = {
#     "hi": "Hindi", "mr": "Marathi", "ta": "Tamil", 
#     "te": "Telugu", "bn": "Bengali", "gu": "Gujarati", 
#     "pa": "Punjabi", "en": "English"
# }

# # # --- HELPERS ---

# def detect_language(text):
#     try:
#         lang = detect(text[:1000])
#         return lang if lang in LANG_MAP else "en"
#     except:
#         return "hi" if re.search(r"[ऀ-ॿ]", text) else "en"


# # --- CORE FUNCTIONS ---

# def multilingual_summarize(text):
#     """
#     Main summarization function: Handles 20+ pages by prioritizing 
#     Gemini Pro and using smart chunking if needed.
#     """
#     if not text or len(text.strip()) < 100:
#         raise Exception("Content too short for summarization.")

#     # 1. Language Detection
#     lang_code = detect_language(text)
#     lang_name = LANG_MAP.get(lang_code, "English")

#     # 2. Strategy: Try Gemini Models one by one
#     # Note: 20 pages ~ 15k words (Gemini can handle this in one go)
#     for model_id in MODEL_PRIORITY:
#         try:
#             print(f"🚀 Summarizing with {model_id} ({lang_name})...")
            
#             # Professional Prompt for Long Content
#             prompt = (
#                 f"Summarize the following content in {lang_name}. "
#                 "Provide a comprehensive yet concise summary. "
#                 "Highlight the key points and main conclusion. "
#                 f"\n\nContent:\n{text[:45000]}" # Approx 25-30 pages limit
#             )
            
#             response = client.models.generate_content(
#                 model=model_id,
#                 contents=prompt
#             )
            
#             if response.text:
#                 return response.text.strip(), lang_code
                
#         except Exception as e:
#             print(f"⚠️ {model_id} failed or quota hit: {e}")
#             continue # Try next model in list

#     # 3. Strategy: Local Fallback (If all Gemini models fail)
#     print("🔄 All Gemini models failed. Using Local BART Fallback...")
#     try:
#         summary = local_fallback_summary(text, lang_code)
#         return summary.strip(), lang_code
#     except Exception as e:
#         print(f"❌ Critical Failure: {e}")
#         return text[:1000] + "...", lang_code

# # --- UPDATED LOCAL FALLBACK (BART handles long text in chunks) ---

# def local_fallback_summary(text, target_lang):
#     """BART summary with Chunking for long docs"""
#     load_local_model()
#     if not en_summarizer:
#         return text[:500] + "..."

#     # Translate to English if needed (BART is English-centric)
#     working_text = text[:10000] # Local model constraint
#     if target_lang != "en":
#         try:
#             working_text = GoogleTranslator(source=target_lang, target="en").translate(working_text)
#         except: pass

#     parts = []
#     # BART cannot handle 20 pages at once, so we MUST chunk
#     for c in chunk_text(working_text, max_words=400):
#         try:
#             out = en_summarizer(c, max_length=150, min_length=50, do_sample=False)
#             parts.append(out[0]["summary_text"])
#         except: continue
    
#     combined = " ".join(parts)
    
#     # Translate back to target language
#     if target_lang == "en":
#         return combined
#     return GoogleTranslator(source="en", target=target_lang).translate(combined)

# def generate_summary_audio(summary_text):
#     """Your original audio logic - Do not change"""
#     if not summary_text or not summary_text.strip():
#         raise Exception("Summary text empty")
    
#     # Calls your main story audio engine
#     audio_path = generate_full_audio_sync(summary_text)
#     return audio_path

# def detect_emotion(text):
#     """Detect tone for audio engine using Gemini"""
#     try:
#         response = client.models.generate_content(
#             model=CURRENT_MODEL,
#             contents=f"Output only one word (happy/sad/neutral) for this tone: {text[:500]}"
#         )
#         return response.text.strip().lower()
#     except:
#         return "neutral"

import os
import re
from google import genai  
from langdetect import detect
from transformers import pipeline
# from deep_translator import GoogleTranslator
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