/**
 * Was die Güte an der Zeichnung des Siegels ändert (#416, Entwurf C „Hand bricht aus der
 * Blase“): Winkel der Hand, Farbe und Text für Screenreader. Die Zeichnung selbst, eine
 * eckige Sprechblase unten links, aus der die Hand oben rechts ragt, steht in
 * `siegel.component.html`, die Hand in `shared/marke/hand.ts`. Das Logo
 * `public/marke/logo.svg` und die Favicons sind dieselbe Zeichnung bei Güte 10; wer die
 * Blase oder die Hand ändert, ändert sie mit (der Test in `siegel.component.spec.ts`
 * passt darauf auf).
 */
/** Höchste Güte. Güte 1–10; ohne Daten (`null`) ist ein Beitrag „neu“. */
export const HOECHSTE_GUETE = 10;

/** Ganzzahlige Güte zwischen 1 und 10, oder `null` für „neu“; 0 und darunter gelten als neu. */
export function normierteGuete(guete: number | null | undefined): number | null {
  if (guete === null || guete === undefined || Number.isNaN(guete)) return null;
  const gerundet = Math.round(guete);
  return gerundet < 1 ? null : Math.min(HOECHSTE_GUETE, gerundet);
}

/**
 * Drehung der Hand im Uhrzeigersinn in Grad: 90 = waagrecht (neu), 0 = senkrecht nach
 * oben (Güte 10), 9 Grad je Punkt Güte. Größer als 90 wird es nie, der Daumen zeigt
 * also nie nach unten.
 */
export function siegelWinkel(guete: number | null): number {
  const g = normierteGuete(guete) ?? 0;
  return 90 - g * (90 / HOECHSTE_GUETE);
}

const zwischen = (a: number, b: number, t: number): number => a + (b - a) * t;
const runde = (x: number): number => Math.round(x * 10) / 10;

type Hsl = [farbton: number, saettigung: number, helligkeit: number];
const GRAU: Hsl = [80, 6, 58];
const GELB: Hsl = [46, 90, 46];
const GRUEN: Hsl = [146, 100, 27];
/** Anteil der Güte-Skala, an dem das Siegel ganz gelb ist. */
const GELB_BEI = 0.4;

const mische = (von: Hsl, nach: Hsl, t: number): Hsl =>
  [0, 1, 2].map((i) => zwischen(von[i], nach[i], t)) as Hsl;

/**
 * Farbe des Siegels: Grau über Gelb nach Grün, nie Rot (der Farbton bleibt zwischen
 * Gelb und Grün). Güte 10 ist das Grün des Logos.
 */
export function siegelFarbe(guete: number | null): string {
  const t = (normierteGuete(guete) ?? 0) / HOECHSTE_GUETE;
  const [h, s, l] = t <= GELB_BEI ? mische(GRAU, GELB, t / GELB_BEI) : mische(GELB, GRUEN, (t - GELB_BEI) / (1 - GELB_BEI));
  return `hsl(${runde(h)} ${runde(s)}% ${runde(l)}%)`;
}

/** Was Screenreader über das Siegel sagen. */
export function siegelText(guete: number | null): string {
  const g = normierteGuete(guete);
  return g === null ? 'Siegel: neu, noch keine Güte' : `Siegel: Güte ${g} von ${HOECHSTE_GUETE}`;
}
