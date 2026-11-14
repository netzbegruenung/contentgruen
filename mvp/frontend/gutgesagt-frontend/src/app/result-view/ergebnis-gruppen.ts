import { SearchResponse } from '../services/dtos/searchDtos';
import { BaseSearchResult } from '../services/dtos/commonDtos';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { typBeschreibung } from '../shared/content-type-registry';

/**
 * Die Ergebnisseite als eine Liste (K2+): Treffer nach Aussage gruppiert, in jeder
 * Gruppe die Typen in fester Reihenfolge, je Typ zuerst nur wenige Karten. Am Handy
 * und am Desktop dieselbe Darstellung; oben waehlen Chips den Typ.
 */

/** Die Typen der Treffer, in der Reihenfolge der Seite: Kommentare zuerst. */
export const TREFFER_TYPEN = ['commentary', 'generictext', 'image', 'post'] as const;
export type TrefferTyp = (typeof TREFFER_TYPEN)[number];
export type TypFilter = 'alle' | TrefferTyp;

/** Wie viele Karten je Typ und Gruppe zuerst dastehen; der Rest auf "Alle N … zeigen". */
export const KARTEN_JE_TYP = 3;

/** Woher die Treffer eines Typs in der Suchantwort kommen. */
const FELD: Record<TrefferTyp, keyof SearchResponse> = {
  commentary: 'commentary_search_results',
  generictext: 'generictext_search_results',
  image: 'image_search_results',
  post: 'post_search_results',
};

/** Namen je Typ: Chip und "Alle N … zeigen" in der Mehrzahl, Ueberschrift je nach Zahl. */
export const TYP_NAMEN: Record<TrefferTyp, { einzahl: string; mehrzahl: string }> = {
  commentary: { einzahl: 'Kommentar', mehrzahl: 'Kommentare' },
  generictext: { einzahl: 'Hintergrundinfo', mehrzahl: 'Hintergrundinfos' },
  image: { einzahl: 'Bild', mehrzahl: 'Bilder' },
  post: { einzahl: 'Post', mehrzahl: 'Posts' },
};

/** Die Treffer eines Typs aus der Antwort; fehlende Felder (aeltere Antworten) sind leer. */
export function trefferDesTyps(antwort: SearchResponse, typ: TrefferTyp): BaseSearchResult[] {
  return (antwort[FELD[typ]] as BaseSearchResult[] | undefined) ?? [];
}

/** Alle Treffer der Antwort, gleich welchen Typs. */
export function alleTreffer(antwort: SearchResponse): BaseSearchResult[] {
  return TREFFER_TYPEN.flatMap((typ) => trefferDesTyps(antwort, typ));
}

/** Wie viele Treffer je Typ; gezaehlt wird die Liste, nicht das Zaehlerfeld. */
export function anzahlJeTyp(antwort: SearchResponse | null): Record<TrefferTyp, number> {
  const anzahl = { commentary: 0, generictext: 0, image: 0, post: 0 };
  if (antwort) {
    for (const typ of TREFFER_TYPEN) {
      anzahl[typ] = trefferDesTyps(antwort, typ).length;
    }
  }
  return anzahl;
}

/** Schluessel einer Aussage an einem Treffer: die ID, sonst der Text; null ohne Aussage. */
export function aussageSchluessel(treffer: BaseSearchResult): string | null {
  const text = treffer.statement_text?.trim();
  if (!text) {
    return null;
  }
  return treffer.statement_id || `text:${text}`;
}

/**
 * Wozu eine Gruppe gehoert: zur erkannten Aussage, zu einer aehnlichen (es gibt eine
 * erkannte, aber eine andere), zu einer Aussage ohne erkannte (die Treffer verteilen
 * sich), oder zu keiner Aussage (direkte Treffer zum Suchtext).
 */
export type GruppenArt = 'erkannt' | 'aehnlich' | 'aussage' | 'ohne';

