import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

/**
 * Query-Parameter, mit dem die Destillier-Ansicht ein Beitragsformular oeffnet
 * (?einwurf=<id>). Der Pfeil des Formulars fuehrt damit zurueck zum Einwurf, beim
 * Bild-Formular ist das sein einziger Zweck. Auch die Ergebnisseite nach dem
 * Speichern traegt ihn, damit ihr Pfeil in den Fangkorb fuehrt.
 *
 * Eigene Datei ohne weitere Abhaengigkeiten: Die Routentabelle wird beim Start
 * geladen und soll den Destillier-Dienst nicht ins erste Buendel ziehen.
 */
export const EINWURF_PARAM = 'einwurf';

/** Der fruehere Name. Geteilte Adressen und die installierte App tragen ihn noch. */
const ALTER_EINWURF_PARAM = 'rohinput'; // retired-ok: alte Adressen muessen weiter aufgehen

/**
 * Leitet eine Adresse mit dem frueheren Parameternamen auf den neuen um, bevor das
 * Formular sie liest. Uebrige Parameter bleiben; steht der neue Name schon in der
 * Adresse, gilt er.
 *
 * Als erster Guard der Route: Wer danach zum Login muss, kommt mit der neuen Adresse
 * zurueck. Ein schlichter UrlTree genuegt fuer die History: Beim Start der App und
 * beim Neuladen ersetzt der Router die alte Adresse, und innerhalb der App kommt sie
 * gar nicht erst hinein.
 */
export const alteEinwurfAdresseUmleiten: CanActivateFn = (route, state) => {
  const alteId = route.queryParamMap.get(ALTER_EINWURF_PARAM);
  if (alteId === null) {
    return true;
  }
  const ziel = inject(Router).parseUrl(state.url);
  const { [ALTER_EINWURF_PARAM]: _alt, ...uebrige } = ziel.queryParams;
  ziel.queryParams = { ...uebrige, [EINWURF_PARAM]: uebrige[EINWURF_PARAM] ?? alteId };
  return ziel;
};
