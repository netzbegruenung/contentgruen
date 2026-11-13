const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Eine Kennung (Glossar) lesbar kurz, solange das Backend keinen Anzeigenamen liefert:
 * eine UUID als „Person 3f2a“ (die ersten vier Zeichen), lange andere Kennungen ebenso,
 * kurze bleiben, wie sie sind. Die volle Kennung gehört in den Tooltip.
 */
export function kurzeKennung(kennung: string | null | undefined): string {
  if (!kennung) {
    return '';
  }
  if (UUID.test(kennung) || kennung.length > 16) {
    return `Person ${kennung.replace(/[^a-zA-Z0-9]/g, '').slice(0, 4)}`;
  }
  return kennung;
}
