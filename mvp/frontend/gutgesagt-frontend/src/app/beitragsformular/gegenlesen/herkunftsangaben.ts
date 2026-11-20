/**
 * Herkunft ohne Fundstelle (Gegenlesen-Messung an 535 KI-Inputs, 19.11.2026): Eine
 * Startseite ("https://www.umweltbundesamt.de") oder ein Pfad auf dem eigenen Rechner
 * ("/mnt/data/x.pdf") zeigt niemandem, wo es steht. Das Formular prüft das selbst und
 * schickt dem Gegenlesen nur Ja/Nein; die Herkunft selbst geht nicht mit.
 */

/** Links in einem Text: Die Langfassung eines Kommentars kann die Herkunft als Link tragen. */
const LINKS = /\bhttps?:\/\/\S+|\bwww\.\S+/gi;
/** Satzzeichen nach einem Link gehören nicht dazu ("… siehe www.example.org."). */
const SATZZEICHEN_AM_ENDE = /[.,;:!?)\]»«“”"']+$/;
/** Ein Pfad, der nur auf dem eigenen Rechner liegt. */
const LOKALER_PFAD = /^(?:file:|sandbox:|~\/|\/(?:mnt|home|tmp|users|var|data)\/|[a-z]:[\\/])/i;
/** Eine Adresse ohne Schema ("www.bmwk.de", "destatis.de/DE/…"). */
const ADRESSE = /^(?:www\.)?[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}(?:[/?#]|$)/i;
/** Pfade, die nur die Startseite sind ("/", "/de", "/index.html"). */
const STARTSEITE = /^\/*(?:(?:de|en|start|startseite|home)\/*)?(?:index\.\w+)?\/*$/i;

/** Eine eingetragene Herkunft, wie die Formulare sie halten. */
export interface Herkunftseintrag {
  reference_string?: string | null;
}

/**
 * Nennt die Angabe eine Fundstelle? Nein bei einem lokalen Pfad und bei einer Adresse,
 * die nur die Startseite ist. Eine Angabe ohne Adresse ("Umweltbundesamt, Bericht 2024")
 * zählt: Geprüft wird nur, ob sie sich finden lässt, nicht ob sie stimmt.
 */
export function hatFundstelle(angabe: string): boolean {
  let adresse = angabe.trim();
  if (LOKALER_PFAD.test(adresse)) {
    return false;
  }
  if (!/^https?:\/\//i.test(adresse)) {
    if (!ADRESSE.test(adresse)) {
      return true;
    }
    adresse = `http://${adresse}`;
  }
  let url: URL;
  try {
    url = new URL(adresse);
  } catch {
    return true;
  }
  return !!url.search || !STARTSEITE.test(url.pathname);
}

/**
 * Ist Herkunft eingetragen, aber keine Angabe nennt eine Fundstelle? Gezählt werden die
 * eingetragene Herkunft und Links im Text (Langfassung).
 */
export function herkunftOhneFundstelle(
  eintraege: readonly (Herkunftseintrag | null)[] | null | undefined,
  text?: string | null,
): boolean {
  const angaben = [
    ...(eintraege ?? []).map((e) => e?.reference_string?.trim() ?? ''),
    ...(text?.match(LINKS) ?? []).map((link) => link.replace(SATZZEICHEN_AM_ENDE, '')),
  ].filter(Boolean);
  return angaben.length > 0 && !angaben.some(hatFundstelle);
}
