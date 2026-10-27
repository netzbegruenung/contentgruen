import { ActivatedRouteSnapshot, convertToParamMap } from '@angular/router';

import { routes } from './app.routes';
import { AuthGuard } from './auth/auth.guard';
import { gespeichertEltern } from './beitragsformular/beitrag-gespeichert/gespeichert-adresse';
import { EINWURF_PARAM, alteEinwurfAdresseUmleiten } from './destillieren/einwurf-adresse';

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
  it('fuehrt aus dem Destillier-Ablauf zurueck zum Einwurf, sonst nach /contribute', () => {
    const eltern = elternFunktion('workflow/add-commentary');

    expect(eltern(snapshotMit({ [EINWURF_PARAM]: 'e-42' }))).toEqual(['/destillieren', 'e-42']);
    expect(eltern(snapshotMit({}))).toBe('/contribute');
  });

  /**
   * Alte Adressen mit dem frueheren Parameternamen schreibt der Guard um, bevor
   * Formular, Ergebnisseite oder Pfeil ihn lesen; das Verhalten selbst testet
   * einwurf-adresse.spec.ts. Hier: Jede Route, deren Pfeil den Parameter liest,
   * traegt ihn, und zwar vor dem AuthGuard, damit der Login schon die neue Adresse
   * mitnimmt. Die Routen kommen aus der Tabelle, damit eine neue nicht durchrutscht.
   */
  it('leitet alte Einwurf-Adressen auf allen Routen um, die den Parameter lesen', () => {
    const formularEltern = elternFunktion('workflow/add-commentary');
    const lesend = routes.filter(
      (route) => route.data?.['parent'] === formularEltern || route.data?.['parent'] === gespeichertEltern,
    );

    expect(lesend.map((route) => route.path)).toEqual(
      jasmine.arrayContaining([
        'workflow/add-commentary',
        'workflow/add-generictext',
        'workflow/add-commentary/gespeichert/:id',
        'workflow/add-generictext/gespeichert/:id',
        'workflow/add-image',
      ]),
    );
    for (const eintrag of lesend) {
      expect(eintrag.canActivate?.[0]).withContext(eintrag.path ?? '').toBe(alteEinwurfAdresseUmleiten);
    }
  });

  /**
   * Der Pfeil auf /einwerfen: ohne Parameter auf die Beitragen-Seite, mit
   * ?von=fangkorb zurueck in die Liste. Den Parameter setzt der FAB im Fangkorb
   * (raw-input-list.component.ts, zumEinwerfen).
   */
  it('fuehrt von /einwerfen nach /contribute, aus dem Fangkorb aber zurueck', () => {
    const eltern = elternFunktion('einwerfen');

    expect(eltern(snapshotMit({}))).toBe('/contribute');
    expect(eltern(snapshotMit({ von: 'fangkorb' }))).toBe('/fangkorb');
    expect(eltern(snapshotMit({ von: 'suche' }))).toBe('/contribute');
  });

  it('nutzt dieselbe Funktion fuer alle drei Beitragsformulare', () => {
    for (const pfad of ['workflow/add-commentary', 'workflow/add-generictext', 'workflow/add-image']) {
      const eltern = elternFunktion(pfad);

      expect(eltern(snapshotMit({ [EINWURF_PARAM]: 'e-1' })))
        .withContext(pfad)
        .toEqual(['/destillieren', 'e-1']);
    }
  });

  it('fuehrt nach "Selbst beantworten" aus Formular und Ergebnisseite zurueck auf "Hier fehlt eine Antwort"', () => {
    const von = { von: 'hier-fehlt-eine-antwort' };

    expect(elternFunktion('workflow/add-commentary')(snapshotMit(von))).toBe('/hier-fehlt-eine-antwort');
    expect(gespeichertEltern(snapshotMit(von))).toBe('/hier-fehlt-eine-antwort');
    expect(gespeichertEltern(snapshotMit({}))).toBe('/contribute');
  });

  it('zeigt "Hier fehlt eine Antwort" nur Angemeldeten', () => {
    const eintrag = routes.find((route) => route.path === 'hier-fehlt-eine-antwort');
    expect(eintrag).withContext('Route fehlt').toBeTruthy();
    expect(eintrag!.canActivate).toContain(AuthGuard);
  });
});
