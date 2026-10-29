import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { abschnitt, normalisiert } from '../testing/rechtstext';
import { ORGANISATION } from '../shared/organisation';
import { ImpressumComponent } from './impressum.component';

/** Das Impressum duzt wie die anderen Rechtstexte und die App (#222, Entscheidung 29.10.2026). */
describe('ImpressumComponent', () => {
  let seite: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ImpressumComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    const fixture = TestBed.createComponent(ImpressumComponent);
    fixture.detectChanges();
    seite = fixture.nativeElement as HTMLElement;
  });

  it('duzt die Lesenden und spricht von Mitwirkenden', () => {
    const text = normalisiert(seite.textContent);

    expect(text).not.toMatch(/\b(Sie|Ihr|Ihre|Ihnen)\b/);
    expect(text).not.toContain('Nutzerinnen und Nutzer');
    expect(abschnitt(seite, 'Kontaktstelle nach Art. 11 und 12 DSA')).toContain('kannst du uns');
  });

  it('nennt die Kontaktadresse von Gut gesagt und den Feedback-Knopf (#430)', () => {
    const kontakt = abschnitt(seite, 'Kontakt');
    const mail = seite.querySelector(`a[href="mailto:${ORGANISATION.kontaktMail}"]`);

    expect(kontakt).toContain(`Fragen und Hinweise zu Gut gesagt: ${ORGANISATION.kontaktMail}`);
    expect(kontakt).toContain('„Feedback“');
    expect(mail).not.toBeNull();
  });

});
