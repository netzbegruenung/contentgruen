import { HttpErrorResponse } from '@angular/common/http';

/**
 * Die Meldung zu einem gescheiterten Speichern: bei 422 die erste Validierungsmeldung
 * des Backends, knapp (ohne Pydantics "Value error, "), sonst null - dann gilt die
 * allgemeine Meldung.
 */
export function validierungsMeldung(fehler: unknown): string | null {
  if (!(fehler instanceof HttpErrorResponse) || fehler.status !== 422) {
    return null;
  }
  const detail = (fehler.error as { detail?: unknown } | null)?.detail;
  const erste = Array.isArray(detail) ? detail[0] : detail;
  const text = typeof erste === 'string' ? erste : (erste as { msg?: unknown } | undefined)?.msg;
  return typeof text === 'string' && text.trim() ? text.replace(/^Value error,\s*/i, '').trim() : null;
}
