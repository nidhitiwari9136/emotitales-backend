# import os
# from groq import Groq
# from google import genai
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# GEMINI_KEY = os.getenv("GEMINI_API_KEY")
# GROQ_KEY = os.getenv("GROQ_API_KEY")
# OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# gemini_client = genai.Client(api_key=GEMINI_KEY)
# groq_client = Groq(api_key=GROQ_KEY)


# def build_prompt(language, emotion, length, topic):
#     return f"""
# You are an emotionally intelligent children's storyteller.

# Language: {language}
# Emotion: {emotion}
# Length: {length}

# Write a cinematic, emotionally rich, child-friendly story.

# Topic:
# {topic}

# Rules:
# - Clear visual storytelling
# - Character emotions visible
# - Dialogues allowed
# - Strong beginning, emotional middle, meaningful ending
# - No technical explanation
# """


# from google import genai
# import os

# GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# def generate_story(language, emotion, word_limit, topic):

#     client = genai.Client(api_key=GEMINI_KEY)

#     prompt_text = f"""
# You are an emotionally intelligent children's storyteller.

# Write a detailed emotional story in {language}.
# The story should be approximately {word_limit} words.
# Keep it between {word_limit - 50} and {word_limit} words.

# Emotion tone: {emotion}

# Make it cinematic, child-friendly, expressive.
# Include dialogues if suitable.
# Strong beginning, emotional middle, meaningful ending.

# Topic:
# {topic}
# """

#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=prompt_text
#     )

#     story = response.text.strip()

#     # 🔥 Soft trim (only if very oversized)
#     words = story.split()
#     if len(words) > word_limit + 50:
#         story = " ".join(words[:word_limit])

#     return story


import os
from groq import Groq
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

# Clients
gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None


def generate_story(language, emotion, word_limit, topic):

    prompt_text = f"""
You are an emotionally intelligent children's storyteller.

Write a detailed emotional story in {language}.
The story should be approximately {word_limit} words.
Keep it between {word_limit - 50} and {word_limit} words.

Emotion tone: {emotion}

Make it cinematic, child-friendly, expressive.
Include dialogues if suitable.
Strong beginning, emotional middle, meaningful ending.

Topic:
{topic}
"""

    # ================= GEMINI TRY =================
    if gemini_client:
        try:
            print("🔥 Trying Gemini...")
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_text
            )

            if response and response.text:
                story = response.text.strip()
                return trim_story(story, word_limit)

        except Exception as e:
            print("❌ Gemini failed:", e)

    # ================= GROQ FALLBACK =================
    if groq_client:
        try:
            print("⚡ Falling back to Groq...")

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # best for storytelling
                messages=[
                    {"role": "system", "content": "You are a children's storyteller."},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.8,
                max_tokens=word_limit * 2
            )

            story = response.choices[0].message.content.strip()
            return trim_story(story, word_limit)

        except Exception as e:
            print("❌ Groq failed:", e)

    # ================= FINAL FALLBACK =================
    return "⚠️ Story generation failed. Please try again later."


# ================= HELPER =================
def trim_story(story, word_limit):
    words = story.split()

    if len(words) > word_limit + 50:
        return " ".join(words[:word_limit])

    return story