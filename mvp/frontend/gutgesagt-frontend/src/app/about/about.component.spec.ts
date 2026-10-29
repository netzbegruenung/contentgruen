import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';

import { AboutComponent } from './about.component';
import { ORGANISATION } from '../shared/organisation';
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
    expect(text).toContain('jeden Beitrag verantwortet ein Mensch');
    expect(text).toContain('Jeder Beitrag beginnt bei 0 Stimmen und 0 Nutzungen');
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

    expect(abschnitt.querySelector(`a[href="mailto:${ORGANISATION.kontaktMail}"]`)).not.toBeNull();
    expect(abschnitt.querySelector(`a[href="${ORGANISATION.chat.url}"]`)).toBeNull();

    (abschnitt.querySelector('.feedback-knopf') as HTMLButtonElement).click();

    expect(TestBed.inject(MatDialog).open).toHaveBeenCalledWith(FeedbackDialogComponent, jasmine.anything());
  });

  it('öffnet die Hilfe', () => {
    const dialog = TestBed.inject(MatDialog);

    (seite.querySelector('.hilfe-knopf') as HTMLButtonElement).click();

    expect(dialog.open).toHaveBeenCalled();
  });
});
