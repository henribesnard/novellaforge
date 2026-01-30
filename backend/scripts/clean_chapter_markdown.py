"""
Script de nettoyage des chapitres existants.
Supprime les artefacts markdown (**, *, #, ---, ```, etc.)
du contenu des chapitres en base de donnees.

Usage:
    cd backend
    python -m scripts.clean_chapter_markdown
"""
import asyncio
import re
import sys
import os

# Ajouter le repertoire backend au path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)

# Charger le .env depuis la racine du projet
from dotenv import load_dotenv
load_dotenv(os.path.join(root_dir, ".env"))

# Remplacer le hostname Docker "postgres" par "localhost:5436" pour execution locale
db_url = os.environ.get("DATABASE_URL", "")
if "postgres:5432" in db_url:
    os.environ["DATABASE_URL"] = db_url.replace("postgres:5432", "localhost:5436")

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentType


def sanitize_markdown(raw: str) -> str:
    """
    Port Python de sanitizeForTTS (frontend/src/lib/tts-sanitizer.ts).
    Supprime les artefacts markdown/HTML tout en preservant
    la ponctuation narrative (dialogues, pauses, tirets cadratins).
    """
    text = raw

    # 1. Balises HTML
    text = re.sub(r'<[^>]+>', ' ', text)

    # 2. Blocs de code (```...```)
    text = re.sub(r'```[\s\S]*?```', ' ', text)

    # 3. Separateurs markdown (---, ***, ___, ===)
    text = re.sub(r'^[ \t]*[-*_=]{3,}[ \t]*$', ' ', text, flags=re.MULTILINE)

    # 4. Titres markdown (# ## ### etc.)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # 5. Citations : > texte -> texte
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # 6. Listes a puces : - texte ou * texte (en debut de ligne)
    text = re.sub(r'^[ \t]*[-*+]\s+', '', text, flags=re.MULTILINE)

    # 7. Listes numerotees : 1. texte (en debut de ligne)
    text = re.sub(r'^[ \t]*\d+\.\s+', '', text, flags=re.MULTILINE)

    # 8. Images markdown : ![alt](url) -> supprimer
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)

    # 9. Liens markdown : [texte](url) -> texte
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # 10. Gras+italique : ***texte*** ou ___texte___
    text = re.sub(r'(\*{3}|_{3})(.+?)\1', r'\2', text)

    # 11. Gras : **texte** ou __texte__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)

    # 12. Italique : *texte* ou _texte_ (attention aux apostrophes)
    text = re.sub(r'(^|[^\w])\*([^*\n]+?)\*(?!\w)', r'\1\2', text)
    text = re.sub(r'(^|[^\w])_([^_\n]+?)_(?!\w)', r'\1\2', text)

    # 13. Barre : ~~texte~~
    text = re.sub(r'~~(.+?)~~', r'\1', text)

    # 14. Code inline : `code` -> code
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # 15. Asterisques ou underscores isoles restants
    text = re.sub(r'(^|[^\w])([*_]+)(?!\w)', r'\1', text)

    # 16. Normalisation des espaces (garder les sauts de paragraphe)
    # Remplacer les espaces multiples sur une meme ligne
    text = re.sub(r'[^\S\n]+', ' ', text)
    # Normaliser les sauts de ligne multiples (max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def count_words(text: str) -> int:
    """Compte les mots dans un texte."""
    if not text or not text.strip():
        return 0
    return len(text.split())


async def main():
    print("=" * 60)
    print("NovellaForge - Nettoyage markdown des chapitres")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        # Recuperer tous les chapitres
        result = await session.execute(
            select(Document).where(Document.document_type == DocumentType.CHAPTER)
        )
        chapters = result.scalars().all()

        print(f"\nChapitres trouves: {len(chapters)}")

        if not chapters:
            print("Aucun chapitre a nettoyer.")
            return

        cleaned_count = 0
        skipped_count = 0

        for chapter in chapters:
            if not chapter.content:
                skipped_count += 1
                continue

            original = chapter.content
            cleaned = sanitize_markdown(original)

            if cleaned != original:
                chapter.content = cleaned
                chapter.word_count = count_words(cleaned)
                cleaned_count += 1

                # Afficher un resume des changements
                diff_chars = len(original) - len(cleaned)
                print(
                    f"  [NETTOYE] {chapter.title} "
                    f"(projet: {chapter.project_id}) "
                    f"-> -{diff_chars} caracteres, "
                    f"word_count: {count_words(original)} -> {chapter.word_count}"
                )
            else:
                skipped_count += 1
                print(f"  [OK]      {chapter.title} (deja propre)")

        if cleaned_count > 0:
            await session.commit()
            print(f"\nCommit effectue.")

        print(f"\n{'=' * 60}")
        print(f"Resume:")
        print(f"  Chapitres traites : {len(chapters)}")
        print(f"  Chapitres nettoyes: {cleaned_count}")
        print(f"  Chapitres ignores : {skipped_count}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
