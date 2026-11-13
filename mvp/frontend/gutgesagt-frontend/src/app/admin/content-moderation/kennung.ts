/**
 * Eine Kennung (Glossar) lesbar kurz, solange das Backend keinen Anzeigenamen liefert:
 * „Person“ und acht Zeichen eines Hashs über die ganze Kennung (FNV-1a, 32 bit). Ein
 * Hash statt der ersten Zeichen, damit ähnliche Kennungen nicht gleich aussehen. Kurze
 * Kennungen (bis 12 Zeichen) bleiben, wie sie sind. Die volle Kennung gehört daneben,
 * aufklappbar oder im Tooltip.
 */
export function kurzeKennung(kennung: string | null | undefined): string {
  if (!kennung) {
    return '';
  }
  if (kennung.length <= 12) {
    return kennung;
  }
  let hash = 0x811c9dc5;
  for (let i = 0; i < kennung.length; i++) {
    hash ^= kennung.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return `Person ${hash.toString(16).padStart(8, '0')}`;
}
