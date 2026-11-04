import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Cc0HinweisComponent } from './cc0-hinweis.component';
import { erwarteCc0Hinweis } from './cc0-hinweis.testing';
import { CONSENT_HINWEIS_SATZ } from '../consent-hinweis';

@Component({
  standalone: true,
  imports: [Cc0HinweisComponent],
  template: `
    <div class="formular"><p appCc0Hinweis></p><button>Speichern</button></div>
    <div class="satz"><p appCc0Hinweis [hinweis]="satz"></p></div>
  `,
})
class GastComponent {
  readonly satz = CONSENT_HINWEIS_SATZ;
}

describe('Cc0HinweisComponent', () => {
  let wurzel: HTMLElement;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [GastComponent], providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(GastComponent);
    fixture.detectChanges();
    wurzel = fixture.nativeElement;
  });

  it('steht als Absatz an seiner Stelle und verlinkt CC0 und die Nutzungsbedingungen', () => {
    const absatz = erwarteCc0Hinweis(wurzel.querySelector('.formular')!);

    expect(absatz.nextElementSibling!.tagName).toBe('BUTTON');
  });

  it('zeigt beim Satz den Wortlaut fuers Speichern beim Tippen', () => {
    erwarteCc0Hinweis(wurzel.querySelector('.satz')!, CONSENT_HINWEIS_SATZ);
  });
});
