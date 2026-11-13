import { DestroyRef } from '@angular/core';
import { fakeAsync, tick } from '@angular/core/testing';

import { NACHLADEN_MS, selbstNachladen } from './selbst-nachladen';

/** Ein DestroyRef zum Ausloesen von Hand. */
function zerstoerbar(): { ref: DestroyRef; zerstoeren: () => void } {
  const rueckrufe: Array<() => void> = [];
  const ref = { onDestroy: (rueckruf: () => void) => rueckrufe.push(rueckruf) } as unknown as DestroyRef;
  return { ref, zerstoeren: () => rueckrufe.forEach((rueckruf) => rueckruf()) };
}

describe('selbstNachladen', () => {
  let sichtbarkeit: DocumentVisibilityState;

  beforeEach(() => {
    sichtbarkeit = 'visible';
    spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);
  });

  it('laedt im Takt nach, solange der Reiter sichtbar ist, und nicht sofort', fakeAsync(() => {
    const laden = jasmine.createSpy('laden');
    const { ref, zerstoeren } = zerstoerbar();

    selbstNachladen(laden, ref);
    expect(laden).not.toHaveBeenCalled();

    tick(NACHLADEN_MS);
    expect(laden).toHaveBeenCalledTimes(1);

    sichtbarkeit = 'hidden';
    tick(NACHLADEN_MS);
    expect(laden).toHaveBeenCalledTimes(1);
    zerstoeren();
  }));

  it('laedt sofort, wenn der Reiter wieder sichtbar wird, aber nicht beim Verstecken', fakeAsync(() => {
    const laden = jasmine.createSpy('laden');
    const { ref, zerstoeren } = zerstoerbar();
    selbstNachladen(laden, ref);

    sichtbarkeit = 'hidden';
    document.dispatchEvent(new Event('visibilitychange'));
    expect(laden).not.toHaveBeenCalled();

    sichtbarkeit = 'visible';
    document.dispatchEvent(new Event('visibilitychange'));
    expect(laden).toHaveBeenCalledTimes(1);
    zerstoeren();
  }));

  it('hoert mit dem Ende der Seite auf', fakeAsync(() => {
    const laden = jasmine.createSpy('laden');
    const { ref, zerstoeren } = zerstoerbar();
    selbstNachladen(laden, ref);

    zerstoeren();
    tick(NACHLADEN_MS);
    document.dispatchEvent(new Event('visibilitychange'));

    expect(laden).not.toHaveBeenCalled();
  }));
});
