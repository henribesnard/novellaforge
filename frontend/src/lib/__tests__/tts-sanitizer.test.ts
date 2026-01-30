import { describe, expect, it } from 'vitest';
import { sanitizeForTTS } from '../tts-sanitizer';

describe('sanitizeForTTS', () => {
  it('supprime le gras markdown', () => {
    expect(sanitizeForTTS('**Sofia** se retourna')).toBe('Sofia se retourna');
  });

  it('supprime l italique markdown', () => {
    expect(sanitizeForTTS('*Il faut partir*')).toBe('Il faut partir');
  });

  it('supprime le gras+italique', () => {
    expect(sanitizeForTTS('***Attention***')).toBe('Attention');
  });

  it('supprime les titres markdown', () => {
    expect(sanitizeForTTS('# Chapitre 1\nTexte')).toBe('Chapitre 1 Texte');
  });

  it('supprime les separateurs', () => {
    expect(sanitizeForTTS('Fin.\n---\nDebut.')).toBe('Fin. Debut.');
    expect(sanitizeForTTS('Fin.\n***\nDebut.')).toBe('Fin. Debut.');
  });

  it('extrait le texte des liens', () => {
    expect(sanitizeForTTS('[cliquez ici](https://example.com)')).toBe('cliquez ici');
  });

  it('supprime les images', () => {
    expect(sanitizeForTTS('Texte ![alt](img.png) suite')).toBe('Texte suite');
  });

  it('supprime les citations', () => {
    expect(sanitizeForTTS('> Il murmura doucement')).toBe('Il murmura doucement');
  });

  it('supprime les listes a puces', () => {
    expect(sanitizeForTTS('- Premier\n- Deuxieme')).toBe('Premier Deuxieme');
  });

  it('supprime les listes numerotees', () => {
    expect(sanitizeForTTS('1. Premier\n2. Deuxieme')).toBe('Premier Deuxieme');
  });

  it('supprime le code inline', () => {
    expect(sanitizeForTTS('Utilise `const x = 1` ici')).toBe('Utilise const x = 1 ici');
  });

  it('supprime les blocs de code', () => {
    expect(sanitizeForTTS('Avant\n```\ncode\n```\nApres')).toBe('Avant Apres');
  });

  it('supprime le texte barre', () => {
    expect(sanitizeForTTS('~~ancien~~ nouveau')).toBe('ancien nouveau');
  });

  it('supprime les balises HTML', () => {
    expect(sanitizeForTTS('<p>Texte <strong>gras</strong></p>')).toBe('Texte gras');
  });

  it('preserve les apostrophes et accents francais', () => {
    expect(sanitizeForTTS("L'enfant s'approcha de l'\u00e9tang")).toBe(
      "L'enfant s'approcha de l'\u00e9tang"
    );
  });

  it('preserve les guillemets de dialogue', () => {
    expect(sanitizeForTTS('Elle dit : \u00ab Viens ici. \u00bb')).toBe('Elle dit : \u00ab Viens ici. \u00bb');
  });

  it('preserve la ponctuation narrative', () => {
    expect(sanitizeForTTS('Il hesita... puis avanca.')).toBe('Il hesita... puis avanca.');
  });

  it('preserve les tirets cadratins', () => {
    expect(sanitizeForTTS('Sofia \u2014 la plus jeune \u2014 sourit.')).toBe(
      'Sofia \u2014 la plus jeune \u2014 sourit.'
    );
  });

  it('ne touche pas aux asterisques dans un contexte non-markdown', () => {
    expect(sanitizeForTTS('Note * importante')).toBe('Note importante');
  });

  it('gere un texte deja propre', () => {
    const clean = 'Sofia marchait dans les rues de Naples.';
    expect(sanitizeForTTS(clean)).toBe(clean);
  });

  it('gere un texte vide', () => {
    expect(sanitizeForTTS('')).toBe('');
  });

  it('gere un melange de markdown', () => {
    const input =
      '# Scene 1\n\n**Sofia** regarda *Lorenzo* et dit :\n\n> Tu dois partir.\n\n---\n\nElle ferma la porte.';
    const expected = 'Scene 1 Sofia regarda Lorenzo et dit : Tu dois partir. Elle ferma la porte.';
    expect(sanitizeForTTS(input)).toBe(expected);
  });
});
