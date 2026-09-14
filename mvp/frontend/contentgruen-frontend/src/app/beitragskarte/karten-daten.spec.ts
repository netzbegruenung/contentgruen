import { ausBeitrag, ausEinwurf, ausSuchergebnis } from './karten-daten';
import { ContentResult } from '../services/dtos/contributionDtos';
import { RawInput, RawInputDraft, RawInputLink } from '../services/raw-input.service';

function inhalt(felder: Record<string, unknown> = {}): any {
  return {
    id: 'c-1',
    text: 'Text des Beitrags',
    content_type: 'commentary',
    created: '2026-09-13T12:00:00Z',
    last_modified: '2026-09-13T12:00:00Z',
    original_author: '0f3c2a9e-1111-2222-3333-444455556666',
    last_modified_by: '0f3c2a9e-1111-2222-3333-444455556666',
    title: 'Wärmepumpe lohnt sich auch im Altbau',
    references: [],
    usage_count: 3,
    ...felder,
  };
}

function paket(feld: string, felder: Record<string, unknown> = {}, rest: Record<string, unknown> = {}): any {
  return {
    score: 0.9,
    statement_text: '',
    statement_similarity_score: 0,
    reply_relevance: 0,
    [feld]: inhalt(felder),
    ...rest,
  };
}

function einwurf(felder: Partial<RawInput> = {}): RawInput {
  return {
    id: 'e-1',
    content: null,
    url: 'https://www.instagram.com/reel/ABC/',
    image_url: null,
    submitted_by: 'alice',
    source_channel: 'web',
    status: 'open',
    created_at: '2026-09-13T12:00:00Z',
    drafts: [],
    links: [],
    ...felder,
  };
}

function satz(id: string, user_id: string, sentence: string): RawInputDraft {
  return { id, user_id, sentence, updated_at: '2026-09-13T12:30:00Z' };
}

function link(draft_id: string | null, content_type: string | null = 'commentary', content_id = 'c-9'): RawInputLink {
  return { content_id, content_type, draft_id, processed_by: 'carol', processed_at: '2026-09-13T13:00:00Z' };
}

