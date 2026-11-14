import { SEITENTITEL_MARKE, ausEinwurf, hinweisTitel } from './karten-daten';
import { SEITENTITEL_PRAEFIX } from '../einwerfen/einwerfen.component';
import { Einwurf } from '../services/einwurf.service';

/** Geteilte Einwuerfe sehen im Fangkorb nicht roh aus (Nutzerfuehrung 13.11., T3). */
describe('hinweisTitel', () => {
  it('nutzt dieselbe Marke wie das Einwerfen', () => {
    expect(SEITENTITEL_MARKE).toBe(SEITENTITEL_PRAEFIX);
  });

  it('trennt bei alten Einwuerfen „Seitentitel:“ ab und setzt den Rest mit Strich dahinter', () => {
    // So legte das Einwerfen den Vorschlag bis zur Persona-Runde 2 an (P44).
    const geteilt = 'Seitentitel: Windkraft: Neue Studie\nSchau mal, das passt';

    expect(hinweisTitel(geteilt)).toBe('Windkraft: Neue Studie – Schau mal, das passt');
    expect(hinweisTitel('Seitentitel:   Nur der Titel ')).toBe('Nur der Titel');
  });

  it('laesst einen Hinweis ohne Marke, wie er ist, und einen nackten Link weg', () => {
    expect(hinweisTitel('Mein Hinweis: Seitentitel: egal')).toBe('Mein Hinweis: Seitentitel: egal');
    expect(hinweisTitel('https://example.org', 'https://example.org')).toBeNull();
    expect(hinweisTitel('Seitentitel: ')).toBeNull();
  });

  it('zeigt die Karte im Fangkorb ohne Marke', () => {
    const karte = ausEinwurf({
      id: 'e-1',
      content: 'Seitentitel: Windkraft: Neue Studie',
      url: 'https://example.org/a',
      image_url: null,
      submitted_by: null,
      source_channel: 'share',
      status: 'open',
      created_at: '2026-11-13T10:00:00Z',
    } as Einwurf);

    expect(karte.titel).toBe('Windkraft: Neue Studie');
  });
});
