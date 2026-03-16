from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
import os
from .pdf_utils import extract_text_from_pdf, extract_text_from_txt
from .models import Story, SummaryHistory, LibraryStory
from .storygen.story_matcher import find_similar_stories
from .storygen.translator import translate_story
import asyncio

# Google Auth imports (Inhe function ke bahar rakh sakte hain, ye heavy nahi hain)
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

        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            "YOUR_GOOGLE_CLIENT_ID"
        )
        email = idinfo.get("email")
        if not email:
            return JsonResponse({"error": "Email not found"}, status=400)

        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email}
        )
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        return JsonResponse({"message": "Google login successful", "username": user.username})
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
            return JsonResponse({"message": "Login successful", "username": user.username})
        else:
            return JsonResponse({"error": "Invalid credentials"})
    return JsonResponse({"error": "Invalid request"})

@csrf_exempt
def logout_user(request):
    logout(request)
    return JsonResponse({"message": "Logged out"})

# ============================================================
# SUMMARY API
# ============================================================
@csrf_exempt
def generate_summary(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:

        from .ai_utils import multilingual_summarize, generate_summary_audio

        mode = request.POST.get("mode", "text")

        text = None
        file = request.FILES.get("file")

        if file:

            print("Uploaded file:", file.name)

            ext = os.path.splitext(file.name.lower())[1]

            if ext == ".pdf":

                text = extract_text_from_pdf(file)

            elif ext == ".txt":

                text = extract_text_from_txt(file)

            else:
                return JsonResponse({"error": "Unsupported file"}, status=400)

        else:

            text = request.POST.get("text")

        if not text or not text.strip():

            return JsonResponse({"error": "No input"}, status=400)

        print("Text length:", len(text))

        # -------- SUMMARIZE -------- #

        summary, language = multilingual_summarize(text)

        history = SummaryHistory.objects.create(
            input_text=text[:5000],
            language=language,
            summary=summary
        )

        response = {"summary": summary}

        if mode == "audio":

            audio_path = generate_summary_audio(summary)

            if audio_path:

                history.audio_file.name = audio_path.replace("media/", "")
                history.save()

                response["audio"] = request.build_absolute_uri(
                    settings.MEDIA_URL + os.path.basename(audio_path)
                )

        return JsonResponse(response)

    except Exception as e:

        import traceback
        traceback.print_exc()

        return JsonResponse({"error": str(e)}, status=500)
        
# ============================================================
# STORY GENERATION API
# ============================================================
@csrf_exempt
def generate_or_fetch_story(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        # 🔥 LAZY IMPORT
        from .storygen.story_engine import generate_story
        data = json.loads(request.body)
        prompt = data.get("prompt")
        language = data.get("language", "English")
        emotion = data.get("emotion", "happy")
        length = data.get("length", "medium")

        word_limit = {"short": 150, "medium": 400, "long": 1000}.get(length, 400)

        if not prompt:
            return JsonResponse({"error": "Prompt required"}, status=400)

        # 1️⃣ Check similar stories
        matches = find_similar_stories(prompt)
        if matches:
            return JsonResponse({"type": "library_options", "matches": matches})

        # 2️⃣ Generate new story
        story_text = generate_story("English", emotion, word_limit, prompt)

        # 🔥 Translation
        if language.lower() != "english":
            story_text = translate_story(story_text, language)

        return JsonResponse({"type": "generated", "story": story_text})
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
        return JsonResponse({"title": story.title, "story": content})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def generate_story_audio(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        # 🔥 LAZY IMPORT
        from .storygen.audio_engine import generate_full_audio_sync
        data = json.loads(request.body)
        story_text = data.get("story")
        audio_path = generate_full_audio_sync(story_text)
        filename = os.path.basename(audio_path)
        audio_url = request.build_absolute_uri(settings.MEDIA_URL + "audio/" + filename)
        return JsonResponse({"audio": audio_url})
    except Exception as e:
        print("AUDIO ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_all_library_stories(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=400)
    stories = LibraryStory.objects.all()[:30]
    data = [{"id": s.id, "title": s.title, "category": s.category} for s in stories]
    return JsonResponse({"stories": data})