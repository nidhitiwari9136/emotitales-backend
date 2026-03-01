from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
import os
from .ai_utils import multilingual_summarize,  generate_summary_audio
from .pdf_utils import extract_text_from_pdf
from .storygen.story_engine import generate_story
from .storygen.audio_engine import generate_full_audio_sync
from .models import Story, SummaryHistory,LibraryStory
from .storygen.story_matcher import find_similar_stories
from .storygen.translator import translate_story
import asyncio
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

@csrf_exempt
def google_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        token = data.get("token")

        if not token:
            return JsonResponse({"error": "Token missing"}, status=400)

        # 🔥 VERIFY GOOGLE TOKEN
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            "YOUR_GOOGLE_CLIENT_ID"
        )

        email = idinfo.get("email")
        name = idinfo.get("name")

        if not email:
            return JsonResponse({"error": "Email not found"}, status=400)

        # 🔥 CHECK IF USER EXISTS
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email}
        )

        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)

        return JsonResponse({
            "message": "Google login successful",
            "username": user.username
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
        
@csrf_exempt
def register_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return JsonResponse({"error": "All fields are required"})

            if len(password) < 8:
                return JsonResponse({"error": "Password must be at least 8 characters"})

            if User.objects.filter(username=username).exists():
                return JsonResponse({"error": "User already exists"})

            User.objects.create_user(username=username, password=password)

            return JsonResponse({"message": "User registered successfully"})

        except Exception as e:
            return JsonResponse({"error": str(e)})

    return JsonResponse({"error": "Invalid request"})


@csrf_exempt
def login_user(request):
    if request.method == "POST":

        data = json.loads(request.body)

        username = data.get("username")
        password = data.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return JsonResponse({
                "message": "Login successful",
                "username": user.username
            })
        else:
            return JsonResponse({"error": "Invalid credentials"})

    return JsonResponse({"error": "Invalid request"})

@csrf_exempt
def logout_user(request):
    logout(request)
    return JsonResponse({"message": "Logged out"})


# ============================================================
# SUMMARY API (TEXT / PDF / 
# ============================================================


@csrf_exempt
def generate_summary(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:

        mode = request.POST.get("mode", "text")

        # ------------------------------------
        # INPUT HANDLING
        # ------------------------------------

        text = None
        file = request.FILES.get("file")

        if file:

            print("UPLOADED FILE:", file.name, file.size)

            file.seek(0)
            data = file.read()
            print("FILE SIZE:", len(data))
            file.seek(0)

            ext = os.path.splitext(file.name.lower())[1]

            # ---------- PDF ----------
            if ext == ".pdf":
                text = extract_text_from_pdf(file)

            # ---------- IMAGE ----------
            elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
                text = extract_text_from_image(file)

            else:
                return JsonResponse(
                    {"error": "Unsupported file type"},
                    status=400
                )

            print("EXTRACTED TEXT PREVIEW:", text[:400])

        else:

            text = request.POST.get("text")

            if not text or not text.strip():
                return JsonResponse(
                    {"error": "No input provided"},
                    status=400
                )

        # ------------------------------------
        # DEBUG BEFORE SUMMARY
        # ------------------------------------

        print("========== TEXT SENT TO SUMMARIZER ==========")
        print(text[:800])
        print("============================================")

        # ------------------------------------
        # SUMMARY
        # ------------------------------------

        summary, language = multilingual_summarize(text)


        history = SummaryHistory.objects.create(
            input_text=text,
            language=language,
            summary=summary,
        )

        response = {"summary": summary}

        if mode in ["audio"]:

            audio_path = generate_summary_audio(summary)

            history.audio_file.name = audio_path.replace("media/", "")
            history.save()

            response["audio"] = request.build_absolute_uri(
                settings.MEDIA_URL
                + "audio/"
                + os.path.basename(audio_path)
            )


        return JsonResponse(response)

    except Exception as e:
        print("🔥 BACKEND ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)


# ============================================================
# STORY GENERATION API (GROQ)
# ============================================================
@csrf_exempt
def generate_or_fetch_story(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)

        prompt = data.get("prompt")
        language = data.get("language", "English")
        emotion = data.get("emotion", "happy")
        length = data.get("length", "medium")

        if length == "short":
            word_limit = 150
        elif length == "medium":
            word_limit = 400
        elif length == "long":
            word_limit = 1000
        else:
            word_limit = 400

        if not prompt:
            return JsonResponse({"error": "Prompt required"}, status=400)

        # 1️⃣ Check similar stories
        matches = find_similar_stories(prompt)

        if matches:
            return JsonResponse({
                "type": "library_options",
                "matches": matches
            })

        # 2️⃣ Generate new story
        story_text = generate_story("English", emotion, word_limit, prompt)

        # 🔥 Always translate after generation
        if language.lower() != "english":
            story_text = translate_story(story_text, language)

        return JsonResponse({
            "type": "generated",
            "story": story_text
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def open_library_story(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        story_id = data.get("story_id")
        language = data.get("language", "English")

        story = LibraryStory.objects.get(id=story_id)

        content = story.content_en

        if language.lower() != "english":
            content = translate_story(content, language)

        return JsonResponse({
            "title": story.title,
            "story": content
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def generate_story_audio(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        story_text = data.get("story")

        audio_path = generate_full_audio_sync(story_text)
        
        filename = os.path.basename(audio_path)
        audio_url = request.build_absolute_uri(
            settings.MEDIA_URL + "audio/" + filename
            )
       

        print("FINAL AUDIO URL:", audio_url)

        return JsonResponse({
            "audio": audio_url
        })

    except Exception as e:
        print("AUDIO ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_all_library_stories(request):

    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=400)

    stories = LibraryStory.objects.all()[:30]

    data = []

    for story in stories:
        data.append({
            "id": story.id,
            "title": story.title,
            "category": story.category,
        })

    return JsonResponse({"stories": data})