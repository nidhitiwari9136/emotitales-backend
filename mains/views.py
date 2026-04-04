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
        
        # 1. Client ID ko Environment Variable se uthao
        CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") 
        
        if not token:
            return JsonResponse({"error": "Token missing"}, status=400)

        # 2. Token verify karo
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            CLIENT_ID
        )
        
        email = idinfo.get("email")
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")

        # 3. User create ya fetch karo
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email, # Username hamesha unique hona chaiye
                "first_name": first_name,
                "last_name": last_name
            }
        )
        
        # Django session login
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        
        return JsonResponse({
            "message": "Google login successful", 
            "username": user.username,
            "email": user.email
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

                response["audio"] = settings.MEDIA_URL + "audio/" + os.path.basename(audio_path)

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
        from .storygen.audio_engine import generate_full_audio_sync
        data = json.loads(request.body)
        story_text = data.get("story")
        audio_path = generate_full_audio_sync(story_text)
        filename = os.path.basename(audio_path)
        
        audio_url = settings.MEDIA_URL + "audio/" + filename
        return JsonResponse({"audio": audio_url})
    except Exception as e:
        print("AUDIO ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def get_all_library_stories(request):
    # 1. Database se stories uthao
    stories = LibraryStory.objects.all()

    # 2. Agar database khali hai, toh JSON se load karega
    if not stories.exists():
        # Apna path: mains/storygen/data/stories.json
        json_path = os.path.join(settings.BASE_DIR, 'mains', 'storygen', 'data', 'stories.json')
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    stories_data = json.load(f)
                    for item in stories_data:
                        # Database mein entry create karega
                        LibraryStory.objects.get_or_create(
                            title=item.get('title'),
                            defaults={
                                'category': item.get('category', 'General'),
                                'content_en': item.get('content_en', item.get('content', ''))
                            }
                        )
                # Data load hone ke baad fir se stories fetch karega
                stories = LibraryStory.objects.all()
            except Exception as e:
                print(f"Error loading stories: {e}")

    # 3. Frontend ko data bhejo
    data = [{"id": s.id, "title": s.title, "category": s.category} for s in stories]
    return JsonResponse({"stories": data})

@csrf_exempt
def translate_existing_story(request):
    try:
        data = json.loads(request.body)
        text = data.get("text")
        language = data.get("language")

        translated = translate_story(text, language)

        return JsonResponse({"story": translated})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)