import os
from google import genai

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def translate_story(text, language):

    if language.lower() == "english":
        return text

    if not GEMINI_KEY:
        print("Gemini key missing")
        return text

    try:
        client = genai.Client(api_key=GEMINI_KEY)

        prompt = f"""
        You are a strict translator.

        Translate the following story EXACTLY into {language}.

        RULES:
        - Do NOT change story meaning
        - Do NOT add new content
        - Do NOT rewrite
        - Keep same length and structure
        - Only translate language

        Story:
        {text}
        """

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt
        )

        if hasattr(response, "text") and response.text:
            return response.text.strip()

        return text

    except Exception as e:
        print("Translation error:", e)
        return text