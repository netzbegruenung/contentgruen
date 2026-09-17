/**
 * Ein Titel ist ein Satz: Umbrueche samt umgebendem Leerraum werden zu einem
 * Leerzeichen. Enter bricht im Titelfeld nicht um; eingefuegter Text kann aber
 * Umbrueche mitbringen.
 */
export function einzeilig(wert: string | null | undefined): string {
  return (wert ?? '').replace(/\s*[\r\n]+\s*/g, ' ').trim();
}
