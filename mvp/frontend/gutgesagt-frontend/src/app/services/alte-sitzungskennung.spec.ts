import { alteSitzungskennungEntfernen } from './alte-sitzungskennung';

/**
 * Bis #446 legte die SPA eine Sitzungskennung im localStorage ab. Sie wird nicht
 * mehr gebraucht; was noch in Browsern liegt, raeumt der Start der App weg.
 */
describe('alteSitzungskennungEntfernen', () => {
  function speicher(eintraege: Record<string, string>): Storage {
    const daten = { ...eintraege };
    return {
      getItem: (k: string) => (k in daten ? daten[k] : null),
      setItem: (k: string, v: string) => { daten[k] = v; },
      removeItem: (k: string) => { delete daten[k]; },
      clear: () => Object.keys(daten).forEach((k) => delete daten[k]),
      key: (i: number) => Object.keys(daten)[i] ?? null,
      get length() { return Object.keys(daten).length; },
    } as Storage;
  }

  it('entfernt die Kennung und ihren Zeitstempel', () => {
    const s = speicher({
      gutgesagt_session_id: '12345678-1234-4234-8234-123456789012',
      gutgesagt_session_id_created_at: '1700000000000',
    });

    alteSitzungskennungEntfernen(s);

    expect(s.getItem('gutgesagt_session_id')).toBeNull();
    expect(s.getItem('gutgesagt_session_id_created_at')).toBeNull();
  });

  it('laesst andere Eintraege stehen', () => {
    const s = speicher({ gutgesagt_session_id: 'x', anderes: 'bleibt' });

    alteSitzungskennungEntfernen(s);

    expect(s.getItem('anderes')).toBe('bleibt');
  });

  it('scheitert nicht, wenn der Speicher gesperrt ist', () => {
    const gesperrt = {
      removeItem: () => { throw new DOMException('blockiert', 'SecurityError'); },
    } as unknown as Storage;

    expect(() => alteSitzungskennungEntfernen(gesperrt)).not.toThrow();
  });

  it('scheitert nicht ohne Speicher', () => {
    expect(() => alteSitzungskennungEntfernen(null)).not.toThrow();
  });
});
