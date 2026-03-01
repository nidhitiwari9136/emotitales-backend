from mains.models import LibraryStory
from difflib import SequenceMatcher


def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_similar_stories(user_prompt, threshold=0.4):

    stories = LibraryStory.objects.all()
    matches = []

    for story in stories:
        score = similarity(user_prompt, story.title + " " + story.content_en[:500])

        if score > threshold:
            matches.append({
                "id": story.id,
                "title": story.title,
                "category": story.category,
                "score": round(score, 2)
            })

    matches = sorted(matches, key=lambda x: x["score"], reverse=True)

    return matches[:5]