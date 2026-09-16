import { RawInput } from '../services/raw-input.service';
import { zustandVonEinwurf } from '../beitragskarte/karten-daten';
import { Plattform, PLATTFORMEN, plattformAusUrl } from '../shared/plattform';

/**
 * Schluessel im sessionStorage. Filter und Tab halten innerhalb der Sitzung, nicht
 * darueber hinaus - wer den Fangkorb morgen oeffnet, sieht wieder alles und
 * beginnt beim Destillieren.
 */
export const FILTER_SCHLUESSEL = 'contentgruen.fangkorb.filter';

/**
 * Die Plattformen, die ein gespeicherter Filter ohne Angabe "bekannte" kannte -
 * so hat ihn die Version vor Threads, X und Bluesky abgelegt.
 */
const FRUEHER_BEKANNTE: ReadonlyArray<string> = ['instagram', 'youtube', 'tiktok', 'web'];

/** Die drei Arbeitsstufen als Tabs. Verworfenes liegt unter "Erledigt" hinter einem Chip. */
export type FangkorbTab = 'destillieren' | 'ausformulieren' | 'erledigt';

/** Reihenfolge, Beschriftung und die eine Zeile, die im leeren Tab steht. */
export const TABS: ReadonlyArray<{ wert: FangkorbTab; name: string; leer: string }> = [
  { wert: 'destillieren', name: 'Destillieren', leer: 'Nichts zu destillieren.' },
  { wert: 'ausformulieren', name: 'Ausformulieren', leer: 'Nichts auszuformulieren.' },
  { wert: 'erledigt', name: 'Erledigt', leer: 'Noch nichts erledigt.' },
];

/** So liegt der Filter im Storage: dazu, welche Plattformen es beim Speichern gab. */
interface GespeicherterFilter extends FangkorbFilter {
  bekannte: string[];
}

export interface FangkorbFilter {
  /** Eingeblendete Plattformen, Standard alle. Einwuerfe ohne Link blendet das nie aus. */
  plattformen: Plattform[];
  /** Nur selbst Eingeworfenes. */
  nurMeine: boolean;
  /** Der offene Tab. */
  tab: FangkorbTab;
  /** Verworfenes unter "Erledigt" mitzeigen; standardmaessig ausgeblendet. */
  verworfenSichtbar: boolean;
}

export function standardFilter(): FangkorbFilter {
  return {
    plattformen: PLATTFORMEN.map((eintrag) => eintrag.wert),
    nurMeine: false,
    tab: 'destillieren',
    verworfenSichtbar: false,
  };
}

/**
 * Ob ein Einwurf unter den Chips sichtbar ist - Plattform und "nur meine". Der
 * Tab entscheidet getrennt davon (``passtZumTab``), damit die Zaehler der anderen
 * Tabs dieselben Chips beruecksichtigen.
 *
 * Ohne bekannte eigene Kennung zeigt "nur meine" nichts an, statt stillschweigend
 * alles.
 */
export function passtZumFilter(
  einwurf: RawInput,
  filter: FangkorbFilter,
  eigeneKennung: string | null,
): boolean {
  const plattform = plattformAusUrl(einwurf.url);
  if (plattform && !filter.plattformen.includes(plattform)) {
    return false;
  }
  if (filter.nurMeine && (!eigeneKennung || einwurf.submitted_by !== eigeneKennung)) {
    return false;
  }
  return true;
}

/**
 * Ob ein Einwurf in diesem Tab liegt.
 *
 * Verworfenes gehoert zu "Erledigt", ist dort aber nur zu sehen, wenn der Chip
 * "verworfen" an ist - sonst taucht wieder auf, was jemand weggelegt hat.
 */
export function passtZumTab(
  einwurf: RawInput,
  tab: FangkorbTab,
  verworfenSichtbar: boolean,
): boolean {
  const zustand = zustandVonEinwurf(einwurf);
  if (zustand === 'verworfen') {
    return tab === 'erledigt' && verworfenSichtbar;
  }
  return zustand === tab;
}

/**
 * Filter und Tab dieser Sitzung lesen.
 *
 * Fehlt die Ablage, ist sie unlesbar oder ist der Storage gesperrt (privater
 * Modus), gilt der Standard. Plattformen, die es heute nicht mehr gibt, fallen
 * heraus. Plattformen, die der gespeicherte Filter noch nicht kannte, gelten als
 * eingeblendet - sonst blieben ihre Einwuerfe unsichtbar, ohne dass je jemand sie
 * abgewaehlt hat. Das frueher gespeicherte "nur offene" wird ignoriert; die Tabs
 * leisten dasselbe.
 */
export function filterLaden(): FangkorbFilter {
  try {
    const roh = sessionStorage.getItem(FILTER_SCHLUESSEL);
    if (!roh) {
      return standardFilter();
    }
    const gelesen = JSON.parse(roh) as Partial<GespeicherterFilter> | null;
    const kannte = Array.isArray(gelesen?.bekannte) ? gelesen.bekannte : FRUEHER_BEKANNTE;
    const gespeichert: string[] | null = Array.isArray(gelesen?.plattformen) ? gelesen.plattformen : null;
    return {
      plattformen: gespeichert
        ? PLATTFORMEN.map((eintrag) => eintrag.wert).filter(
            (wert) => gespeichert.includes(wert) || !kannte.includes(wert),
          )
        : standardFilter().plattformen,
      nurMeine: gelesen?.nurMeine === true,
      tab: TABS.some((eintrag) => eintrag.wert === gelesen?.tab)
        ? (gelesen!.tab as FangkorbTab)
        : standardFilter().tab,
      verworfenSichtbar: gelesen?.verworfenSichtbar === true,
    };
  } catch {
    return standardFilter();
  }
}

/**
 * Den Tab merken, den der Fangkorb beim naechsten Oeffnen zeigen soll.
 *
 * Gebraucht am Ende des Destillier-Ablaufs: Wer den letzten offenen Einwurf
 * verarbeitet hat, landet wieder im Fangkorb - und zwar dort, wo das Ergebnis
 * liegt, nicht in einem leeren "Destillieren".
 */
export function tabMerken(tab: FangkorbTab): void {
  filterSpeichern({ ...filterLaden(), tab });
}

export function filterSpeichern(filter: FangkorbFilter): void {
  try {
    const gespeichert: GespeicherterFilter = {
      ...filter,
      bekannte: PLATTFORMEN.map((eintrag) => eintrag.wert),
    };
    sessionStorage.setItem(FILTER_SCHLUESSEL, JSON.stringify(gespeichert));
  } catch {
    // Ohne Storage gelten Filter und Tab eben nur, solange die Seite offen ist.
  }
}
