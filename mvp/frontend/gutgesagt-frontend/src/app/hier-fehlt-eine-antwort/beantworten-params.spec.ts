import { convertToParamMap } from '@angular/router';

import { beantwortenParams } from './hier-fehlt-eine-antwort.component';
import { gesuchtAus, lueckeZuSatz } from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';

describe('beantwortenParams und "Lücke zu" (Nutzerfuehrung 13.11.)', () => {
  it('nimmt die Nachfrage als ?gesucht= mit, nur wenn es eine gibt', () => {
    expect(beantwortenParams({ statement_id: 'a-1', personen_ohne_treffer: 2 })).toEqual({
      aussage: 'a-1',
      von: 'hier-fehlt-eine-antwort',
      gesucht: '2',
    });
    expect(beantwortenParams({ statement_id: 'a-1', personen_ohne_treffer: 0 })).toEqual({
      aussage: 'a-1',
      von: 'hier-fehlt-eine-antwort',
    });
    expect(beantwortenParams({ statement_id: 'a-1' })).toEqual({ aussage: 'a-1', von: 'hier-fehlt-eine-antwort' });
  });

  it('liest ?gesucht= nur als positive Zahl', () => {
    expect(gesuchtAus(convertToParamMap({ gesucht: '4' }))).toBe(4);
    expect(gesuchtAus(convertToParamMap({ gesucht: 'viele' }))).toBe(0);
    expect(gesuchtAus(convertToParamMap({ gesucht: '-1' }))).toBe(0);
    expect(gesuchtAus(convertToParamMap({}))).toBe(0);
  });

  it('formuliert den Satz je nach Zahl', () => {
    expect(lueckeZuSatz(3)).toBe('3 Personen haben danach gesucht, ab jetzt finden sie was.');
    expect(lueckeZuSatz(1)).toBe('Eine Person hat danach gesucht, ab jetzt findet sie was.');
    expect(lueckeZuSatz(0)).toBe('Wer danach sucht, findet ab jetzt deine Antwort.');
  });
});
