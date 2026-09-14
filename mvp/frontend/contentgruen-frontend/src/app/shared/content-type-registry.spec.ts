import { CONTENT_TYPE_REGISTRY, typLabel } from './content-type-registry';

describe('content-type-registry', () => {
  describe('typLabel', () => {
    it('liefert die deutschen Namen aus dem label-Feld', () => {
      expect(typLabel('commentary')).toBe('Kommentar');
      expect(typLabel('image')).toBe('Bild');
      expect(typLabel('post')).toBe('Post');
      expect(typLabel('statement')).toBe('Aussage');
      expect(typLabel('reference')).toBe('Herkunft');
    });

    it('versteht beide Schreibweisen der Hintergrundinfo', () => {
      expect(typLabel('generic_text')).toBe('Hintergrundinfo');
      expect(typLabel('generictext')).toBe('Hintergrundinfo');
    });

    it('gibt einen unbekannten Typ unveraendert zurueck und macht aus nichts einen leeren Text', () => {
      expect(typLabel('podcast')).toBe('podcast');
      expect(typLabel(null)).toBe('');
      expect(typLabel(undefined)).toBe('');
    });
  });

  it('fuehrt Aussage und Herkunft ohne Ergebnisfeld, also ohne Suchkarte', () => {
    expect(CONTENT_TYPE_REGISTRY['statement'].resultField).toBeUndefined();
    expect(CONTENT_TYPE_REGISTRY['reference'].resultField).toBeUndefined();
  });

  it('gibt jedem Typ mit Suchkarte ein Symbol fuer den Kartenkopf', () => {
    for (const config of Object.values(CONTENT_TYPE_REGISTRY)) {
      if (config.resultField) {
        expect(config.emoji).withContext(config.key).toBeTruthy();
      }
    }
  });
});
