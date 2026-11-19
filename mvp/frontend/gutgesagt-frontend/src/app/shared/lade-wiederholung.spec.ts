import { fakeAsync, tick } from '@angular/core/testing';
import { Subject } from 'rxjs';

import { LadeWiederholung, WIEDERHOLUNG_MS, lohntWiederholung } from './lade-wiederholung';

describe('LadeWiederholung', () => {
  it('plant nach einem lohnenden Fehler einen Versuch, den Erfolg wieder abraeumt', fakeAsync(() => {
    const ende$ = new Subject<void>();
    const wiederholung = new LadeWiederholung(ende$);
    const laden = jasmine.createSpy('laden');

    expect(wiederholung.fehlgeschlagen({ status: 503 }, laden)).toBeTrue();
    wiederholung.erfolg();
    tick(WIEDERHOLUNG_MS[WIEDERHOLUNG_MS.length - 1]);
    window.dispatchEvent(new Event('online'));

    expect(laden).not.toHaveBeenCalled();
    ende$.next();
  }));

  it('wiederholt nur ohne Status, bei 0, 408, 429 und 5xx', () => {
    expect([undefined, 0, 408, 429, 500, 503].map((status) => lohntWiederholung(status === undefined ? new Error('x') : { status }))).toEqual([
      true, true, true, true, true, true,
    ]);
    expect([400, 401, 403, 404].map((status) => lohntWiederholung({ status }))).toEqual([false, false, false, false]);
  });
});
