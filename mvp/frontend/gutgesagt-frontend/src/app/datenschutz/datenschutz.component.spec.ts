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

  describe('Beitrag löschen durch den Autor (#250)', () => {
    it('sagt, dass ein gelöschter Beitrag nur ausgeblendet wird und erst auf Antrag ganz entfernt', () => {
      const text = abschnitt('Beiträge, die Sie einstellen');

      expect(text).toContain('nicht sofort aus unseren Daten entfernt');
      expect(text).toContain('lässt sich nicht zurückholen');
      expect(text).toContain('Vollständig entfernt wird er nur, wenn Sie uns darum bitten');
      expect(abschnitt('Ihre Rechte')).toContain('Das gilt auch für Beiträge, die Sie selbst gelöscht haben.');
    });
  });

  describe('Kennung (#284, #333, #385)', () => {
    it('spricht von der Kennung, nicht von der Nutzerkennung', () => {
      expect(ganzerText()).not.toContain('Nutzerkennung');
      expect(abschnitt('Anmeldung über die Netzbegrünung')).toContain(
        'eine Kennung (eine feste Zeichenfolge, die Ihr Konto bezeichnet, kein Name)',
      );
    });

    it('behauptet nicht mehr, angemeldete Browser bekämen die Kennung', () => {
      expect(ganzerText()).not.toContain('Technisch übermitteln wir an angemeldete Browser auch die Kennung');
      expect(abschnitt('Beiträge, die Sie einstellen')).toContain(
        'Ihre Kennung geben wir außer an Ihren eigenen Browser nur an Administratorinnen und Administratoren heraus',
      );
    });
  });

  describe('Suchvorgänge (#239, #289)', () => {
    it('nennt den Tag statt eines Zeitpunkts und die Frist von 90 Tagen mit Tageszähler', () => {
      const text = abschnitt('Suchvorgänge');

      expect(text).toContain('den Tag (keine Uhrzeit)');
      expect(text).toContain('nach 90 Tagen automatisch');
      expect(text).toContain('je Tag nur, wie oft gesucht wurde und von wie vielen verschiedenen Pseudonymen');
      expect(text).not.toContain('keine Löschfrist');
    });
  });

  describe('Feedback (#343)', () => {
    it('beschreibt Feedback ohne Kennung, nur für Admins, mit 180 Tagen Frist', () => {
      const text = abschnitt('Feedback');

      expect(text).toContain('auch ohne Konto');
      expect(text).toContain('Wir speichern dazu weder Ihre Kennung noch eine Sitzungskennung');
      expect(text).toContain('der Tag des Eingangs');
      expect(text).toContain('nur Administratorinnen und Administratoren');
      expect(text).toContain('nach 180 Tagen automatisch');
    });
  });

  describe('Einwürfe in den Fangkorb', () => {
    it('nennt keine Screenshots und statt „verarbeitende Person“ die Person, die den Einwurf verknüpft hat', () => {
      const text = abschnitt('Einwürfe in den Fangkorb');

      expect(ganzerText()).not.toContain('Screenshot');
      expect(ganzerText()).not.toContain('verarbeitenden Person');
      expect(text).toContain('die Kennung der Person, die den Einwurf mit einem Beitrag verknüpft hat');
    });

    it('sagt, dass Sätze an fremden Einwürfen nach einer Kontolöschung bleiben und „ehemalige Person“ zeigen', () => {
      const text = abschnitt('Einwürfe in den Fangkorb');

      expect(text).toContain('Ihre Sätze an Einwürfen anderer bleiben stehen');
      expect(text).toContain('„ehemalige Person“');
    });
  });

  describe('Kontolöschung (#278)', () => {
    it('nennt die Liste gelöschter Konten mit 14 Tagen', () => {
      expect(abschnitt('Ihre Rechte')).toContain('bis 14 Tage nach der Kontolöschung');
    });

    it('zählt die gespeicherte Zahl der Rückmeldung zu dem, was mit dem Konto geht', () => {
      expect(abschnitt('Ihre Rechte')).toContain('die gespeicherte Zahl für die Rückmeldung zur Nutzung');
    });
  });

  describe('Protokolldateien (#275)', () => {
    it('nennt für die Anwendung den Pfad ohne Suchtext und keine verweisende Seite', () => {
      const text = abschnitt('Zugriffe innerhalb der Anwendung');

      expect(text).toContain('ohne Suchtext und sonstige Zusätze in der Adresse');
      expect(text).toContain('aber nicht die verweisende Seite');
      expect(text).toContain('Für Suchen und für Aufrufe der Ergebnisseite schreibt er gar keine Zeile');
    });

    it('nimmt ältere Zeilen von der Zusage aus, dass keine Suchtexte darin stehen', () => {
      expect(abschnitt('Protokolle der Anwendung')).toContain('Ausnahme');
    });
  });

  describe('Weitere Korrekturen am Ist-Stand', () => {
    it('Meldungen: Kennung und Sitzungskennung stehen bei angemeldeten Meldungen nebeneinander', () => {
      expect(abschnitt('Meldungen von Beiträgen')).toContain('stehen also beide nebeneinander');
      expect(abschnitt('Verwendung von Beiträgen')).toContain(
        'es sei denn, Sie haben aus demselben Browser angemeldet eine Meldung abgegeben',
      );
    });

    it('Gerätespeicher: kein Kennzahlen-Eintrag, dafür Fangkorb-Filter und Teilen-Menü', () => {
      const text = abschnitt('Weitere Einträge');

      expect(text).not.toContain('Kennzahlen');
      expect(text).toContain('Ihre Filter im Fangkorb');
      expect(text).toContain('Teilen-Menü');
    });

    it('Anmelde-Cookie: enthält die Angaben des Identitätsdienstes, nicht nur drei', () => {
      expect(abschnitt('Anmelde-Cookie')).toContain(
        'die Angaben, die der Identitätsdienst bei der Anmeldung übermittelt',
      );
    });

    it('KI-Vorschlag für Bildunterschriften: abgeschaltet, vor dem Einschalten wird die Erklärung ergänzt', () => {
      const text = abschnitt('Keine Übermittlung außerhalb der EU');

      expect(text).toContain('Unterschrift');
      expect(text).toContain('ist auf dieser Plattform abgeschaltet');
    });
  });
});
