/**
 * Der Merker fuer „Seit deinem letzten Besuch“ im localStorage, je Konto unter einem
 * eigenen Schluessel (wie die Meilensteine in #668). Der Schluessel traegt einen Pruefwert
 * der Kennung, nicht die Kennung selbst. Beim Abmelden und beim Widerruf der
 * Art.-9-Einwilligung wird der Eintrag entfernt. Ohne Abhaengigkeiten, damit
 * AuthService und Einwilligung ihn loeschen koennen, ohne die Dienste der Startseite zu laden.
 */
export const LETZTER_BESUCH_PRAEFIX = 'gutgesagt-letzter-besuch-';

export interface BesuchMerker {
  /** ISO-Zeitpunkt des letzten Besuchs der Startseite. */
  zeit: string;
  /** IDs der Aussagen, die damals in „Hier fehlt eine Antwort“ standen. */
  aussagen: string[];
}

/** FNV-1a ueber die Kennung, 32 Bit hexadezimal: genuegt zum Trennen, ist kein Geheimnis. */
export function besuchSchluessel(kennung: string): string {
  let wert = 0x811c9dc5;
  for (let i = 0; i < kennung.length; i++) {
    wert ^= kennung.charCodeAt(i);
    wert = Math.imul(wert, 0x01000193) >>> 0;
  }
  return LETZTER_BESUCH_PRAEFIX + wert.toString(16).padStart(8, '0');
}

export function besuchMerkerLesen(kennung: string): BesuchMerker | null {
  try {
    const roh = localStorage.getItem(besuchSchluessel(kennung));
    if (!roh) {
      return null;
    }
    const merker = JSON.parse(roh) as Partial<BesuchMerker> | null;
    if (typeof merker?.zeit !== 'string' || Number.isNaN(Date.parse(merker.zeit)) || !Array.isArray(merker.aussagen)) {
      return null;
    }
    return { zeit: merker.zeit, aussagen: merker.aussagen.filter((id): id is string => typeof id === 'string') };
  } catch {
    return null;
  }
}

export function besuchMerkerSchreiben(kennung: string, merker: BesuchMerker): void {
  try {
    localStorage.setItem(besuchSchluessel(kennung), JSON.stringify(merker));
  } catch {
    // Ohne Speicher (privates Fenster) gibt es eben nichts „seit dem letzten Besuch“.
  }
}

/** Beim Abmelden und beim Widerruf: den Eintrag des Kontos entfernen. */
export function besuchMerkerEntfernen(kennung: string | null): void {
  if (!kennung) {
    return;
  }
  try {
    localStorage.removeItem(besuchSchluessel(kennung));
  } catch {
    // Ohne Speicher gibt es nichts zu entfernen.
  }
}
