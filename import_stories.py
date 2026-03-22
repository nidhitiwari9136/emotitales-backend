import os
import json
import django

# Django environment setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emotitales.settings')
django.setup()

from mains.models import LibraryStory  # Check karo aapka model name yahi hai na?

def import_data():
    json_path = 'mains/storygen/data/stories.json'
    
    if not os.path.exists(json_path):
        print(f"❌ File nahi mili: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        count = 0
        for item in data:
            # Yahan check karo ki aapke JSON ke keys models se match karein
            obj, created = LibraryStory.objects.get_or_create(
                title=item.get('title'),
                defaults={
                    'category': item.get('category', 'General'),
                    'content_en': item.get('content_en', item.get('content', ''))
                }
            )
            if created:
                count += 1
        
        print(f"✅ Success! {count} nayi stories database mein aa gayi hain.")

if __name__ == "__main__":
    import_data()