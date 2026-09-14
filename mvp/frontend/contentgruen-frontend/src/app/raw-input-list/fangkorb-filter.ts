import { RawInput } from '../services/raw-input.service';
import { Plattform, PLATTFORMEN, plattformAusUrl } from '../shared/plattform';

/**
 * Schluessel im sessionStorage. Der Filter haelt innerhalb der Sitzung, nicht
 * darueber hinaus - wer den Fangkorb morgen oeffnet, sieht wieder alles.
 */
export const FILTER_SCHLUESSEL = 'contentgruen.fangkorb.filter';

/**
 * Die Plattformen, die ein gespeicherter Filter ohne Angabe "bekannte" kannte -
 * so hat ihn die Version vor Threads, X und Bluesky abgelegt.
 */
const FRUEHER_BEKANNTE: ReadonlyArray<string> = ['instagram', 'youtube', 'tiktok', 'web'];

/** So liegt der Filter im Storage: dazu, welche Plattformen es beim Speichern gab. */
interface GespeicherterFilter extends FangkorbFilter {
  bekannte: string[];
}

export interface FangkorbFilter {
  /** Eingeblendete Plattformen, Standard alle. Einwuerfe ohne Link blendet das nie aus. */
  plattformen: Plattform[];
  /** Nur, woran noch Arbeit ist: offen oder destilliert, aber nicht ausformuliert. */
  nurOffene: boolean;
  /** Nur selbst Eingeworfenes. */
  nurMeine: boolean;
}

export function standardFilter(): FangkorbFilter {
  return {
    plattformen: PLATTFORMEN.map((eintrag) => eintrag.wert),
    nurOffene: false,
    nurMeine: false,
  };
}

/**
 * Ob ein Einwurf unter diesem Filter sichtbar ist.
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
  if (filter.nurOffene && einwurf.status !== 'open' && einwurf.status !== 'in_progress') {
    return false;
  }
  if (filter.nurMeine && (!eigeneKennung || einwurf.submitted_by !== eigeneKennung)) {
    return false;
  }
  return true;
}

/**
 * Den Filter dieser Sitzung lesen.
 *
 * Fehlt er, ist er unlesbar oder ist der Storage gesperrt (privater Modus), gilt
 * der Standard. Plattformen, die es heute nicht mehr gibt, fallen heraus.
 * Plattformen, die der gespeicherte Filter noch nicht kannte, gelten als
 * eingeblendet - sonst blieben ihre Einwuerfe unsichtbar, ohne dass je jemand
 * sie abgewaehlt hat.
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
      nurOffene: gelesen?.nurOffene === true,
      nurMeine: gelesen?.nurMeine === true,
    };
  } catch {
    return standardFilter();
  }
}

export function filterSpeichern(filter: FangkorbFilter): void {
  try {
    const gespeichert: GespeicherterFilter = {
      ...filter,
      bekannte: PLATTFORMEN.map((eintrag) => eintrag.wert),
    };
    sessionStorage.setItem(FILTER_SCHLUESSEL, JSON.stringify(gespeichert));
  } catch {
    // Ohne Storage gilt der Filter eben nur, solange die Seite offen ist.
  }
}
