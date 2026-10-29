import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { DatenschutzComponent } from './datenschutz.component';

/**
 * Die Datenschutzerklaerung beschreibt, was die App tut (#222). Geprueft wird der Text,
 * den Lesende sehen, je Abschnitt: Ein Abschnitt reicht von seiner Ueberschrift (h2 oder
 * h3) bis zur naechsten Ueberschrift derselben oder hoeheren Ebene.
 */
describe('DatenschutzComponent', () => {
  let seite: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatenschutzComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    const fixture = TestBed.createComponent(DatenschutzComponent);
    fixture.detectChanges();
    seite = fixture.nativeElement as HTMLElement;
  });

  function normalisiert(text: string | null): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
  }

  function abschnitt(titel: string): string {
    const kopf = Array.from(seite.querySelectorAll('h2, h3')).find(
      (h) => normalisiert(h.textContent) === titel,
    );
    if (!kopf) {
      throw new Error(`Kein Abschnitt "${titel}"`);
    }
    const ebene = kopf.tagName === 'H2' ? ['H2'] : ['H2', 'H3'];
    const teile: string[] = [];
    let knoten = kopf.nextElementSibling;
    while (knoten && !ebene.includes(knoten.tagName)) {
      teile.push(knoten.textContent ?? '');
      knoten = knoten.nextElementSibling;
    }
    return normalisiert(teile.join(' '));
  }

  function ganzerText(): string {
    return normalisiert(seite.textContent);
  }

  describe('Rückmeldung zur Nutzung (#349)', () => {
    it('nennt die gespeicherte Zahl ohne Zeitpunkt, lit. f und die Frist bis zur Kontolöschung', () => {
      const text = abschnitt('Rückmeldung zur Nutzung Ihrer Beiträge');

      expect(text).toContain('Seit deinem letzten Besuch wurden deine Beiträge N-mal genutzt');
      expect(text).toContain('nur eine Zahl');
      expect(text).toContain('Wann Sie da waren, speichern wir nicht');
      expect(text).toContain('Artikel 6 Absatz 1 Buchstabe f DSGVO');
      expect(text).toContain('bis zur Löschung Ihres Kontos');
    });
  });

  describe('Suchen ohne Treffer und „Hier fehlt eine Antwort“ (#350, #370)', () => {
    it('nennt alle angemeldeten Mitwirkenden mit der Zahl der Personen, die Zahl der Suchen nur für Admins', () => {
      const text = abschnitt('Suchen ohne Treffer');

      expect(text).toContain('alle angemeldeten Mitwirkenden');
      expect(text).toContain('„Hier fehlt eine Antwort“');
      expect(text).toContain('Danach wurde ohne Treffer gesucht: n Personen');
      expect(text).toContain('die Zahl der Suchen sehen sie nicht');
      expect(text).toContain('Administratorinnen und Administratoren zusätzlich die Zahl der Suchen');
    });

    it('sagt, dass eine übernommene Suchanfrage die Kennung der anlegenden Person trägt', () => {
      const text = abschnitt('Suchen ohne Treffer');

      expect(text).toContain('trägt deren Kennung');
    });
  });
});
