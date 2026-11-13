import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import { FarbschemaKnopfComponent } from './farbschema-knopf.component';
import { FarbschemaService } from '../../../services/farbschema.service';

describe('FarbschemaKnopfComponent', () => {
  let fixture: ComponentFixture<FarbschemaKnopfComponent>;
  let dunkel: ReturnType<typeof signal<boolean>>;
  let umschalten: jasmine.Spy;

  // Ersatz fuer den Dienst: Ein echtes Umschalten setzte data-theme am Testdokument
  beforeEach(() => {
    dunkel = signal(false);
    umschalten = jasmine.createSpy('umschalten').and.callFake(() => dunkel.update((d) => !d));
    TestBed.configureTestingModule({
      imports: [FarbschemaKnopfComponent],
      providers: [{ provide: FarbschemaService, useValue: { dunkel: () => dunkel(), umschalten } }],
    });
    fixture = TestBed.createComponent(FarbschemaKnopfComponent);
    fixture.detectChanges();
  });

  function knopf(): HTMLButtonElement {
    return fixture.nativeElement.querySelector('button');
  }

  it('ist ein Schalter mit festem Namen und zeigt, wohin er schaltet', () => {
    expect(knopf().getAttribute('aria-label')).toBe('Dunkles Farbschema');
    expect(knopf().getAttribute('aria-pressed')).toBe('false');
    expect(knopf().querySelector('mat-icon')!.textContent!.trim()).toBe('dark_mode');
  });

  it('schaltet beim Klick um und meldet den neuen Zustand', () => {
    knopf().click();
    fixture.detectChanges();

    expect(umschalten).toHaveBeenCalledTimes(1);
    expect(knopf().getAttribute('aria-pressed')).toBe('true');
    expect(knopf().querySelector('mat-icon')!.textContent!.trim()).toBe('light_mode');
  });

  it('hat einen sichtbaren Fokusrahmen', () => {
    // Regel in den Komponenten-Styles: outline bei :focus-visible
    const regeln = Array.from(document.styleSheets)
      .flatMap((blatt) => { try { return Array.from(blatt.cssRules); } catch { return []; } })
      .map((regel) => regel.cssText)
      .filter((text) => text.includes('farbschema-knopf') && text.includes(':focus-visible'));
    expect(regeln.some((text) => /outline:\s*2px solid/.test(text))).toBeTrue();
  });
});
