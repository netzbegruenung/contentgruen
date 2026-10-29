import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { NutzungsbedingungenComponent } from './nutzungsbedingungen.component';

/**
 * Die Nutzungsbedingungen sprechen die Sprache des Glossars und versprechen nur, was die
 * Moderation tut (#222). Geprueft wird der Text, den Lesende sehen, je Abschnitt.
 */
describe('NutzungsbedingungenComponent', () => {
  let seite: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NutzungsbedingungenComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    const fixture = TestBed.createComponent(NutzungsbedingungenComponent);
    fixture.detectChanges();
    seite = fixture.nativeElement as HTMLElement;
  });

  function normalisiert(text: string | null): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
  }

  /** Der Abschnitt, dessen Ueberschrift mit der Nummer beginnt, etwa „7.“. */
  function abschnittNummer(nummer: string): string {
    const kopf = Array.from(seite.querySelectorAll('h2')).find((h) =>
      normalisiert(h.textContent).startsWith(`${nummer} `),
    );
    if (!kopf) {
      throw new Error(`Kein Abschnitt ${nummer}`);
    }
    return normalisiert(kopf.parentElement?.textContent ?? null);
  }

  it('verwendet „Destillat“ nicht, das kein Glossarbegriff ist', () => {
    expect(normalisiert(seite.textContent)).not.toMatch(/Destillat/);
    expect(abschnittNummer('3.')).toContain('Dein Text');
  });

  it('nennt in Abschnitt 2 Einwerfen, Beitragen und Bewerten statt Kommentieren', () => {
    expect(abschnittNummer('2.')).toContain('Zum Einwerfen, Beitragen und Bewerten meldest du dich an');
  });

  it('beschreibt Sperren als Regelweg der Moderation', () => {
    const text = abschnittNummer('7.');

    expect(text).toContain('sperren wir ihn');
    expect(text).toContain('Eine Meldung allein sperrt nichts');
    expect(text).not.toContain('entfernen rechtswidrige Inhalte, sobald wir Kenntnis erlangen');
  });
});
