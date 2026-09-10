/**
 * Tracking-Parameter aus Adressen entfernen.
 *
 * Zwei Gruende, beide aus dem Instagram-Test: Instagram haengt an jede geteilte
 * Adresse ein ``stkn``, das sich pro Teilen-Vorgang aendert. Ungefiltert ist
 * dieselbe Reel bei jedem Einwurf eine andere URL -- eine spaetere
 * Dublettenerkennung liefe ins Leere. Und es ist ein Meta-Token, das niemand in
 * der Datenbank braucht.
 */

/**
 * Parameter, die vollstaendig entfernt werden.
 *
 * ``stkn`` ist im Test belegt (Instagram-Share). Die uebrigen sind die
 * gaengigen Verwandten derselben Familie und stehen hier, weil sie dieselbe
 * Eigenschaft haben: sie identifizieren den Weg, nicht den Inhalt.
 */
const TRACKING_PARAMETER = [
  'stkn', // Instagram, pro Share-Vorgang neu -- im Test belegt
  'igsh', // Instagram
  'igshid', // Instagram, aeltere Schreibweise
  'fbclid', // Facebook
  'gclid', // Google Ads
  'mc_cid', // Mailchimp
  'mc_eid', // Mailchimp
];

/** Praefixe, bei denen jeder Parameter mit diesem Anfang entfernt wird. */
const TRACKING_PRAEFIXE = ['utm_'];

/** Dieselbe Erkennung wie im Einwurf-Formular, damit beide dasselbe als URL ansehen. */
const URL_MUSTER_GLOBAL = /https?:\/\/[^\s]+/gi;

function istTrackingParameter(name: string): boolean {
  const klein = name.toLowerCase();
  return (
    TRACKING_PARAMETER.includes(klein) ||
    TRACKING_PRAEFIXE.some((praefix) => klein.startsWith(praefix))
  );
}

/**
 * Entfernt bekannte Tracking-Parameter aus einer einzelnen Adresse.
 *
 * Gibt die Eingabe unveraendert zurueck, wenn sie keine gueltige Adresse ist
 * oder nichts zu entfernen war -- diese Funktion darf nie werfen und nie etwas
 * kaputtmachen, das sie nicht versteht. Insbesondere bleibt der Suchteil
 * unangetastet, wenn kein Tracking-Parameter darin steht: ein Umschreiben ueber
 * URLSearchParams wuerde sonst die Kodierung veraendern, ohne dass sich inhaltlich
 * etwas aendert.
 */
export function trackingParameterEntfernen(url: string): string {
  if (!url) {
    return url;
  }

  let zerlegt: URL;
  try {
    zerlegt = new URL(url);
  } catch {
    return url;
  }

  const zuEntfernen: string[] = [];
  zerlegt.searchParams.forEach((_wert, name) => {
    if (istTrackingParameter(name)) {
      zuEntfernen.push(name);
    }
  });

  if (zuEntfernen.length === 0) {
    return url;
  }

  for (const name of zuEntfernen) {
    zerlegt.searchParams.delete(name);
  }

  // Bleibt nichts uebrig, soll auch das Fragezeichen weg -- "…/reel/ABC/?" waere
  // fuer eine Dublettenerkennung wieder eine eigene Zeichenkette.
  if (!zerlegt.searchParams.toString()) {
    zerlegt.search = '';
  }

  return zerlegt.toString();
}

/**
 * Wendet {@link trackingParameterEntfernen} auf jede Adresse an, die im Text steckt.
 *
 * Noetig, weil der geteilte Text die Adresse zugleich als Freitext enthaelt: das
 * Einwurf-Formular speichert bei "Text mit Link darin" beides, und dann duerfen
 * die Tracking-Parameter auch im Freitext nicht stehenbleiben.
 */
export function urlsInTextBereinigen(text: string): string {
  if (!text) {
    return text;
  }
  return text.replace(URL_MUSTER_GLOBAL, (treffer) => trackingParameterEntfernen(treffer));
}
