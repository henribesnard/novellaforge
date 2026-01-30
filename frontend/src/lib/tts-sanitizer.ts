/**
 * Nettoie le texte pour une lecture TTS fluide.
 * Supprime les artefacts markdown, HTML et caracteres parasites
 * tout en preservant la ponctuation narrative (dialogues, pauses).
 */
export function sanitizeForTTS(raw: string): string {
  let text = raw;

  // 1. HTML tags (filet de securite)
  text = text.replace(/<[^>]+>/g, ' ');

  // 2. Blocs de code (```...```)
  text = text.replace(/```[\s\S]*?```/g, ' ');

  // 3. Separateurs markdown (---, ***, ___, ===)
  text = text.replace(/^[ \t]*[-*_=]{3,}[ \t]*$/gm, ' ');

  // 4. Titres markdown (# ## ### etc.)
  text = text.replace(/^#{1,6}\s+/gm, '');

  // 5. Citations : > texte -> texte
  text = text.replace(/^>\s+/gm, '');

  // 6. Listes a puces : - texte ou * texte (en debut de ligne)
  text = text.replace(/^[ \t]*[-*+]\s+/gm, '');

  // 7. Listes numerotees : 1. texte (en debut de ligne)
  text = text.replace(/^[ \t]*\d+\.\s+/gm, '');

  // 8. Images markdown : ![alt](url) -> supprimer
  text = text.replace(/!\[([^\]]*)\]\([^)]+\)/g, '');

  // 9. Liens markdown : [texte](url) -> texte
  text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

  // 10. Gras+italique : ***texte*** ou ___texte___
  text = text.replace(/(\*{3}|_{3})(.+?)\1/g, '$2');

  // 11. Gras : **texte** ou __texte__
  text = text.replace(/\*\*(.+?)\*\*/g, '$1');
  text = text.replace(/__(.+?)__/g, '$1');

  // 12. Italique : *texte* ou _texte_ (attention aux apostrophes)
  text = text.replace(/(^|[^\w])\*([^*\n]+?)\*(?!\w)/g, '$1$2');
  text = text.replace(/(^|[^\w])_([^_\n]+?)_(?!\w)/g, '$1$2');

  // 13. Barre : ~~texte~~
  text = text.replace(/~~(.+?)~~/g, '$1');

  // 14. Code inline : `code` -> code
  text = text.replace(/`([^`]+)`/g, '$1');

  // 15. Asterisques ou underscores isoles restants (nettoyage final)
  text = text.replace(/(^|[^\w])([*_]+)(?!\w)/g, '$1');

  // 16. Normalisation des espaces
  text = text.replace(/\s+/g, ' ');
  text = text.trim();

  return text;
}
