import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { FESTE_LEISTE_KLASSE, FormularLeisteComponent } from './formular-leiste.component';

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

  it('blendet sich aus, solange ein Textfeld den Fokus hat', () => {
    const fixture = TestBed.createComponent(GastComponent);
    fixture.detectChanges();
    const leiste: HTMLElement = fixture.nativeElement.querySelector('.leiste');
    const textfeld: HTMLInputElement = fixture.nativeElement.querySelector('.textfeld');
    const haken: HTMLInputElement = fixture.nativeElement.querySelector('.haken');

    textfeld.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    fixture.detectChanges();
    expect(leiste.classList).toContain('leiste--beim-tippen');

    textfeld.dispatchEvent(new FocusEvent('focusout', { bubbles: true, relatedTarget: haken }));
    fixture.detectChanges();
    expect(leiste.classList).not.toContain('leiste--beim-tippen');

    haken.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    fixture.detectChanges();
    expect(leiste.classList).not.toContain('leiste--beim-tippen');
    fixture.destroy();
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
});
