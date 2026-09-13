import { RawInput } from '../services/raw-input.service';
import { Plattform, PLATTFORMEN, plattformAusUrl } from '../shared/plattform';

/**
 * Schluessel im sessionStorage. Der Filter haelt innerhalb der Sitzung, nicht
 * darueber hinaus - wer den Fangkorb morgen oeffnet, sieht wieder alles.
 */
export const FILTER_SCHLUESSEL = 'contentgruen.fangkorb.filter';

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
 * der Standard. Unbekannte Plattformen aus einer aelteren Version fallen heraus.
 */
export function filterLaden(): FangkorbFilter {
  try {
    const roh = sessionStorage.getItem(FILTER_SCHLUESSEL);
    if (!roh) {
      return standardFilter();
    }
    const gelesen = JSON.parse(roh) as Partial<FangkorbFilter> | null;
    const bekannte: string[] = PLATTFORMEN.map((eintrag) => eintrag.wert);
    return {
      plattformen: Array.isArray(gelesen?.plattformen)
        ? gelesen.plattformen.filter((wert): wert is Plattform => bekannte.includes(wert))
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
    sessionStorage.setItem(FILTER_SCHLUESSEL, JSON.stringify(filter));
  } catch {
    // Ohne Storage gilt der Filter eben nur, solange die Seite offen ist.
  }
}
