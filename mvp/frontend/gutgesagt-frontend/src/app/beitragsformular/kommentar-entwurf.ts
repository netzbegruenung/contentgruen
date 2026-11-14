import { kontoPruefwert } from '../einwilligung/entwurf-vor-einwilligung';

/**
 * Der Entwurf des Kommentarformulars über einen App-Wechsel (Entscheidung E1, 14.11.2026):
 * Wer am Handy zu Instagram wechselt, kommt oft in einen neu geladenen Tab zurück, und der
 * Text war weg (Persona-Runde 2, P30).
 *
 * Nur dieses Formular, nur im sessionStorage, also nur in diesem Tab. Geschrieben wird beim
 * Ausblenden der Seite. Ein Eintrag mit Zeitpunkt, dem Prüfwert der Kennung (FNV-1a, wie die
 * Entwürfe vor der Einwilligung, nicht die Kennung selbst) und der Aussage, auf die er
 * antwortet. Nach ENTWURF_HOECHSTENS_MS gilt er nicht mehr. Gelöscht wird er beim Absenden,
 * beim Leeren des Formulars, beim Abmelden und beim Widerruf der Art.-9-Einwilligung; einen
 * Eintrag eines anderen Kontos verwendet das Formular nicht.
 */
export const KOMMENTAR_ENTWURF_SCHLUESSEL = 'gutgesagt-kommentar-entwurf';

/** Eine Stunde; danach ist es kein App-Wechsel mehr, sondern ein neuer Anfang. */
export const KOMMENTAR_ENTWURF_HOECHSTENS_MS = 60 * 60 * 1000;

/** Was vom Formular gesichert wird: die Texte und die Wahl von Zweck und Stil. */
export interface KommentarEntwurfWerte {
  title: string;
  text: string;
  kurz: string;
  lang: string;
  zweck: string | null;
  stil: string | null;
}

interface Eintrag {
  zeit: number;
  konto: number;
  aussage: string;
  werte: KommentarEntwurfWerte;
}

function istEintrag(wert: unknown): wert is Eintrag {
  const e = wert as Eintrag | null;
  return !!e && typeof e.zeit === 'number' && typeof e.konto === 'number' && typeof e.aussage === 'string' && !!e.werte;
}

/** Sichern; ohne Anmeldung oder ohne Text und Titel nichts (dann auch kein alter Eintrag). */
export function kommentarEntwurfSichern(
  werte: KommentarEntwurfWerte,
  aussage: string,
  kennung: string | null,
  jetzt = Date.now(),
): void {
  const konto = kontoPruefwert(kennung);
  if (konto === null || !(werte.text?.trim() || werte.title?.trim())) {
    kommentarEntwurfLoeschen();
    return;
  }
  try {
    sessionStorage.setItem(KOMMENTAR_ENTWURF_SCHLUESSEL, JSON.stringify({ zeit: jetzt, konto, aussage, werte }));
  } catch {
    // Ohne Speicher (privates Fenster, gesperrt) gibt es keinen Entwurf; mehr passiert nicht.
  }
}

/**
 * Der Entwurf für dieses Konto und diese Aussage, oder null. Zu alt, aus der Zukunft oder von
 * einem anderen Konto: Der Eintrag wird gelöscht. Eine andere Aussage lässt ihn liegen.
 */
export function kommentarEntwurfHolen(aussage: string, kennung: string | null, jetzt = Date.now()): KommentarEntwurfWerte | null {
  let eintrag: unknown;
  try {
    const roh = sessionStorage.getItem(KOMMENTAR_ENTWURF_SCHLUESSEL);
    eintrag = roh ? JSON.parse(roh) : null;
  } catch {
    return null;
  }
  if (!eintrag) return null;
  const konto = kontoPruefwert(kennung);
  if (
    !istEintrag(eintrag) ||
    konto === null ||
    eintrag.konto !== konto ||
    jetzt - eintrag.zeit > KOMMENTAR_ENTWURF_HOECHSTENS_MS ||
    jetzt < eintrag.zeit
  ) {
    kommentarEntwurfLoeschen();
    return null;
  }
  return eintrag.aussage === aussage ? eintrag.werte : null;
}

/** Beim Absenden, Leeren, Abmelden und Widerruf. */
export function kommentarEntwurfLoeschen(): void {
  try {
    sessionStorage.removeItem(KOMMENTAR_ENTWURF_SCHLUESSEL);
  } catch {
    // Ohne Speicher gibt es nichts zu löschen.
  }
}
