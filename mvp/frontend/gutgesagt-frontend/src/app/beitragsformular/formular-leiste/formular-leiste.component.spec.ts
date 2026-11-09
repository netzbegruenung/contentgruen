import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { FESTE_LEISTE_KLASSE, FormularLeisteComponent, ueberTastatur } from './formular-leiste.component';

@Component({
  standalone: true,
  imports: [FormularLeisteComponent],
  template: `<input class="textfeld" /><input type="checkbox" class="haken" />
    <app-formular-leiste><button type="submit">Speichern</button></app-formular-leiste>`,
})
class GastComponent {}

describe('FormularLeisteComponent', () => {
  it('traegt den Knopf und haelt am body Platz frei, solange sie da ist', () => {
    const fixture = TestBed.createComponent(GastComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.leiste button').textContent).toContain('Speichern');
    expect(document.body.classList).toContain(FESTE_LEISTE_KLASSE);

    fixture.destroy();
    expect(document.body.classList).not.toContain(FESTE_LEISTE_KLASSE);
  });

  it('bleibt stehen, solange ein Textfeld den Fokus hat (#616)', () => {
    const fixture = TestBed.createComponent(GastComponent);
    fixture.detectChanges();
    const textfeld: HTMLInputElement = fixture.nativeElement.querySelector('.textfeld');

    textfeld.focus();
    textfeld.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    fixture.detectChanges();

    const leiste: HTMLElement = fixture.nativeElement.querySelector('.leiste');
    expect(getComputedStyle(leiste).display).not.toBe('none');
    expect(leiste.querySelector('button')!.offsetHeight).toBeGreaterThan(0);
    fixture.destroy();
  });

  it('steht bei offener Tastatur um deren Hoehe hoeher, ohne Tastatur am Rand', () => {
    expect(ueberTastatur(844, { height: 844, offsetTop: 0 })).toBe(0);
    expect(ueberTastatur(844, { height: 500, offsetTop: 0 })).toBe(344);
    // Der Ausschnitt ist mit der Tastatur nach unten gescrollt
    expect(ueberTastatur(844, { height: 500, offsetTop: 100 })).toBe(244);
    // Eine Toolbar macht den Ausschnitt groesser als das Fenster: nie unter den Rand
    expect(ueberTastatur(800, { height: 844, offsetTop: 0 })).toBe(0);
  });

  it('zeigt einen Fehler knapp ueber dem Knopf', () => {
    const fixture = TestBed.createComponent(FormularLeisteComponent);
    fixture.componentRef.setInput('fehler', 'Speichern hat nicht geklappt.');
    fixture.detectChanges();

    const meldung: HTMLElement = fixture.nativeElement.querySelector('.leiste-fehler');
    expect(meldung.textContent).toContain('Speichern hat nicht geklappt.');
    expect(meldung.getAttribute('role')).toBe('alert');

    fixture.componentRef.setInput('fehler', null);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.leiste-fehler')).toBeNull();
    fixture.destroy();
  });

  it('bietet hinter der Meldung optional einen Textlink an', () => {
    const fixture = TestBed.createComponent(FormularLeisteComponent);
    fixture.componentRef.setInput('fehler', 'Es gibt schon einen sehr ähnlichen Kommentar.');
    fixture.componentRef.setInput('aktion', 'Ansehen');
    const geklickt = jasmine.createSpy('geklickt');
    fixture.componentInstance.aktionGeklickt.subscribe(geklickt);
    fixture.detectChanges();

    (fixture.nativeElement.querySelector('.leiste-aktion') as HTMLButtonElement).click();

    expect(geklickt).toHaveBeenCalledTimes(1);
    fixture.destroy();
  });

  it('zeigt einen Hinweis in Hinweisfarbe, ein Fehler geht vor', () => {
    const fixture = TestBed.createComponent(FormularLeisteComponent);
    fixture.componentRef.setInput('hinweis', 'Diesen Kommentar hast du schon gespeichert.');
    fixture.detectChanges();

    const hinweis: HTMLElement = fixture.nativeElement.querySelector('.leiste-hinweis');
    expect(hinweis.textContent).toContain('Diesen Kommentar hast du schon gespeichert.');
    // Ohne role: der Kasten im Formular sagt den Hinweis an
    expect(hinweis.getAttribute('role')).toBeNull();
    expect(fixture.nativeElement.querySelector('.leiste-fehler')).toBeNull();

    fixture.componentRef.setInput('fehler', 'Speichern hat nicht geklappt.');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.leiste-hinweis')).toBeNull();
    expect(fixture.nativeElement.querySelector('.leiste-fehler')).toBeTruthy();
    fixture.destroy();
  });

  it('rueckt bei einem visualViewport-Resize ueber die Tastatur und raeumt die Listener weg', () => {
    const lauscher = new Map<string, () => void>();
    const ausschnitt = {
      height: 844,
      offsetTop: 0,
      addEventListener: jasmine.createSpy('add').and.callFake((typ: string, f: () => void) => lauscher.set(typ, f)),
      removeEventListener: jasmine.createSpy('remove'),
    };
    spyOnProperty(window, 'visualViewport', 'get').and.returnValue(ausschnitt as unknown as VisualViewport);
    spyOnProperty(window, 'innerHeight', 'get').and.returnValue(844);
    const fixture = TestBed.createComponent(FormularLeisteComponent);
    fixture.detectChanges();
    const leiste: HTMLElement = fixture.nativeElement.querySelector('.leiste');
    expect(leiste.style.getPropertyValue('--leiste-ueber-tastatur')).toBe('0px');

    ausschnitt.height = 500;
    lauscher.get('resize')!();
    expect(leiste.style.getPropertyValue('--leiste-ueber-tastatur')).toBe('344px');

    fixture.destroy();
    expect(ausschnitt.removeEventListener).toHaveBeenCalledWith('resize', lauscher.get('resize'));
    expect(ausschnitt.removeEventListener).toHaveBeenCalledWith('scroll', lauscher.get('scroll'));
  });
});
