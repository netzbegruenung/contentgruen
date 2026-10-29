import { ausBeitrag, ausEinwurf, ausSuchergebnis } from './karten-daten';
import { ContentResult } from '../services/dtos/contributionDtos';
import { Einwurf, Satz, Verknuepfung } from '../services/einwurf.service';

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

function einwurf(felder: Partial<Einwurf> = {}): Einwurf {
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

function satz(id: string, user_id: string, sentence: string): Satz {
  return { id, user_id, sentence, updated_at: '2026-09-13T12:30:00Z' };
}

function link(draft_id: string | null, content_type: string | null = 'commentary', content_id = 'c-9'): Verknuepfung {
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
      expect(daten.einwurfAngaben).toBeUndefined();
    });

    it('nimmt den Anzeigenamen vom Inhalt', () => {
      expect(ausSuchergebnis(paket('commentary_result', { autor_name: 'Kim' })).autorName).toBe('Kim');
    });

    it('uebernimmt das Kennzeichen eigener Beitrag vom Server (#333)', () => {
      const ohneKennung = { original_author: undefined };
      expect(ausSuchergebnis(paket('commentary_result', { ...ohneKennung, ist_eigener_beitrag: true })).eigen).toBeTrue();
      expect(ausSuchergebnis(paket('commentary_result', { ...ohneKennung, ist_eigener_beitrag: false })).eigen).toBeFalse();
      expect(ausSuchergebnis(paket('commentary_result', { ...ohneKennung, ist_eigener_beitrag: null })).eigen).toBeNull();
      expect(ausSuchergebnis(paket('commentary_result', ohneKennung)).autor).toBeNull();
    });

    it('macht aus der leeren Kennung einer anonymen Antwort null', () => {
      const daten = ausSuchergebnis(paket('commentary_result', { original_author: '' }));

      expect(daten.autor).toBeNull();
      expect(daten.autorName).toBeNull();
    });

    it('liest Kurz- und Langfassung eines Kommentars', () => {
      const daten = ausSuchergebnis(paket('commentary_result', { short_text: 'kurz', long_text: 'lang' }));

      expect(daten.extra).toEqual({ kurz: 'kurz', lang: 'lang' });
    });

    it('liest Zweck und Stil eines Kommentars (#357)', () => {
      const eigene = ausSuchergebnis(paket('commentary_result', { zweck: 'eigene_leute', style: 'bissig' }));
      const spalte = ausSuchergebnis(paket('commentary_result', { zweck: 'kommentarspalte', style: null }));
      const ohneAngabe = ausSuchergebnis(paket('commentary_result'));

      expect(eigene.extra?.fuerEigeneLeute).toBeTrue();
      expect(eigene.extra?.stil).toBe('bissig');
      expect(spalte.extra?.fuerEigeneLeute).toBeFalsy();
      expect(spalte.extra?.stil).toBeUndefined();
      expect(ohneAngabe.extra?.fuerEigeneLeute).toBeFalsy();
    });

    it('laesst einen unbekannten Stil weg', () => {
      expect(ausSuchergebnis(paket('commentary_result', { style: 'sarkastisch' })).extra?.stil).toBeUndefined();
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

    it('zeigt keine Interaktionen, wenn keine erfasst sind', () => {
      // Das Post-Formular fragt sie nicht ab; gespeichert wird dann 0.
      const post = ausSuchergebnis(paket('post_result', { platform: 'Instagram', author: '@a', engagement: 0 }));

      expect(post.extra?.engagement).toBeUndefined();
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
      original_author: 'person-1',
      text: 'Text',
      content_type: 'generic_text',
      score: 0,
      title: 'Erneuerbare senken Strompreise deutlich',
      usage_count: 12,
      ...felder,
    });

    it('erkennt den eigenen Beitrag in Meine Beitraege am Kennzeichen, ohne Kennung (#385)', () => {
      const meiner = eintrag({ original_author: null, ist_eigener_beitrag: true });

      expect(ausBeitrag(meiner).eigen).toBeTrue();
      expect(ausBeitrag(meiner).autor).toBeNull();
    });

    it('uebernimmt Nutzung und Zuwachs der letzten 7 Tage', () => {
      const daten = ausBeitrag(eintrag({ nutzung_letzte_7_tage: 4 }));

      expect([daten.nutzung, daten.nutzungLetzte7Tage]).toEqual([12, 4]);
      expect(ausBeitrag(eintrag()).nutzungLetzte7Tage).toBe(0);
    });

    it('uebernimmt am Kommentar die Fassungen und die Nutzung je Fassung (#355)', () => {
      const je = { kurz: { nutzung: 3, letzte_7_tage: 1 }, mittel: { nutzung: 4, letzte_7_tage: 0 } };
      const daten = ausBeitrag(
        eintrag({ content_type: 'commentary', short_text: 'Kurz.', long_text: ' ', nutzung_je_fassung: je }),
      );

      expect(daten.extra).toEqual({ kurz: 'Kurz.', lang: undefined });
      expect(daten.nutzungJeFassung).toEqual(je);
    });

    it('laesst Fassungen bei anderen Beitragstypen weg', () => {
      const daten = ausBeitrag(eintrag({ short_text: 'Kurz.' }));

      expect(daten.extra).toBeUndefined();
      expect(daten.nutzungJeFassung).toBeUndefined();
    });

    it('uebernimmt das Kennzeichen eigener Beitrag aus dem Einzelabruf (#333)', () => {
      // Das Beitrag-Sheet im Fangkorb laedt per getById: ohne Kennung, mit Kennzeichen.
      const ohneKennung = eintrag({ original_author: null, ist_eigener_beitrag: true });

      expect(ausBeitrag(ohneKennung).eigen).toBeTrue();
      expect(ausBeitrag(ohneKennung).autor).toBeNull();
      expect(ausBeitrag(eintrag()).eigen).toBeNull();
    });

    it('uebernimmt den Anzeigenamen aus dem Einzelabruf', () => {
      expect(ausBeitrag(eintrag({ autor_name: 'Anna B.' })).autorName).toBe('Anna B.');
      expect(ausBeitrag(eintrag()).autorName).toBeNull();
    });

    it('bringt die Backend-Schreibweise des Typs auf den Registry-Schluessel', () => {
      const daten = ausBeitrag(eintrag());

      expect(daten.typ).toBe('generictext');
      expect(daten.titel).toBe('Erneuerbare senken Strompreise deutlich');
      expect(daten.nutzung).toBe(12);
      expect(daten.quellen).toEqual([]);
      expect(daten.statement).toBeUndefined();
    });

    it('uebernimmt die Herkunft mit Adresse und Beschreibung', () => {
      const daten = ausBeitrag(
        eintrag({
          references: [
            {
              reference_id: 'r-1',
              created: '2026-09-01T10:00:00',
              reference_text: 'https://example.org/studie',
              reference_description: 'Studie des Umweltbundesamts',
            },
          ],
        }),
      );

      expect(daten.quellen).toEqual([
        { id: 'r-1', url: 'https://example.org/studie', beschreibung: 'Studie des Umweltbundesamts' },
      ]);
    });

    it('zeigt ein Bild ohne Unterschrift mit Titel, ohne Titel mit der Domain der Bildadresse', () => {
      const mitTitel = ausBeitrag(
        eintrag({ content_type: 'image', text: null, title: 'Solardach', image_url: 'https://www.example.org/b.jpg' }),
      );
      expect(mitTitel.titel).toBe('Solardach');
      expect(mitTitel.text).toBeNull();

      const ohneTitel = ausBeitrag(
        eintrag({ content_type: 'image', text: null, title: null, image_url: 'https://www.example.org/b.jpg' }),
      );
      expect(ohneTitel.titel).toBe('example.org');
      expect(ohneTitel.text).toBeNull();
    });

    it('uebernimmt die Bildadresse und kommt ohne Titel aus', () => {
      const daten = ausBeitrag(eintrag({ content_type: 'image', image_url: 'https://example.org/b.jpg', title: null }));

      expect(daten.typ).toBe('image');
      expect(daten.bildUrl).toBe('https://example.org/b.jpg');
      expect(daten.titel).toBeNull();
    });
  });

  describe('ausEinwurf', () => {
    it('macht aus einem Einwurf genau eine Karte mit dem Hinweis als Titel', () => {
      const karte = ausEinwurf(einwurf({ content: 'Gute Antwort in den Kommentaren' }));

      expect(karte.id).toBe('e-1');
      expect(karte.typ).toBeNull();
      expect(karte.titel).toBe('Gute Antwort in den Kommentaren');
      expect(karte.autor).toBe('alice');
      expect(karte.einwurfAngaben).toEqual({
        einwurfId: 'e-1',
        stufe: 'offen',
        herkunft: 'Instagram',
        link: 'https://www.instagram.com/reel/ABC/',
        linkText: 'instagram.com/reel/ABC',
        saetze: [],
        beitraege: [],
        verwerfbar: true,
      });
    });

    it('uebernimmt das Kennzeichen eigener Einwurf vom Server (#385)', () => {
      expect(ausEinwurf(einwurf({ submitted_by: null, ist_eigener_einwurf: true })).eigen).toBeTrue();
      expect(ausEinwurf(einwurf({ submitted_by: null, ist_eigener_einwurf: false })).eigen).toBeFalse();
      expect(ausEinwurf(einwurf({ submitted_by: null })).eigen).toBeNull();
    });

    it('nennt den Einwerfer beim Anzeigenamen, sonst ohne Namen', () => {
      expect(ausEinwurf(einwurf({ submitted_by_name: 'Jürgen Ö.' })).autorName).toBe('Jürgen Ö.');
      expect(ausEinwurf(einwurf()).autorName).toBeNull();
    });

    it('laesst ohne Hinweis den Titel leer - die Link-Zeile ist dann die Aufschrift', () => {
      const karte = ausEinwurf(einwurf({ url: 'https://beispiel-zeitung.de/artikel/1' }));

      expect(karte.titel).toBeNull();
      expect(karte.einwurfAngaben!.herkunft).toBe('beispiel-zeitung.de');
      expect(karte.einwurfAngaben!.linkText).toBe('beispiel-zeitung.de/artikel/1');
    });

    it('wiederholt den Link nicht als Titel', () => {
      expect(ausEinwurf(einwurf({ content: 'https://www.instagram.com/reel/ABC/' })).titel).toBeNull();
    });

    it('kuerzt die Adresse auf Domain und Pfad, ohne Schema, www und Abfrage', () => {
      const karte = ausEinwurf(
        einwurf({ url: 'https://www.tagesschau.de/inland/heizung-101.html?utm_source=x#top' }),
      );

      expect(karte.einwurfAngaben!.linkText).toBe('tagesschau.de/inland/heizung-101.html');
    });

    it('nimmt bei einem Bild-Einwurf die Bildadresse als Link', () => {
      const karte = ausEinwurf(einwurf({ url: null, image_url: 'https://bilder.example.org/1.jpg' }));

      expect(karte.einwurfAngaben!.link).toBe('https://bilder.example.org/1.jpg');
      expect(karte.einwurfAngaben!.linkText).toBe('bilder.example.org/1.jpg');
      expect(karte.titel).toBeNull();
    });

    it('legt die Saetze in die Karte und zaehlt je Satz die Beitraege daraus', () => {
      const karte = ausEinwurf(
        einwurf({
          status: 'processed',
          drafts: [satz('s-1', 'bob', 'Ohne Beitrag geblieben'), satz('s-2', 'bob', 'Zweimal genommen')],
          links: [link('s-2', 'commentary', 'c-1'), link('s-2', 'generic_text', 'c-2')],
        }),
      );

      expect(karte.einwurfAngaben!.saetze).toEqual([
        { id: 's-1', text: 'Ohne Beitrag geblieben', beitraege: 0 },
        { id: 's-2', text: 'Zweimal genommen', beitraege: 2 },
      ]);
      expect(karte.einwurfAngaben!.stufe).toBe('ausformuliert');
    });

    it('haelt jeden Beitrag fuer das Sheet bereit, auch ohne Satz und ohne Typ', () => {
      const karte = ausEinwurf(
        einwurf({
          status: 'processed',
          drafts: [satz('s-1', 'bob', 'Genommen')],
          links: [link('s-1', 'commentary', 'c-1'), link(null, null, 'c-alt')],
        }),
      );

      expect(karte.einwurfAngaben!.beitraege).toEqual([
        { contentId: 'c-1', typ: 'commentary', satz: 'Genommen' },
        { contentId: 'c-alt', typ: null, satz: null },
      ]);
    });

    it('nimmt fuer Farbe und Zeichen die erste Verknuepfung mit Typ', () => {
      const karte = ausEinwurf(
        einwurf({
          status: 'processed',
          drafts: [satz('s-1', 'bob', 'Alt'), satz('s-2', 'bob', 'Neu')],
          // Die aelteste Verknuepfung stammt aus der Zeit vor Fangkorb v2 und
          // traegt keinen Typ - die Karte soll trotzdem Farbe bekennen.
          links: [link('s-1', null, 'c-alt'), link('s-2', 'generic_text', 'c-neu')],
        }),
      );

      expect(karte.typ).toBe('generictext');
    });

    it('bleibt ohne jeden Typ farblos', () => {
      const karte = ausEinwurf(
        einwurf({ status: 'processed', links: [link(null, null, 'c-alt')] }),
      );

      expect(karte.typ).toBeNull();
    });

    it('nennt einen Einwurf mit Satz, aber ohne Beitrag ausformulierbar', () => {
      const karte = ausEinwurf(
        einwurf({ status: 'in_progress', drafts: [satz('s-1', 'bob', 'Ein Satz')] }),
      );

      expect(karte.einwurfAngaben!.stufe).toBe('destilliert');
      expect(karte.einwurfAngaben!.verwerfbar).toBeTrue();
    });

    it('bleibt verworfen, auch wenn jemand anderes dazu einen Satz hat', () => {
      const karte = ausEinwurf(einwurf({ status: 'discarded', drafts: [satz('s-1', 'bob', 'Satz')] }));

      expect(karte.einwurfAngaben!.stufe).toBe('verworfen');
      expect(karte.einwurfAngaben!.verwerfbar).toBeFalse();
      expect(karte.einwurfAngaben!.saetze.length).toBe(1);
    });

    it('laesst einen ausformulierten Einwurf nicht mehr verwerfen', () => {
      const karte = ausEinwurf(einwurf({ status: 'processed', links: [link(null, 'commentary')] }));

      expect(karte.einwurfAngaben!.stufe).toBe('ausformuliert');
      expect(karte.einwurfAngaben!.verwerfbar).toBeFalse();
    });
  });
});
