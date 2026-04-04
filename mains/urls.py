from django.urls import path
from . import views

urlpatterns = [
    path('register/',views.register_user),
    path('login/',views.login_user),
    path('logout/',views.logout_user),
    path('summary/', views.generate_summary, name='summary'),
    path("story/", views.generate_or_fetch_story),
    path("library/", views.get_all_library_stories),
    path("open-story/", views.open_library_story),
    path("audio/", views.generate_story_audio),
    path("google-login/", views.google_login),
    path("translate/", views.translate_existing_story),
]