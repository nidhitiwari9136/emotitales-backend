import os
import re
from google import genai
from langdetect import detect
from dotenv import load_dotenv

load_dotenv()

# ---------------- CONFIG ---------------- #

MODEL_PRIORITY = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro"
]

MAX_CHUNK_SIZE = 15000

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

LANG_MAP = {
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "en": "English"
}

# ---------------- LANGUAGE DETECTION ---------------- #

def detect_language(text):
    try:
        lang = detect(text[:1000])
        return lang if lang in LANG_MAP else "en"
    except:
        return "hi" if re.search(r"[ऀ-ॿ]", text) else "en"


# ---------------- TEXT CHUNKING ---------------- #

def split_text(text, size=MAX_CHUNK_SIZE):

    chunks = []

    for i in range(0, len(text), size):
        chunks.append(text[i:i + size])

    return chunks


# ---------------- SAFE RESPONSE PARSER ---------------- #

def get_text(response):

    try:

        if hasattr(response, "text") and response.text:
            return response.text

        if response.candidates:
            return response.candidates[0].content.parts[0].text

    except:
        pass

    return None


# ---------------- GEMINI CALL ---------------- #

def call_gemini(prompt):

    for model in MODEL_PRIORITY:

        try:

            print("🚀 Trying model:", model)

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            text = get_text(response)

            if text:
                return text.strip()

        except Exception as e:

            print("⚠️ Model failed:", model, str(e))

    raise Exception("All Gemini models failed")


# ---------------- MAIN SUMMARIZER ---------------- #

def multilingual_summarize(text):

    if not text or len(text.strip()) < 50:
        raise Exception("Content too short for summarization")

    lang_code = detect_language(text)
    lang_name = LANG_MAP.get(lang_code, "English")

    chunks = split_text(text)

    summaries = []

    for i, chunk in enumerate(chunks):

        print(f"📄 Processing chunk {i+1}/{len(chunks)}")

        prompt = f"""
You are an expert document summarizer.

Summarize the following content in {lang_name}.

Rules:
- Keep the important ideas
- Remove repetition
- Write clearly and concisely
- Use small paragraphs

CONTENT:
{chunk}
"""

        summary = call_gemini(prompt)

        if summary:
            summaries.append(summary)

    if not summaries:
        raise Exception("Failed to generate summaries")

    # ---------------- FINAL SUMMARY ---------------- #

    combined_text = "\n".join(summaries)

    final_prompt = f"""
Create a final concise summary in {lang_name}
based on the following summaries.

TEXT:
{combined_text}
"""

    final_summary = call_gemini(final_prompt)

    return final_summary, lang_code


# ---------------- AUDIO GENERATION ---------------- #

def generate_summary_audio(summary_text):

    if not summary_text or not summary_text.strip():
        return None

    from .storygen.audio_engine import generate_full_audio_sync

    return generate_full_audio_sync(summary_text)