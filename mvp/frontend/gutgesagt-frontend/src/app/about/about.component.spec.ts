import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';

import { AboutComponent } from './about.component';
import { ORGANISATION } from '../shared/organisation';
import { KEINE_GENERATIVE_KI, SUCHE_MIT_SPRACHMODELLEN } from '../shared/ki-saetze';
import { FeedbackDialogComponent } from '../shared/feedback/feedback-dialog.component';

/** Text eines Elements mit einfachen Leerzeichen, damit Umbrüche im Template keine Rolle spielen. */
function einzeilig(element: Element): string {
  return element.textContent!.replace(/\s+/g, ' ');
}

describe('AboutComponent', () => {
  let fixture: ComponentFixture<AboutComponent>;
  let seite: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AboutComponent],
      providers: [provideRouter([]), { provide: MatDialog, useValue: { open: jasmine.createSpy('open') } }],
    }).compileComponents();

    fixture = TestBed.createComponent(AboutComponent);
    fixture.detectChanges();
    seite = fixture.nativeElement;
  });

  it('spricht nicht vom Widerlegen von Falschbehauptungen', () => {
    const text = seite.textContent!.toLowerCase();

    for (const wort of ['widerleg', 'falschbehauptung', 'falschinformation', 'fake news', 'desinformation']) {
      expect(text).withContext(wort).not.toContain(wort);
    }
  });

  it('sagt im Kopf, worum es geht: Antworten, die Unentschiedene mitnehmen, gesammelt von vielen', () => {
    const kopf = seite.querySelector('.hero-section')!;

    expect(kopf.querySelector('h1')!.textContent).toContain('Über Gut gesagt');
    expect(kopf.textContent).toContain('Antworten, die Unentschiedene mitnehmen');
    expect(kopf.textContent).toContain('Gesammelt und verbessert von vielen');
  });

  it('zeigt das Logo im neuen Auftritt', () => {
    expect(seite.querySelector('.hero-section img')!.getAttribute('src')).toBe('marke/logo.svg');
  });

  it('richtet die Antworten an die Mitlesenden', () => {
    const abschnitt = seite.querySelector('.mitlesende')!;

    expect(abschnitt.querySelector('h2')!.textContent).toContain('Für die Mitlesenden');
    expect(abschnitt.textContent).toContain('Unentschiedenen');
    expect(abschnitt.querySelector('.nicht-jede-aussage')!.textContent).toContain(
      'Nicht jede Aussage braucht eine Antwort',
    );
  });

  it('erklärt die Kette in der Reihenfolge Einwerfen, Destillieren, Ausformulieren', () => {
    const schritte = Array.from(seite.querySelectorAll('.mitmachen .kette > li')).map(
      (li) => li.querySelector('strong')!.textContent,
    );

    expect(schritte).toEqual(['Einwerfen:', 'Destillieren:', 'Ausformulieren:']);
  });

  it('zählt als Nutzung nur das Kopieren fremder Beiträge, Teilen gibt es noch nicht', () => {
    const text = einzeilig(seite.querySelector('.mitmachen')!);

    expect(text).toContain('Kopiert jemand einen fremden Beitrag, zählt das als Nutzung');
    expect(text).not.toContain('Teilen');
  });

  it('sagt, dass Menschen den Startbestand schreiben und jeder Beitrag bei 0 beginnt', () => {
    const text = einzeilig(seite.querySelector('.startbestand')!);

    expect(text).toContain('Gründungsteam');
    expect(text).not.toContain('Startkont');
    expect(text).toContain(KEINE_GENERATIVE_KI);
    expect(text).toContain('Jeder Beitrag beginnt bei 0 Stimmen und 0 Nutzungen');
  });

  // Persona-Test Gerd: „KI schlägt höchstens etwas vor“ las er als Hintertür
  it('sagt zu KI dasselbe wie die Hilfe und nennt die Modelle', () => {
    const text = einzeilig(seite);
    const ki = einzeilig(seite.querySelector('.technik-ki')!);
    const modelle = einzeilig(seite.querySelector('.technik-modelle')!);

    expect(text).not.toContain('KI schlägt');
    expect(text).not.toContain('KI hilft');
    expect(ki).toContain(KEINE_GENERATIVE_KI);
    expect(ki).toContain(SUCHE_MIT_SPRACHMODELLEN);
    expect(modelle).toContain('multilingual-e5-base');
    expect(modelle).toContain('mDeBERTa-v3');
    // Der Bestaetiger (NLI_BESTAETIGER_MODELL, core/config.py) liegt im Image und ist zuschaltbar
    expect(modelle).toContain('Zwei weitere');
    expect(modelle).toContain('XLM-RoBERTa-large');
    expect(modelle).toContain('nach festen Regeln');
  });

  it('nennt CC0 und verlinkt die Nutzungsbedingungen', () => {
    const abschnitt = seite.querySelector('.cc0')!;

    expect(abschnitt.textContent).toContain('Die Texte der Beiträge stehen unter CC0');
    expect(abschnitt.querySelector('a')!.getAttribute('href')).toBe('/nutzungsbedingungen');
  });

  it('sagt, dass es keine offizielle Linie gibt', () => {
    const abschnitt = seite.querySelector('.linie')!;

    expect(abschnitt.querySelector('h2')!.textContent).toContain('Keine offizielle Linie');
    expect(abschnitt.textContent).toContain('nur als Herkunft');
  });

  it('ordnet die Zeitleiste unter ihre h2 ein, ohne Stufe zu überspringen', () => {
    expect(seite.querySelectorAll('.timeline h4').length).toBe(0);
    expect(seite.querySelectorAll('.timeline-item > h3').length).toBe(3);
  });

  it('nimmt Kontakt-Links aus der Organisationskonstante', () => {
    const links = Array.from(seite.querySelectorAll('a[target="_blank"]')).map((a) => a.getAttribute('href'));

    expect(links.filter((href) => href === ORGANISATION.chat.url).length).toBe(1);
    expect(links).toContain(ORGANISATION.url);
  });

  it('schickt Feedback in die App und nennt die Kontaktadresse, nicht den Chat (#290, #430)', () => {
    const abschnitt = seite.querySelector('.feedback-kontakt')!;

    expect(abschnitt.querySelector(`a[href="mailto:${ORGANISATION.gutgesagtMail}"]`)).not.toBeNull();
    expect(abschnitt.querySelector(`a[href="${ORGANISATION.chat.url}"]`)).toBeNull();

    (abschnitt.querySelector('.feedback-knopf') as HTMLButtonElement).click();

    expect(TestBed.inject(MatDialog).open).toHaveBeenCalledWith(FeedbackDialogComponent, jasmine.anything());
  });

  it('öffnet die Hilfe', () => {
    const dialog = TestBed.inject(MatDialog);

    (seite.querySelector('.hilfe-knopf') as HTMLButtonElement).click();

    expect(dialog.open).toHaveBeenCalled();
  });

  it('erklärt unter „Bewerten“ das Siegel mit Beispielen von neu bis Güte 10 (#427)', () => {
    expect(seite.querySelector('.siegel-absatz')!.textContent).toContain('Das Siegel zeigt die Güte eines Beitrags');
    const beispiele = Array.from(seite.querySelectorAll('.siegel-beispiele app-siegel svg')).map((svg) =>
      svg.getAttribute('aria-label'),
    );
    expect(beispiele.length).toBe(13);
    expect(beispiele[0]).toBe('Siegel: neu, noch keine Güte');
    expect(beispiele[10]).toBe('Siegel: Güte 10 von 10');
    // Glanz und Krone als Beispiel (#351)
    expect(seite.querySelectorAll('.siegel-beispiele .siegel-glanz').length).toBe(1);
    expect(beispiele[11]).toBe('Siegel: Güte 7 von 10, mit Glanz');
    expect(beispiele[12]).toBe('Siegel: Güte 7 von 10, mit Krone');
    expect(seite.querySelectorAll('.siegel-beispiele .siegel-krone').length).toBe(1);
    expect(seite.querySelector('.siegel-absatz')!.textContent).toContain('Die Krone sehen nur Angemeldete.');
  });
});
