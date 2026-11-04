/**
 * Ob eine E-Mail-Adresse so aussieht, wie der Suchdienst sie annimmt (`EmailStr`,
 * email_validator). Dieselben Regeln, soweit sie ohne DNS gehen: Punkt-Atome im
 * lokalen Teil (hoechstens 64 Zeichen), Domain aus mindestens zwei Labels
 * (je 1 bis 63 Zeichen, kein Bindestrich am Rand), die Endung endet auf einen
 * Buchstaben, keine Domains fuer besondere Zwecke (RFC 6761). Umlaute sind erlaubt.
 * Die Gesamtlaenge begrenzt das Feld selbst.
 */

const ZEICHEN_LOKAL = "[\\p{L}\\p{N}!#$%&'*+/=?^_`{|}~-]+";
const LOKALER_TEIL = new RegExp(`^${ZEICHEN_LOKAL}(\\.${ZEICHEN_LOKAL})*$`, 'u');
const LABEL = /^[\p{L}\p{N}](?:[\p{L}\p{N}-]{0,61}[\p{L}\p{N}])?$/u;
const ENDET_AUF_BUCHSTABEN = /\p{L}$/u;

/** Wie `SPECIAL_USE_DOMAIN_NAMES` in email_validator. */
const BESONDERE_DOMAINS = ['arpa', 'invalid', 'local', 'localhost', 'onion', 'test'];

export function istEmailAdresse(adresse: string): boolean {
  const at = adresse.lastIndexOf('@');
  if (at <= 0) {
    return false;
  }
  const lokal = adresse.slice(0, at);
  const domain = adresse.slice(at + 1).toLowerCase();
  if (lokal.length > 64 || !LOKALER_TEIL.test(lokal)) {
    return false;
  }
  const labels = domain.split('.');
  if (labels.length < 2 || !labels.every((label) => LABEL.test(label))) {
    return false;
  }
  if (!ENDET_AUF_BUCHSTABEN.test(labels[labels.length - 1])) {
    return false;
  }
  return !BESONDERE_DOMAINS.some((besondere) => domain === besondere || domain.endsWith(`.${besondere}`));
}