export interface ErgebnisGruppe {
  schluessel: string;
  art: GruppenArt;
  /** Text der Aussage; null bei direkten Treffern. */
  text: string | null;
  /** Bester Score in der Gruppe, fuer die Reihenfolge. */
  bester: number;
  /** Karten je Typ, in der Reihenfolge der Suchantwort. */
  je: Record<TrefferTyp, KartenDaten[]>;
}

const OHNE_AUSSAGE = 'ohne';

/** Macht aus einem Treffer die Karte; die Ergebnisseite reicht einen Zwischenspeicher je Suchantwort. */
export type KarteZu = (treffer: BaseSearchResult) => KartenDaten;

/**
 * Die Treffer nach Aussage gruppiert: die erkannte Aussage zuerst, dann die anderen
 * nach ihrem besten Treffer, die direkten Treffer zuletzt.
 */
export function gruppieren(
  antwort: SearchResponse,
  erkannterSchluessel: string | null,
  karteZu: KarteZu = ausSuchergebnis,
): ErgebnisGruppe[] {
  const gruppen = new Map<string, ErgebnisGruppe>();
  for (const typ of TREFFER_TYPEN) {
    for (const treffer of trefferDesTyps(antwort, typ)) {
      const schluessel = aussageSchluessel(treffer) ?? OHNE_AUSSAGE;
      let gruppe = gruppen.get(schluessel);
      if (!gruppe) {
        gruppe = {
          schluessel,
          art: gruppenArt(schluessel, erkannterSchluessel),
          text: schluessel === OHNE_AUSSAGE ? null : treffer.statement_text!.trim(),
          bester: -Infinity,
          je: { commentary: [], generictext: [], image: [], post: [] },
        };
        gruppen.set(schluessel, gruppe);
      }
      gruppe.bester = Math.max(gruppe.bester, treffer.score ?? 0);
      // Die Aussage bleibt an der Karte (Admins sehen dort die Werte); die Zeile
      // "Antwort auf:" blendet die Seite aus, weil die Gruppe sie nennt.
      gruppe.je[typ].push(karteZu(treffer));
    }
  }
  const rang: Record<GruppenArt, number> = { erkannt: 0, aehnlich: 1, aussage: 1, ohne: 2 };
  return [...gruppen.values()].sort((a, b) => rang[a.art] - rang[b.art] || b.bester - a.bester);
}

function gruppenArt(schluessel: string, erkannt: string | null): GruppenArt {
  if (schluessel === OHNE_AUSSAGE) {
    return 'ohne';
  }
  if (!erkannt) {
    return 'aussage';
  }
  return schluessel === erkannt ? 'erkannt' : 'aehnlich';
}

/** Ein Typ in einer Gruppe, wie er dasteht. */
export interface AnsichtBlock {
  typ: TrefferTyp;
  /** Eindeutig auf der Seite; Anker fuer den Fokus nach "Alle N … zeigen". */
  id: string;
  ueberschrift: string;
  /** Erklaerung des Typs, nur beim ersten Vorkommen auf der Seite (VISION: je eine Zeile). */
  erklaerung: string | null;
  karten: KartenDaten[];
  alle: number;
  /** Text des Knopfs "Alle N … zeigen"; null, wenn schon alle dastehen. */
  mehrText: string | null;
}

export interface AnsichtGruppe {
  schluessel: string;
  art: GruppenArt;
  /**
   * Weniger passend: Es gibt eine erkannte Aussage, und diese Gruppe ist eine andere
   * (aehnliche Aussage oder direkte Treffer). Steht eingeklappt unter "Weitere,
   * weniger passende Treffer" und zaehlt nicht in den Chips.
   */
  weniger: boolean;
  text: string | null;
  id: string;
  anzahl: number;
  bloecke: AnsichtBlock[];
}

/**
 * Was die Seite zeigt: nur Typen, die zum Filter passen, je Typ hoechstens
 * KARTEN_JE_TYP Karten, ausser die Gruppe ist fuer den Typ aufgeklappt.
 * Gruppen ohne passende Karten fallen weg.
 */
