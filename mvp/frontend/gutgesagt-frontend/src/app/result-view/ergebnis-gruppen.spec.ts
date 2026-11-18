import {
  KARTEN_JE_TYP,
  OFFENE_WEITERE_DESKTOP,
  ansichtBauen,
  anzahlJeTyp,
  anzahlSichtbar,
  aufklappSchluessel,
  besteHervorheben,
  istWeniger,
  mitZweiterSpalte,
  gruppieren,
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

  describe('weniger passende Gruppen', () => {
    const daten = () =>
      antwort({
        k: [
          treffer('commentary_result', 'k-1', 'a', 'A', 0.9),
          treffer('commentary_result', 'k-2', 'b', 'B', 0.95),
          treffer('commentary_result', 'k-3', null, '', 0.6),
        ],
        b: [treffer('image_result', 'b-1', 'a', 'A', 0.8)],
      });

    it('sind mit erkannter Aussage alle anderen, gezaehlt wird nur die erkannte', () => {
      const gruppen = gruppieren(daten(), 'a');
      expect(gruppen.map((g) => istWeniger(g, gruppen))).toEqual([false, true, true]);
      expect(anzahlSichtbar(gruppen)).toEqual({ commentary: 1, generictext: 0, image: 1, post: 0 });
      expect(ansichtBauen(gruppen, new Set()).map((g) => g.weniger)).toEqual([false, true, true]);
    });

    it('gibt es ohne erkannte Aussage nicht', () => {
      const gruppen = gruppieren(daten(), null);
      expect(gruppen.some((g) => istWeniger(g, gruppen))).toBeFalse();
      expect(anzahlSichtbar(gruppen)).toEqual({ commentary: 3, generictext: 0, image: 1, post: 0 });
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
      const [erste] = ansichtBauen(gruppen(), new Set());
      const kommentare = erste.bloecke[0];
      expect(KARTEN_JE_TYP).toBe(3);
      expect(kommentare.karten.map((k) => k.id)).toEqual(['k-1', 'k-2', 'k-3']);
      expect(kommentare.alle).toBe(5);
      expect(kommentare.mehrText).toBe('Alle 5 Kommentare zeigen');
      expect(erste.anzahl).toBe(6);
    });

    it('zeigt aufgeklappt alle Karten ohne Knopf', () => {
      const [erste] = ansichtBauen(gruppen(), new Set([aufklappSchluessel('a', 'commentary')]));
      expect(erste.bloecke[0].karten.length).toBe(5);
      expect(erste.bloecke[0].mehrText).toBeNull();
    });

    it('vergibt jedem Block eine Ueberschrift und einen eindeutigen Anker', () => {
      const ansicht = ansichtBauen(gruppen(), new Set());
      expect(ansicht.flatMap((g) => g.bloecke.map((b) => [b.id, b.ueberschrift]))).toEqual([
        ['ergebnis-gruppe-0-commentary', 'Kommentare'],
        ['ergebnis-gruppe-0-generictext', 'Hintergrundinfo'],
        ['ergebnis-gruppe-1-generictext', 'Hintergrundinfo'],
      ]);
    });
  });

  describe('besteHervorheben (V3, Designrunde 17.11.)', () => {
    const ansicht = (erkannt: string | null) =>
      ansichtBauen(
        gruppieren(
          antwort({
            k: [
              treffer('commentary_result', 'k-1', 'a', 'A', 0.9),
              treffer('commentary_result', 'k-2', 'a', 'A', 0.8),
              treffer('commentary_result', 'k-3', 'b', 'B', 0.7),
            ],
            h: [treffer('generictext_result', 'h-1', 'a', 'A', 0.5)],
          }),
          erkannt,
        ),
        new Set(),
      );

    it('stellt die erste Karte der erkannten Gruppe als beste heraus, den Rest darunter mit Titel und Zahl', () => {
      const [erste, zweite] = besteHervorheben(ansicht('a'));
      expect(erste.bloecke.map((b) => [b.beste?.id ?? null, b.weitere.map((k) => k.id), b.weitereTitel])).toEqual([
        ['k-1', ['k-2'], 'Weitere Antworten · 1'],
        [null, ['h-1'], 'Hintergrundinfo · 1'],
      ]);
      expect(zweite.weniger).toBeTrue();
      expect(zweite.bloecke[0].beste).withContext('weniger passende Gruppen haben keine beste').toBeNull();
      expect(zweite.bloecke[0].weitereTitel).toBe('Kommentar · 1');
    });

    it('nimmt ohne erkannte Aussage die erste Gruppe und laesst die Karten dieselben Objekte', () => {
      const vorher = ansicht(null);
      const nachher = besteHervorheben(vorher);
      expect(nachher.filter((g) => g.bloecke.some((b) => b.beste)).length).toBe(1);
      expect(nachher[0].bloecke[0].beste).toBe(vorher[0].bloecke[0].karten[0]);
      expect(nachher[1]).withContext('andere Gruppen unveraendert').toBe(vorher[1]);
    });

    it('nennt andere Typen als Kommentar in der Mehrzahl', () => {
      const nurHintergrund = ansichtBauen(
        gruppieren(antwort({ h: [treffer('generictext_result', 'h-1', 'a', 'A', 0.5), treffer('generictext_result', 'h-2', 'a', 'A', 0.4)] }), 'a'),
        new Set(),
      );
      expect(besteHervorheben(nurHintergrund)[0].bloecke[0].weitereTitel).toBe('Weitere Hintergrundinfos · 1');
      expect(besteHervorheben([])).toEqual([]);
    });

    it('stellt jede Gruppe mit bester Antwort zweispaltig, auch mit nur einer Antwort', () => {
      const [erste, zweite] = besteHervorheben(ansicht('a'));
      expect(mitZweiterSpalte(erste)).toBeTrue();
      expect(mitZweiterSpalte(zweite)).withContext('ohne beste Antwort').toBeFalse();
      const eine = [treffer('commentary_result', 'k-1', 'a', 'A', 0.9)];
      const allein = besteHervorheben(ansichtBauen(gruppieren(antwort({ k: eine }), 'a'), new Set()));
      expect(mitZweiterSpalte(allein[0])).withContext('nur eine Antwort: der Kasten steht trotzdem daneben').toBeTrue();
      expect(mitZweiterSpalte(undefined)).toBeFalse();
    });

    it('zaehlt im Knopf wie in der Ueberschrift, ohne die beste Antwort', () => {
      const vier = Array.from({ length: 4 }, (_, i) => treffer('commentary_result', `k-${i + 1}`, 'a', 'A', 1 - i / 100));
      const [block] = besteHervorheben(ansichtBauen(gruppieren(antwort({ k: vier }), 'a'), new Set()))[0].bloecke;
      expect(block.weitereTitel).toBe('Weitere Antworten · 3');
      expect(block.mehrText).toBe('Alle 3 weiteren Antworten zeigen');
      expect(block.offen).withContext('am Handy keine offenen weiteren').toEqual([]);
    });
  });

  describe('Desktop: fuenf Antworten offen (Maintainer 18.11.)', () => {
    const kommentare = (n: number, aussage = 'a') =>
      Array.from({ length: n }, (_, i) => treffer('commentary_result', `k-${i + 1}`, aussage, aussage.toUpperCase(), 1 - i / 100));
    const desktop = (teile: Record<string, any[]>, aufgeklappt = new Set<string>()) =>
      besteHervorheben(
        ansichtBauen(gruppieren(antwort(teile), 'a'), aufgeklappt, OFFENE_WEITERE_DESKTOP),
        OFFENE_WEITERE_DESKTOP,
      );

    it('stellt nach der besten die naechsten vier offen, dann zwei eingeklappt, der Knopf zaehlt den Rest', () => {
      expect(OFFENE_WEITERE_DESKTOP).toBe(4);
      const [block] = desktop({ k: kommentare(9) })[0].bloecke;
      expect(block.beste?.id).toBe('k-1');
      expect(block.offen.map((k) => k.id)).toEqual(['k-2', 'k-3', 'k-4', 'k-5']);
      expect(block.weitere.map((k) => k.id)).toEqual(['k-6', 'k-7']);
      expect(block.karten.length).withContext('Fokus-Index nach "Alle zeigen"').toBe(7);
      expect(block.weitereTitel).toBe('Weitere Antworten · 8');
      expect(block.mehrText).toBe('Alle 4 weiteren Antworten zeigen');
    });

    it('zeigt bei weniger als fuenf Antworten alle offen, ohne Knopf', () => {
      const [block] = desktop({ k: kommentare(3) })[0].bloecke;
      expect(block.offen.map((k) => k.id)).toEqual(['k-2', 'k-3']);
      expect(block.weitere).toEqual([]);
      expect(block.mehrText).toBeNull();
    });

    it('zeigt aufgeklappt alle: vier offen, der Rest eingeklappt', () => {
      const [block] = desktop({ k: kommentare(9) }, new Set([aufklappSchluessel('a', 'commentary')]))[0].bloecke;
      expect(block.offen.length).toBe(4);
      expect(block.weitere.length).toBe(4);
      expect(block.mehrText).toBeNull();
    });

    it('laesst andere Typen und weniger passende Gruppen wie bisher', () => {
      const hintergrund = Array.from({ length: 5 }, (_, i) => treffer('generictext_result', `h-${i + 1}`, 'a', 'A', 0.5 - i / 100));
      const [erste, zweite] = desktop({ k: [...kommentare(2), ...kommentare(5, 'b')], h: hintergrund });
      const hBlock = erste.bloecke[1];
      expect(hBlock.offen).toEqual([]);
      expect(hBlock.weitere.length).toBe(KARTEN_JE_TYP);
      expect(hBlock.mehrText).toBe('Alle 5 Hintergrundinfos zeigen');
      expect(zweite.weniger).toBeTrue();
      expect(zweite.bloecke[0].offen).toEqual([]);
      expect(zweite.bloecke[0].weitere.length).toBe(KARTEN_JE_TYP);
    });
  });
});
