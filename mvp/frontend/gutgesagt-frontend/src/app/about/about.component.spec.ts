import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';

import { AboutComponent } from './about.component';

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

  it('sagt, dass Menschen den Startbestand schreiben und alle Zahlen echt sind', () => {
    const text = seite.querySelector('.startbestand')!.textContent!;

    expect(text).toContain('Gründungsteam');
    expect(text).toContain('jeden Beitrag verantwortet ein Mensch');
    expect(text).toContain('beginnen bei 0');
  });

  it('nennt CC0 und verlinkt die Nutzungsbedingungen', () => {
    const abschnitt = seite.querySelector('.cc0')!;

    expect(abschnitt.textContent).toContain('CC0');
    expect(abschnitt.querySelector('a')!.getAttribute('href')).toBe('/nutzungsbedingungen');
  });

  it('sagt, dass es keine offizielle Linie gibt', () => {
    const abschnitt = seite.querySelector('.linie')!;

    expect(abschnitt.querySelector('h2')!.textContent).toContain('Keine offizielle Linie');
    expect(abschnitt.textContent).toContain('nur als Herkunft');
  });

  it('öffnet die Hilfe', () => {
    const dialog = TestBed.inject(MatDialog);

    (seite.querySelector('.hilfe-knopf') as HTMLButtonElement).click();

    expect(dialog.open).toHaveBeenCalled();
  });
});
