import os
from groq import Groq
from google import genai
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_KEY)
groq_client = Groq(api_key=GROQ_KEY)


def build_prompt(language, emotion, length, topic):
    return f"""
You are an emotionally intelligent children's storyteller.

Language: {language}
Emotion: {emotion}
Length: {length}

Write a cinematic, emotionally rich, child-friendly story.

Topic:
{topic}

Rules:
- Clear visual storytelling
- Character emotions visible
- Dialogues allowed
- Strong beginning, emotional middle, meaningful ending
- No technical explanation
"""


from google import genai
import os

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def generate_story(language, emotion, word_limit, topic):

    client = genai.Client(api_key=GEMINI_KEY)

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

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_text
    )

    story = response.text.strip()

    # 🔥 Soft trim (only if very oversized)
    words = story.split()
    if len(words) > word_limit + 50:
        story = " ".join(words[:word_limit])

    return story