export function ansichtBauen(
  gruppen: readonly ErgebnisGruppe[],
  filter: TypFilter,
  aufgeklappt: ReadonlySet<string>,
): AnsichtGruppe[] {
  const erklaert = new Set<TrefferTyp>();
  const ansicht: AnsichtGruppe[] = [];
  gruppen.forEach((gruppe, nr) => {
    const bloecke: AnsichtBlock[] = [];
    for (const typ of TREFFER_TYPEN) {
      const karten = gruppe.je[typ];
      if (!karten.length || (filter !== 'alle' && filter !== typ)) {
        continue;
      }
      const id = blockId(nr, typ);
      const offen = aufgeklappt.has(aufklappSchluessel(gruppe.schluessel, typ));
      const namen = TYP_NAMEN[typ];
      bloecke.push({
        typ,
        id,
        ueberschrift: karten.length === 1 ? namen.einzahl : namen.mehrzahl,
        erklaerung: erklaert.has(typ) ? null : typBeschreibung(typ) || null,
        karten: offen ? karten : karten.slice(0, KARTEN_JE_TYP),
        alle: karten.length,
        mehrText: !offen && karten.length > KARTEN_JE_TYP ? `Alle ${karten.length} ${namen.mehrzahl} zeigen` : null,
      });
      erklaert.add(typ);
    }
    if (bloecke.length) {
      ansicht.push({
        schluessel: gruppe.schluessel,
        art: gruppe.art,
        weniger: istWeniger(gruppe, gruppen),
        text: gruppe.text,
        id: `ergebnis-gruppe-${nr}`,
        anzahl: bloecke.reduce((summe, block) => summe + block.alle, 0),
        bloecke,
      });
    }
  });
  return ansicht;
}

/**
 * Ob eine Gruppe "weniger passend" ist: Es gibt eine erkannte Aussage, und die Gruppe
 * ist eine andere. Eine Mindest-Aehnlichkeit trennt das nicht: Die Suche liefert nur
 * gewichtete Werte, und auch die rohe Aehnlichkeit liegt fuer Aussagen gleicher
 * Satzform ("Die Gruenen wollen uns ... verbieten") im Band, das der Dienst fuer
 * passende Aussagen misst (aussage_vorschlag_schwelle). Siehe PR #671.
 */
export function istWeniger(gruppe: ErgebnisGruppe, gruppen: readonly ErgebnisGruppe[]): boolean {
  return gruppe.art !== 'erkannt' && gruppen.some((g) => g.art === 'erkannt');
}

/** Treffer je Typ, die ohne Aufklappen dastehen: ohne die weniger passenden Gruppen. */
export function anzahlSichtbar(gruppen: readonly ErgebnisGruppe[]): Record<TrefferTyp, number> {
  const anzahl = { commentary: 0, generictext: 0, image: 0, post: 0 };
  for (const gruppe of gruppen) {
    if (istWeniger(gruppe, gruppen)) {
      continue;
    }
    for (const typ of TREFFER_TYPEN) {
      anzahl[typ] += gruppe.je[typ].length;
    }
  }
  return anzahl;
}

export function blockId(gruppenNr: number, typ: TrefferTyp): string {
  return `ergebnis-gruppe-${gruppenNr}-${typ}`;
}

export function aufklappSchluessel(gruppe: string, typ: TrefferTyp): string {
  return `${gruppe}|${typ}`;
}

/** Die Typwahl gilt fuer die Sitzung; ein gesperrter Storage wirft nicht. */
export const TYPFILTER_SCHLUESSEL = 'gutgesagt.ergebnis.typ';

export function typFilterLesen(): TypFilter {
  try {
    const wert = sessionStorage.getItem(TYPFILTER_SCHLUESSEL);
    return wert && (TREFFER_TYPEN as readonly string[]).includes(wert) ? (wert as TrefferTyp) : 'alle';
  } catch {
    return 'alle';
  }
}

export function typFilterMerken(filter: TypFilter): void {
  try {
    if (filter === 'alle') {
      sessionStorage.removeItem(TYPFILTER_SCHLUESSEL);
    } else {
      sessionStorage.setItem(TYPFILTER_SCHLUESSEL, filter);
    }
  } catch {
    // Ohne Storage gilt die Wahl nur bis zur naechsten Suche.
  }
}