describe('karten-daten', () => {
  describe('ausSuchergebnis', () => {
    it('uebernimmt die gemeinsamen Felder eines Kommentars', () => {
      const daten = ausSuchergebnis(
        paket('commentary_result', {
          references: [
            { reference_id: 'r-1', created: '', reference_text: 'https://example.org', reference_description: 'Studie' },
          ],
        }),
      );

      expect(daten.id).toBe('c-1');
      expect(daten.typ).toBe('commentary');
      expect(daten.titel).toBe('Wärmepumpe lohnt sich auch im Altbau');
      expect(daten.text).toBe('Text des Beitrags');
      expect(daten.autor).toBe('0f3c2a9e-1111-2222-3333-444455556666');
      expect(daten.autorName).toBeNull();
      expect(daten.nutzung).toBe(3);
      expect(daten.quellen).toEqual([{ id: 'r-1', url: 'https://example.org', beschreibung: 'Studie' }]);
      expect(daten.rohling).toBeUndefined();
    });

    it('liest Kurz- und Langfassung eines Kommentars', () => {
      const daten = ausSuchergebnis(paket('commentary_result', { short_text: 'kurz', long_text: 'lang' }));

      expect(daten.extra).toEqual({ kurz: 'kurz', lang: 'lang' });
    });

    it('setzt das Statement nur, wenn es einen Text hat', () => {
      const mit = ausSuchergebnis(
        paket('commentary_result', {}, {
          statement_text: 'Lohnt sich eine Wärmepumpe?',
          statement_similarity_score: 0.873,
          reply_relevance: 0.5,
        }),
      );
      const ohne = ausSuchergebnis(paket('commentary_result', {}, { statement_text: '  ' }));

      expect(mit.statement).toEqual({ text: 'Lohnt sich eine Wärmepumpe?', aehnlichkeit: 87, antwortqualitaet: 50 });
      expect(ohne.statement).toBeUndefined();
    });

    it('uebernimmt nur eine gueltige Stimme', () => {
      expect(ausSuchergebnis(paket('generictext_result', {}, { user_vote: 'dislike' })).stimme).toBe('dislike');
      expect(ausSuchergebnis(paket('generictext_result', {}, { user_vote: null })).stimme).toBeUndefined();
    });

    it('erkennt den Typ am Ergebnisfeld und am expliziten Diskriminator', () => {
      expect(ausSuchergebnis(paket('generictext_result')).typ).toBe('generictext');
      expect(ausSuchergebnis(paket('generictext_result', {}, { content_type: 'generic_text' })).typ).toBe('generictext');
      expect(ausSuchergebnis(paket('commentary_result', {}, { result_type: 'commentary' })).typ).toBe('commentary');
    });

    it('liest die Post-Felder und die Bildadresse', () => {
      const post = ausSuchergebnis(
        paket('post_result', { platform: 'mastodon', author: '@gruen', url: 'https://social.example/1', engagement: 42 }),
      );
      const bild = ausSuchergebnis(paket('image_result', { image_url: 'https://example.org/dach.jpg' }));

      expect(post.typ).toBe('post');
      expect(post.extra).toEqual({
        plattform: 'mastodon',
        postAutor: '@gruen',
        postUrl: 'https://social.example/1',
        engagement: 42,
      });
      expect(bild.typ).toBe('image');
      expect(bild.bildUrl).toBe('https://example.org/dach.jpg');
    });

    it('zaehlt fehlende Nutzung als 0', () => {
      expect(ausSuchergebnis(paket('generictext_result', { usage_count: undefined })).nutzung).toBe(0);
    });

    it('warnt bei einer unbekannten Form und liefert eine Karte ohne Typ', () => {
      spyOn(console, 'warn');

      const daten = ausSuchergebnis({ score: 1, statement_text: null, statement_similarity_score: null, reply_relevance: null } as any);

      expect(daten.typ).toBeNull();
      expect(console.warn).toHaveBeenCalled();
    });
  });

  describe('ausBeitrag', () => {
    const eintrag = (felder: Partial<ContentResult> = {}): ContentResult => ({
      id: 'b-1',
      created: '2026-09-13T21:05:00',
      last_modified: '2026-09-13T21:05:00',
      original_author: 'person-1',
      last_modified_by: 'person-1',
      edit_history: {},
      text: 'Text',
      content_type: 'generic_text',
      score: 0,
      title: 'Erneuerbare senken Strompreise deutlich',
      usage_count: 12,
      ...felder,
    });

    it('bringt die Backend-Schreibweise des Typs auf den Registry-Schluessel', () => {
      const daten = ausBeitrag(eintrag());

      expect(daten.typ).toBe('generictext');
      expect(daten.titel).toBe('Erneuerbare senken Strompreise deutlich');
      expect(daten.nutzung).toBe(12);
      expect(daten.quellen).toEqual([]);
      expect(daten.statement).toBeUndefined();
    });

    it('uebernimmt die Bildadresse und kommt ohne Titel aus', () => {
      const daten = ausBeitrag(eintrag({ content_type: 'image', image_url: 'https://example.org/b.jpg', title: null }));

      expect(daten.typ).toBe('image');
      expect(daten.bildUrl).toBe('https://example.org/b.jpg');
      expect(daten.titel).toBeNull();
    });
  });

  describe('ausEinwurf', () => {
    it('liefert fuer einen Einwurf ohne Saetze genau die Einwurf-Karte', () => {
      const [karte, ...rest] = ausEinwurf(einwurf({ content: 'Gute Antwort in den Kommentaren' }));

      expect(rest).toEqual([]);
      expect(karte.typ).toBeNull();
      expect(karte.titel).toBeNull();
      expect(karte.rohling).toEqual({
        art: 'einwurf',
        einwurfId: 'e-1',
        zustand: 'offen',
        antippbar: true,
        plattform: 'Instagram',
        link: 'https://www.instagram.com/reel/ABC/',
        bildAdresse: null,
        hinweis: 'Gute Antwort in den Kommentaren',
        beteiligte: [{ rolle: 'eingeworfen', kennung: 'alice' }],
        suchSatz: null,
      });
    });

    it('wiederholt den Link nicht als Hinweis und kennt ohne Link keine Plattform', () => {
      expect(ausEinwurf(einwurf({ content: 'https://www.instagram.com/reel/ABC/' }))[0].rohling!.hinweis).toBeNull();
      expect(ausEinwurf(einwurf({ url: null, content: 'nur Text' }))[0].rohling!.plattform).toBeNull();
    });

    it('legt je Satz eine destillierte Karte unter den Einwurf', () => {
      const karten = ausEinwurf(
        einwurf({
          status: 'in_progress',
          drafts: [satz('s-1', 'bob', 'Satz von Bob'), satz('s-2', 'carol', 'Satz von Carol')],
        }),
      );

      expect(karten.length).toBe(3);
      expect(karten[0].rohling!.zustand).toBe('offen');
      expect(karten.slice(1).map((karte) => karte.titel)).toEqual(['Satz von Bob', 'Satz von Carol']);
      expect(karten[1].rohling).toEqual(
        jasmine.objectContaining({
          art: 'satz',
          einwurfId: 'e-1',
          zustand: 'destilliert',
          antippbar: true,
          beteiligte: [{ rolle: 'destilliert', kennung: 'bob' }],
          suchSatz: null,
        }),
      );
      expect(karten[1].typ).toBeNull();
    });

    it('leitet ausformuliert pro Satz aus den Verknuepfungen ab, nicht aus dem Einwurf-Status', () => {
      const karten = ausEinwurf(
        einwurf({
          status: 'in_progress',
          drafts: [satz('s-1', 'bob', 'Nicht genommen'), satz('s-2', 'dave', 'Genommen')],
          links: [link('s-2', 'generic_text')],
        }),
      );
      const [, offen, genommen] = karten;

      expect(offen.rohling!.zustand).toBe('destilliert');
      expect(genommen.rohling!.zustand).toBe('ausformuliert');
      expect(genommen.typ).toBe('generictext');
      expect(genommen.rohling!.beteiligte).toEqual([
        { rolle: 'destilliert', kennung: 'dave' },
        { rolle: 'ausformuliert', kennung: 'carol' },
      ]);
      expect(genommen.rohling!.suchSatz).toBe('Genommen');
    });

    it('macht aus mehreren Saetzen mehrere verschiedene Beitraege', () => {
      const karten = ausEinwurf(
        einwurf({
          status: 'processed',
          drafts: [satz('s-1', 'bob', 'Als Kommentar'), satz('s-2', 'bob', 'Als Hintergrund')],
          links: [link('s-1', 'commentary', 'c-1'), link('s-2', 'generic_text', 'c-2')],
        }),
      );

      expect(karten.slice(1).map((karte) => karte.typ)).toEqual(['commentary', 'generictext']);
    });

    it('gibt einer Verknuepfung ohne passenden Satz eine eigene Karte ohne Titel und Suche', () => {
      const karten = ausEinwurf(
        einwurf({
          status: 'processed',
          drafts: [satz('s-1', 'bob', 'Nie ausformuliert')],
          links: [link('s-geleert'), link(null, null, 'c-alt')],
        }),
      );

      expect(karten.length).toBe(4);
      expect(karten[1].rohling!.zustand).toBe('destilliert');
      const [geleert, alt] = karten.slice(2);
      expect(geleert.rohling!.zustand).toBe('ausformuliert');
      expect(geleert.titel).toBeNull();
      expect(geleert.typ).toBe('commentary');
      expect(geleert.rohling!.suchSatz).toBeNull();
      expect(alt.id).toBe('c-alt');
      expect(alt.typ).toBeNull();
    });

    it('macht einen verworfenen Einwurf samt Saetzen nicht antippbar', () => {
      const karten = ausEinwurf(einwurf({ status: 'discarded', drafts: [satz('s-1', 'bob', 'Satz')] }));

      expect(karten[0].rohling!.zustand).toBe('verworfen');
      expect(karten.every((karte) => karte.rohling!.antippbar === false)).toBeTrue();
    });
  });
});
