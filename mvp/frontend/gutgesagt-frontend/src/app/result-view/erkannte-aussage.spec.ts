import { aussageZumAntworten } from './erkannte-aussage';
import { SearchResponse } from '../services/dtos/searchDtos';

describe('aussageZumAntworten', () => {
  const SUCHE = '11111111-2222-4333-8444-555555555555';
  const ERKANNT = '22222222-2222-4333-8444-555555555555';
  const ANDERE = '33333333-2222-4333-8444-555555555555';

  const kommentar = (statement_id: string | null, statement_text: string, score: number) =>
    ({ score, statement_id, statement_text, statement_similarity_score: 0.9, reply_relevance: 0.8, commentary_result: {} }) as any;

  function antwort(statementId: string | null, treffer: any[]): SearchResponse {
    return {
      query_was_newly_added_as_statement: true,
      statement_id: statementId,
      statement_text: 'heizung verbieten',
      commentary_search_results_count: treffer.length,
      commentary_search_results: treffer,
      generictext_search_results_count: 0,
      generictext_search_results: [],
    };
  }

  it('nimmt die erkannte Aussage statt der eigenen der Suche', () => {
    const treffer = [kommentar(ERKANNT, 'Die Grünen wollen mir meine Heizung verbieten!', 0.9), kommentar(ANDERE, 'Fleisch', 0.6)];
    expect(aussageZumAntworten(antwort(SUCHE, treffer))).toBe(ERKANNT);
  });

  it('nimmt die der Suche, wenn keine Aussage erkannt ist', () => {
    // Verteilt: Die haeufigste traegt weder den obersten Treffer noch die Mehrheit.
    const VIERTE = '44444444-2222-4333-8444-555555555555';
    const treffer = [
      kommentar(ERKANNT, 'A', 0.9),
      kommentar(ANDERE, 'B', 0.5),
      kommentar(ANDERE, 'B', 0.4),
      kommentar(VIERTE, 'C', 0.3),
    ];
    expect(aussageZumAntworten(antwort(SUCHE, treffer))).toBe(SUCHE);
    expect(aussageZumAntworten(antwort(SUCHE, []))).toBe(SUCHE);
  });

  it('nimmt eine erkannte Aussage ohne ID nicht, und keine ungueltige ID', () => {
    expect(aussageZumAntworten(antwort('None', [kommentar(null, 'Nur Text', 0.9)]))).toBeNull();
    expect(aussageZumAntworten(null)).toBeNull();
  });
});
