import { DestroyRef } from '@angular/core';
import { fakeAsync, tick } from '@angular/core/testing';
import { Subject, of, throwError } from 'rxjs';

import { Lauf, NACHLADEN_MS, nachladeStrom, selbstNachladen } from './selbst-nachladen';

/** Ein DestroyRef zum Ausloesen von Hand. */
function zerstoerbar(): { ref: DestroyRef; zerstoeren: () => void } {
  const rueckrufe: Array<() => void> = [];
  const ref = { onDestroy: (rueckruf: () => void) => rueckrufe.push(rueckruf) } as unknown as DestroyRef;
  return { ref, zerstoeren: () => rueckrufe.forEach((rueckruf) => rueckruf()) };
}

describe('selbst nachladen', () => {
  let sichtbarkeit: DocumentVisibilityState;

  function sichtbarWerden(wert: DocumentVisibilityState): void {
    sichtbarkeit = wert;
    document.dispatchEvent(new Event('visibilitychange'));
  }

  beforeEach(() => {
    sichtbarkeit = 'visible';
    spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);
  });

  it('laedt im Takt nach, solange der Reiter sichtbar ist, und nicht sofort', fakeAsync(() => {
    const holen = jasmine.createSpy('holen').and.returnValue(of(1));
    const weiter = jasmine.createSpy('weiter');
    const { ref, zerstoeren } = zerstoerbar();

    selbstNachladen(holen, ref, { next: weiter });
    expect(holen).not.toHaveBeenCalled();

    tick(NACHLADEN_MS);
    expect(weiter).toHaveBeenCalledOnceWith(1);

    sichtbarkeit = 'hidden';
    tick(NACHLADEN_MS * 3);
    expect(holen).toHaveBeenCalledTimes(1);
    zerstoeren();
  }));

  it('fragt im versteckten Reiter nie und laedt beim Sichtbarwerden sofort', fakeAsync(() => {
    const holen = jasmine.createSpy('holen').and.returnValue(of(1));
    const { ref, zerstoeren } = zerstoerbar();
    selbstNachladen(holen, ref, { next: () => undefined });

    sichtbarWerden('hidden');
    tick(NACHLADEN_MS * 4);
    expect(holen).not.toHaveBeenCalled();

    sichtbarWerden('visible');
    expect(holen).toHaveBeenCalledTimes(1);
    zerstoeren();
  }));

  it('startet den Takt beim Sichtbarwerden neu', fakeAsync(() => {
    const holen = jasmine.createSpy('holen').and.returnValue(of(1));
    const { ref, zerstoeren } = zerstoerbar();
    selbstNachladen(holen, ref, { next: () => undefined });

    tick(NACHLADEN_MS - 1000);
    sichtbarWerden('visible');
    expect(holen).toHaveBeenCalledTimes(1);

    // Der alte Takt waere jetzt faellig; der neue erst NACHLADEN_MS nach dem Sichtbarwerden.
    tick(1000);
    expect(holen).toHaveBeenCalledTimes(1);
    tick(NACHLADEN_MS - 1000);
    expect(holen).toHaveBeenCalledTimes(2);
    zerstoeren();
  }));

  it('startet keinen zweiten Lauf, solange einer laeuft, und holt den Anlass danach nach', fakeAsync(() => {
    const antwort = new Subject<number>();
    const holen = jasmine.createSpy('holen').and.returnValue(antwort);
    const abo = nachladeStrom(holen, { sofort: true }).subscribe();

    sichtbarWerden('visible');
    sichtbarWerden('visible');
    expect(holen).toHaveBeenCalledTimes(1);

    holen.and.returnValue(of(2));
    antwort.next(1);
    antwort.complete();
    expect(holen).toHaveBeenCalledTimes(2);
    abo.unsubscribe();
  }));

  it('wartet nach Fehlern laenger (30, 60, 120 s) und nach einem Erfolg wieder im Takt', fakeAsync(() => {
    const holen = jasmine.createSpy('holen').and.returnValue(throwError(() => new Error('weg')));
    const laeufe: Lauf<number>[] = [];
    const abo = nachladeStrom<number>(holen, { sofort: true }).subscribe((lauf) => laeufe.push(lauf));
    expect(holen).toHaveBeenCalledTimes(1);

    tick(NACHLADEN_MS * 2);
    expect(holen).toHaveBeenCalledTimes(2);
    tick(NACHLADEN_MS * 4 - 1);
    expect(holen).toHaveBeenCalledTimes(2);
    tick(1);
    expect(holen).toHaveBeenCalledTimes(3);

    holen.and.returnValue(of(7));
    tick(NACHLADEN_MS * 4);
    expect(holen).toHaveBeenCalledTimes(4);
    tick(NACHLADEN_MS);
    expect(holen).toHaveBeenCalledTimes(5);
    expect(laeufe[laeufe.length - 1]).toEqual({ daten: 7, fehler: null });
    abo.unsubscribe();
  }));

  it('hoert nach einem Fehler auf, den aufhoerenBei als endgueltig erkennt', fakeAsync(() => {
    const holen = jasmine.createSpy('holen').and.returnValue(throwError(() => ({ status: 401 })));
    const abo = nachladeStrom(holen, { sofort: true, aufhoerenBei: (f) => (f as { status: number }).status === 401 }).subscribe();

    tick(NACHLADEN_MS * 10);
    sichtbarWerden('visible');

    expect(holen).toHaveBeenCalledTimes(1);
    abo.unsubscribe();
  }));

  it('startet nach einem Stopp wieder, wenn von aussen angestossen wird', fakeAsync(() => {
    const anstoss$ = new Subject<void>();
    const holen = jasmine.createSpy('holen').and.returnValue(throwError(() => ({ status: 401 })));
    const abo = nachladeStrom(holen, { sofort: true, anstoss$, aufhoerenBei: () => true }).subscribe();
    tick(NACHLADEN_MS * 4);
    expect(holen).toHaveBeenCalledTimes(1);

    holen.and.returnValue(of(1));
    anstoss$.next();
    expect(holen).toHaveBeenCalledTimes(2);
    // Danach wieder im Takt
    tick(NACHLADEN_MS);
    expect(holen).toHaveBeenCalledTimes(3);
    abo.unsubscribe();
  }));

  it('hoert mit dem Ende der Seite auf', fakeAsync(() => {
    const holen = jasmine.createSpy('holen').and.returnValue(of(1));
    const { ref, zerstoeren } = zerstoerbar();
    selbstNachladen(holen, ref, { next: () => undefined });

    zerstoeren();
    tick(NACHLADEN_MS);
    sichtbarWerden('visible');

    expect(holen).not.toHaveBeenCalled();
  }));
});
