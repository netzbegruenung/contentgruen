import {
  KARTEN_JE_TYP,
  TYPFILTER_SCHLUESSEL,
  ansichtBauen,
  anzahlJeTyp,
  aufklappSchluessel,
  gruppieren,
  typFilterLesen,
  typFilterMerken,
} from './ergebnis-gruppen';

describe('ergebnis-gruppen', () => {
  const treffer = (feld: string, id: string, statementId: string | null, text: string, score: number) =>
    ({
      score,
      statement_id: statementId,
      statement_text: text,
      statement_similarity_score: 0.9,
      reply_relevance: 0.8,
      [feld]: { id, content_type: feld.replace('_result', ''), title: id, text: 'Text', references: [] },
    }) as any;

  const antwort = (teile: Record<string, any[]>) =>
    ({
      query_was_newly_added_as_statement: false,
      statement_id: null,
      statement_text: '',
      commentary_search_results_count: (teile['k'] ?? []).length,
      commentary_search_results: teile['k'] ?? [],
      generictext_search_results_count: (teile['h'] ?? []).length,
      generictext_search_results: teile['h'] ?? [],
      image_search_results: teile['b'],
      post_search_results: teile['p'],
    }) as any;

  describe('gruppieren', () => {
    it('gruppiert nach Aussage-ID, sonst Text; erkannte zuerst, dann nach bestem Treffer, direkte zuletzt', () => {
      const gruppen = gruppieren(
        antwort({
          k: [
            treffer('commentary_result', 'k-1', null, '', 0.99),
            treffer('commentary_result', 'k-2', 'b', 'B', 0.6),
            treffer('commentary_result', 'k-3', 'a', 'A', 0.5),
            treffer('commentary_result', 'k-4', null, ' C ', 0.7),
          ],
          b: [treffer('image_result', 'b-1', 'a', 'A', 0.4)],
        }),
        'a',
      );
      expect(gruppen.map((g) => [g.schluessel, g.art, g.text])).toEqual([
        ['a', 'erkannt', 'A'],
        ['text:C', 'aehnlich', 'C'],
        ['b', 'aehnlich', 'B'],
        ['ohne', 'ohne', null],
      ]);
      expect(gruppen[0].je.commentary.map((k) => k.id)).toEqual(['k-3']);
      expect(gruppen[0].je.image.map((k) => k.id)).toEqual(['b-1']);
      expect(gruppen[0].je.commentary[0].statement?.text).withContext('Aussage bleibt fuer die Werte der Admins').toBe('A');
    });

    it('nennt ohne erkannte Aussage jede Gruppe neutral', () => {
      const gruppen = gruppieren(antwort({ k: [treffer('commentary_result', 'k-1', 'a', 'A', 0.5)] }), null);
      expect(gruppen[0].art).toBe('aussage');
    });

    it('kommt mit fehlenden Feldern fuer Bilder und Posts zurecht', () => {
      expect(gruppieren(antwort({}), null)).toEqual([]);
      expect(anzahlJeTyp(antwort({ k: [treffer('commentary_result', 'k-1', null, '', 1)] }))).toEqual({
        commentary: 1,
        generictext: 0,
        image: 0,
        post: 0,
      });
      expect(anzahlJeTyp(null)).toEqual({ commentary: 0, generictext: 0, image: 0, post: 0 });
    });
  });

  describe('ansichtBauen', () => {
    const viele = (n: number) =>
      Array.from({ length: n }, (_, i) => treffer('commentary_result', `k-${i + 1}`, 'a', 'A', 1 - i / 100));
    const gruppen = () =>
      gruppieren(
        antwort({
          k: viele(5),
          h: [treffer('generictext_result', 'h-1', 'a', 'A', 0.5), treffer('generictext_result', 'h-2', 'b', 'B', 0.4)],
        }),
        'a',
      );

    it('begrenzt je Typ auf drei Karten und nennt den Rest im Knopf', () => {
      const [erste] = ansichtBauen(gruppen(), 'alle', new Set());
      const kommentare = erste.bloecke[0];
      expect(KARTEN_JE_TYP).toBe(3);
      expect(kommentare.karten.map((k) => k.id)).toEqual(['k-1', 'k-2', 'k-3']);
      expect(kommentare.alle).toBe(5);
      expect(kommentare.mehrText).toBe('Alle 5 Kommentare zeigen');
      expect(erste.anzahl).toBe(6);
    });

    it('zeigt aufgeklappt alle Karten ohne Knopf', () => {
      const [erste] = ansichtBauen(gruppen(), 'alle', new Set([aufklappSchluessel('a', 'commentary')]));
      expect(erste.bloecke[0].karten.length).toBe(5);
      expect(erste.bloecke[0].mehrText).toBeNull();
    });

    it('zeigt mit Filter nur den Typ und laesst Gruppen ohne ihn weg', () => {
      const ansicht = ansichtBauen(gruppen(), 'generictext', new Set());
      expect(ansicht.map((g) => [g.schluessel, g.bloecke.map((b) => b.typ), g.anzahl])).toEqual([
        ['a', ['generictext'], 1],
        ['b', ['generictext'], 1],
      ]);
      expect(ansichtBauen(gruppen(), 'image', new Set())).toEqual([]);
    });

    it('erklaert jeden Typ nur beim ersten Vorkommen und vergibt eindeutige Anker', () => {
      const ansicht = ansichtBauen(gruppen(), 'alle', new Set());
      expect(ansicht.flatMap((g) => g.bloecke.map((b) => [b.id, b.ueberschrift, !!b.erklaerung]))).toEqual([
        ['ergebnis-gruppe-0-commentary', 'Kommentare', true],
        ['ergebnis-gruppe-0-generictext', 'Hintergrundinfo', true],
        ['ergebnis-gruppe-1-generictext', 'Hintergrundinfo', false],
      ]);
    });
  });

  describe('Typwahl in der Sitzung', () => {
    afterEach(() => sessionStorage.removeItem(TYPFILTER_SCHLUESSEL));

    it('merkt einen Typ, vergisst "Alle" und ignoriert Unbekanntes', () => {
      typFilterMerken('image');
      expect(typFilterLesen()).toBe('image');
      typFilterMerken('alle');
      expect(sessionStorage.getItem(TYPFILTER_SCHLUESSEL)).toBeNull();
      sessionStorage.setItem(TYPFILTER_SCHLUESSEL, 'unsinn');
      expect(typFilterLesen()).toBe('alle');
    });

    it('wirft nicht, wenn der Storage gesperrt ist', () => {
      spyOn(Storage.prototype, 'getItem').and.throwError('gesperrt');
      spyOn(Storage.prototype, 'setItem').and.throwError('gesperrt');
      expect(typFilterLesen()).toBe('alle');
      expect(() => typFilterMerken('post')).not.toThrow();
    });
  });
});
