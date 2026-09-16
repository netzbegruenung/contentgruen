import { ActivatedRouteSnapshot, convertToParamMap } from '@angular/router';

import { routes } from './app.routes';
import { ROHINPUT_PARAM } from './destillieren/destillier-uebergabe.service';

/** Die Elternziel-Funktion einer Route holen, wie goBack sie aufruft. */
function elternFunktion(pfad: string): (snapshot: ActivatedRouteSnapshot) => string | unknown[] {
  const eintrag = routes.find((route) => route.path === pfad);
  expect(eintrag).withContext(`Route ${pfad} fehlt`).toBeTruthy();
  const parent = eintrag!.data?.['parent'];
  expect(typeof parent).withContext(`Route ${pfad} hat keine Elternziel-Funktion`).toBe('function');
  return parent as (snapshot: ActivatedRouteSnapshot) => string | unknown[];
}

function snapshotMit(params: Record<string, string>): ActivatedRouteSnapshot {
  return { queryParamMap: convertToParamMap(params) } as ActivatedRouteSnapshot;
}

describe('Routentabelle', () => {
  /**
   * Die Tabelle nennt den Parameter als Literal, damit sie den Destillier-Dienst
   * nicht ins Startbuendel zieht. Dieser Test haelt beide Stellen zusammen: Wer
   * ROHINPUT_PARAM umbenennt, faellt hier auf, statt erst im Browser.
   */
  it('kennt denselben Parameternamen wie der Destillier-Dienst', () => {
    const eltern = elternFunktion('workflow/add-commentary');

    expect(eltern(snapshotMit({ [ROHINPUT_PARAM]: 'e-42' }))).toEqual(['/destillieren', 'e-42']);
    expect(eltern(snapshotMit({}))).toBe('/contribute');
  });

  it('nutzt dieselbe Funktion fuer alle drei Beitragsformulare', () => {
    for (const pfad of ['workflow/add-commentary', 'workflow/add-generictext', 'workflow/add-image']) {
      const eltern = elternFunktion(pfad);

      expect(eltern(snapshotMit({ [ROHINPUT_PARAM]: 'e-1' })))
        .withContext(pfad)
        .toEqual(['/destillieren', 'e-1']);
    }
  });
});
