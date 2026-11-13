import { SearchResponse } from '../services/dtos/searchDtos';
import { BaseSearchResult } from '../services/dtos/commonDtos';
import { istAussageId } from '../shared/formular-adresse';

/*
 * Die erkannte Aussage einer Suche ("Gefunden zu", #642): eigene Datei, damit die
 * Ergebnisseite und ihre Trefferlisten (Kommentare, Hintergrundinfos) dieselbe Regel
 * nutzen, ohne einander zu importieren.
 */

/** Die Aussage, als die die Suche verstanden wurde: ID (falls bekannt) und Text. */
export interface ErkannteAussage {
  id: string | null;
  text: string;
}

/** Schluessel einer Aussage an einem Treffer: die ID, sonst der Text; null ohne Aussage. */
function aussageSchluessel(treffer: BaseSearchResult): string | null {
  const text = treffer.statement_text?.trim();
  if (!text) {
    return null;
  }
  return treffer.statement_id || `text:${text}`;
}

/**
 * Die erkannte Aussage (#642, R40): die Aussage, ueber die die meisten Treffer
 * gefunden wurden; bei Gleichstand die des Treffers mit dem hoechsten Score. Sie
 * steht einmal ueber den Treffern ("Gefunden zu: ..."), die Karten zeigen ihren
 * Antwort-auf-Kopf dann nur noch, wenn er davon abweicht. null, wenn kein Treffer
 * ueber eine Aussage kam (nur direkte Treffer) oder die gewaehlte weder den
 * obersten Treffer noch die Mehrheit traegt.
 */
export function erkannteAussage(antwort: SearchResponse): ErkannteAussage | null {
  const alle: BaseSearchResult[] = [
    ...(antwort.commentary_search_results ?? []),
    ...(antwort.generictext_search_results ?? []),
    ...(antwort.post_search_results ?? []),
  ];
  const je = new Map<string, { aussage: ErkannteAussage; anzahl: number; bester: number }>();
  for (const treffer of alle) {
    const schluessel = aussageSchluessel(treffer);
    if (!schluessel) {
      continue;
    }
    const eintrag = je.get(schluessel);
    if (eintrag) {
      eintrag.anzahl += 1;
      eintrag.bester = Math.max(eintrag.bester, treffer.score ?? 0);
    } else {
      je.set(schluessel, {
        aussage: { id: treffer.statement_id || null, text: treffer.statement_text!.trim() },
        anzahl: 1,
        bester: treffer.score ?? 0,
      });
    }
  }
  let gewaehlt: { aussage: ErkannteAussage; anzahl: number; bester: number } | null = null;
  let mitAussage = 0;
  let hoechster = -Infinity;
  for (const eintrag of je.values()) {
    mitAussage += eintrag.anzahl;
    hoechster = Math.max(hoechster, eintrag.bester);
  }
  for (const eintrag of je.values()) {
    if (
      !gewaehlt ||
      eintrag.anzahl > gewaehlt.anzahl ||
      (eintrag.anzahl === gewaehlt.anzahl && eintrag.bester > gewaehlt.bester)
    ) {
      gewaehlt = eintrag;
    }
  }
  // Nur, wenn die Zeile fuer die Treffer steht: Sie traegt den obersten Treffer
  // oder die Mehrheit. Verteilt auf viele Aussagen sagte "Gefunden zu" zu wenig.
  if (!gewaehlt || (gewaehlt.bester < hoechster && gewaehlt.anzahl * 2 <= mitAussage)) {
    return null;
  }
  return gewaehlt.aussage;
}

/** Ob ein Treffer ueber genau die erkannte Aussage gefunden wurde. */
export function zurErkanntenAussage(treffer: BaseSearchResult, erkannt: ErkannteAussage | null): boolean {
  if (!erkannt) {
    return false;
  }
  const schluessel = aussageSchluessel(treffer);
  return schluessel !== null && schluessel === (erkannt.id || `text:${erkannt.text}`);
}

/**
 * Worauf "Antworten" aus einer Suche antwortet, per ID: die erkannte Aussage, wo es
 * eine mit ID gibt, sonst die Aussage der Suche; null ohne beides (dann gilt der
 * Suchtext). Die erkannte zuerst: Legt die Suche eine eigene Aussage an (dieselbe
 * Behauptung in anderen Worten), liefert getById sie Nicht-Admins nicht aus (#436);
 * das Formular boete dann nur den Suchtext neben der gefundenen Aussage an, und die
 * Antwort landete leicht an einer Fast-Dublette statt an der Aussage, zu der die
 * Seite "Gefunden zu" sagt.
 */
export function aussageZumAntworten(antwort: SearchResponse | null | undefined): string | null {
  if (!antwort) {
    return null;
  }
  const erkannt = erkannteAussage(antwort)?.id;
  if (istAussageId(erkannt)) {
    return erkannt;
  }
  return istAussageId(antwort.statement_id) ? antwort.statement_id : null;
}
