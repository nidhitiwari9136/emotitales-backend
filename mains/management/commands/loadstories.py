import json
from django.core.management.base import BaseCommand
from mains.models import LibraryStory

class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        with open("mains/storygen/data/stories.json", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            LibraryStory.objects.create(
                title=item["title"],
                category=item["category"],
                content_en=item["content"]
            )

        self.stdout.write(self.style.SUCCESS("Stories Imported Successfully"))