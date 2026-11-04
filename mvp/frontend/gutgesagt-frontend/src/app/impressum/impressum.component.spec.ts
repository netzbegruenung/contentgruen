import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { abschnitt, istTagesdatum, normalisiert, stand } from '../testing/rechtstext';
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
    expect(abschnitt(seite, 'Kontaktstelle nach Art. 11 und 12 DSA')).toContain('auch ohne Konto nutzen kannst');
  });

  it('nennt für Meldungen nach Art. 16 DSA die Meldefunktion und die E-Mail-Adresse als gleichwertige Wege (#521)', () => {
    const text = abschnitt(seite, 'Kontaktstelle nach Art. 11 und 12 DSA');

    expect(text).toContain('Meldungen nach Artikel 16 DSA gehen über die Meldefunktion an jedem Beitrag');
    expect(text).toContain('oder per E-Mail an');
    expect(text).not.toContain('richtest du bitte per E-Mail an');
  });

  it('nennt keine Verantwortliche nach § 18 Abs. 2 MStV, weil Gut gesagt kein journalistisch-redaktionelles Angebot ist (#521)', () => {
    const text = normalisiert(seite.textContent);

    expect(text).not.toContain('§ 18 Abs. 2 MStV');
    expect(text).not.toContain('Verantwortlich für den Inhalt');
  });

  it('trägt das Tagesdatum der letzten Änderung als Stand, nicht nur den Monat (#498)', () => {
    const text = stand(seite);
    expect(istTagesdatum(text)).withContext(text).toBeTrue();
  });

  it('nennt die Kontaktadresse von Gut gesagt und den Feedback-Knopf (#430)', () => {
    const kontakt = abschnitt(seite, 'Kontakt');
    const mail = seite.querySelector(`a[href="mailto:${ORGANISATION.gutgesagtMail}"]`);

    expect(kontakt).toContain(`Fragen und Hinweise zu Gut gesagt: ${ORGANISATION.gutgesagtMail}`);
    expect(kontakt).toContain('„Feedback“');
    expect(mail).not.toBeNull();
  });
});
