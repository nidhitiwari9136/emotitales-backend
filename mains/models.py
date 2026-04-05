from django.db import models


class Upload(models.Model):
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

class SummaryHistory(models.Model):

    input_text = models.TextField()
    language = models.CharField(max_length=10)

    summary = models.TextField()
    emotion = models.CharField(max_length=20)

    audio_file = models.FileField(upload_to="audio/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

class Story(models.Model):
    prompt = models.CharField(max_length=255, unique=True)
    language = models.CharField(max_length=20)

    story_text = models.TextField()

    sentiment = models.CharField(max_length=20, blank=True, null=True)

    audio_file = models.FileField(
        upload_to="audio/", blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.prompt[:50]

from django.db import models

class LibraryStory(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    content_en = models.TextField()

    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
