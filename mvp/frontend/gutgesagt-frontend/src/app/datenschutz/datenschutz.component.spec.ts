import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { abschnitt as abschnittIn, normalisiert } from '../testing/rechtstext';
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

  function abschnitt(titel: string): string {
    return abschnittIn(seite, titel);
  }

  function ganzerText(): string {
    return normalisiert(seite.textContent);
  }

  describe('Anrede (Entscheidung 29.10.2026)', () => {
    it('duzt die Lesenden', () => {
      expect(ganzerText()).not.toMatch(/\b(Ihr|Ihre|Ihren|Ihrem|Ihrer|Ihres|Ihnen)\b/);
      expect(ganzerText()).not.toMatch(/\b(können|möchten|haben) Sie\b/);
      expect(abschnitt('Deine Rechte')).toContain('Wende dich dafür an');
    });
  });

  describe('Rückmeldung zur Nutzung (#349)', () => {
    it('nennt die gespeicherte Zahl ohne Zeitpunkt, lit. f und die Frist bis zur Kontolöschung', () => {
      const text = abschnitt('Rückmeldung zur Nutzung deiner Beiträge');

      expect(text).toContain('Seit deinem letzten Besuch wurden deine Beiträge N-mal genutzt');
      expect(text).toContain('nur eine Zahl');
      expect(text).toContain('Wann du da warst, speichern wir nicht');
      expect(text).toContain('Artikel 6 Absatz 1 Buchstabe f DSGVO');
      expect(text).toContain('bis zur Löschung deines Kontos');
    });
  });

  describe('Suchen ohne Treffer und „Hier fehlt eine Antwort“ (#350, #370)', () => {
    it('nennt alle angemeldeten Mitwirkenden mit der Zahl der Personen, die Zahl der Suchen nur für Admins', () => {
      const text = abschnitt('Suchen ohne Treffer');

      expect(text).toContain('alle angemeldeten Mitwirkenden');
      expect(text).toContain('„Hier fehlt eine Antwort“');
      expect(text).toContain('Danach wurde ohne Treffer gesucht: n Personen');
      expect(text).toContain('die Zahl der Suchen sehen sie nicht');
      expect(text).toContain('Administratorinnen und Administratoren, zusätzlich mit der Zahl der Suchen');
    });

    it('bezieht die Zwei-Personen-Schwelle auf die Listen, nicht auf die Auffindbarkeit', () => {
      const text = abschnitt('Suchen ohne Treffer');

      expect(text).toContain('Auf die Listen der Suchen ohne Treffer kommt ein Eintrag erst');
      expect(text).not.toContain('Ein Eintrag wird erst sichtbar');
    });

    it('sagt, dass eine übernommene Suchanfrage die Kennung der anlegenden Person trägt', () => {
      const text = abschnitt('Suchen ohne Treffer');

      expect(text).toContain('Die Aussage gilt danach als von ihr angelegt und trägt ihre Kennung');
    });
  });

  describe('Wortlaut des CC0-Hinweises (#431)', () => {
    it('nennt die Kennung des Wortlauts an Beitrag, Satz und Einwurf mit Zweck und Rechtsgrundlage', () => {
      const text = abschnitt('Beiträge, die du einstellst');

      expect(text).toContain('An jedem Beitrag, jedem Satz und jedem Einwurf speichern wir außerdem');
      expect(text).toContain('welchen Wortlaut des Hinweises zur CC0-Freigabe');
      expect(text).toContain('die Freigabe nachweisen zu können');
    });
  });

  describe('Suchanfragen (#436)', () => {
    it('sagt, ab wann eine gespeicherte Suchanfrage für alle sichtbar ist', () => {
      const text = abschnitt('Deine Suchanfragen');

      expect(text).toContain('kann danach für alle auffindbar werden');
      expect(text).not.toContain('ist danach für alle auffindbar');
      expect(text).toContain('nur unseren Administratorinnen und Administratoren');
      expect(text).toContain('mindestens zwei verschiedene Personen innerhalb von vier Wochen');
      expect(text).toContain('Gib nichts in das Suchfeld ein, was nicht öffentlich werden soll');
    });
  });

  describe('Beitrag löschen durch den Autor (#250, #421)', () => {
    it('sagt, dass ein gelöschter Beitrag nach 30 Tagen samt Bewertungen endgültig entfernt wird', () => {
      const text = abschnitt('Beiträge, die du einstellst');

      expect(text).toContain('nicht sofort aus unseren Daten entfernt');
      expect(text).toContain('lässt sich nicht zurückholen');
      expect(text).toContain('Er bleibt noch 30 Tage mit deiner Kennung gespeichert');
      expect(text).toContain('Danach entfernen wir ihn endgültig, samt der Bewertungen daran');
      expect(text).toContain('spätestens 31 Tage nach dem Löschen');
      expect(text).not.toContain('Vollständig entfernt wird er nur');
      expect(abschnitt('Deine Rechte')).toContain('Das gilt auch für Beiträge, die du selbst gelöscht hast.');
    });
  });

  describe('Löschfristen (#421)', () => {
    it('Meldungen: 180 Tage nach der Bearbeitung, offene ohne Frist', () => {
      const text = abschnitt('Meldungen von Beiträgen');

      expect(text).toContain('180 Tage nach ihrer Bearbeitung automatisch');
      expect(text).toContain('Offene Meldungen haben keine Frist');
      expect(text).toContain('Artikel 20 DSA');
      expect(text).not.toContain('keine Löschfrist');
    });

    it('Sperren: Kennung des Autors, Widerspruch, 180 Tage nach der Aufhebung (#448)', () => {
      const text = abschnitt('Sperren von Beiträgen und Widerspruch');

      expect(text).toContain('Kennung der Person, die den Beitrag eingestellt hat');
      expect(text).toContain('in „Meine Beiträge“');
      expect(text).toContain('Eine E-Mail schicken wir dazu nicht');
      expect(text).toContain('Artikel 17 und 20 DSA');
      expect(text).toContain('180 Tage danach automatisch');
      expect(text).toContain('entfernen wir deine Kennung und deinen Widerspruchstext');
    });

    it('Einwürfe: 365 Tage nach der letzten Arbeit, ausformulierte so lange wie ihr Beitrag', () => {
      const text = abschnitt('Einwürfe in den Fangkorb');

      expect(text).toContain('365 Tage nach der letzten Arbeit daran');
      expect(text).toContain('das gilt auch für verworfene Einwürfe');
      expect(text).toContain('bleibt er so lange wie dieser Beitrag');
      expect(text).not.toContain('keine Löschfrist');
    });

    it('Bewertungen: gehen mit dem endgültig entfernten Beitrag', () => {
      const text = abschnitt('Bewertungen');

      expect(text).toContain('der bewertete Beitrag endgültig entfernt wird');
      expect(text).not.toContain('keine Löschfrist');
    });
  });

  describe('Fassungen (#355)', () => {
    it('nennt die kopierte Fassung eines Kommentars und den Zähler je Fassung', () => {
      const text = abschnitt('Verwendung von Beiträgen');

      expect(text).toContain('bei einem Kommentar auch welche Fassung (kurz, mittel oder lang)');
      expect(text).toContain('Zähler pro Beitrag, bei Kommentaren auch je Fassung');
    });
  });

  describe('Gegenlesen (#358)', () => {
    it('nennt feste Regeln ohne KI, keine Speicherung und die flüchtige Zählung', () => {
      const text = abschnitt('Gegenlesen beim Schreiben');

      expect(text).toContain('gegen feste Schreibregeln');
      expect(text).toContain('ohne KI');
      expect(text).toContain('wir speichern weder deinen Entwurf noch die Anmerkungen');
      expect(text).toContain('höchstens etwa elf Minuten');
      expect(text).toContain('Artikel 6 Absatz 1 Buchstabe b DSGVO');
    });
  });

  describe('Kennung (#284, #333, #385)', () => {
    it('spricht von der Kennung, nicht von der Nutzerkennung', () => {
      expect(ganzerText()).not.toContain('Nutzerkennung');
      expect(abschnitt('Anmeldung über die Netzbegrünung')).toContain(
        'eine Kennung (eine feste Zeichenfolge, die dein Konto bezeichnet, kein Name)',
      );
    });

    it('behauptet nicht mehr, angemeldete Browser bekämen die Kennung', () => {
      expect(ganzerText()).not.toContain('Technisch übermitteln wir an angemeldete Browser auch die Kennung');
      expect(abschnitt('Beiträge, die du einstellst')).toContain(
        'Deine Kennung geben wir außer an deinen eigenen Browser nur an Administratorinnen und Administratoren heraus',
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
      expect(text).toContain('Wir speichern dazu weder deine Kennung noch eine Sitzungskennung');
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

    it('nennt die Zeitpunkte an Sätzen und an der Verknüpfung', () => {
      const text = abschnitt('Einwürfe in den Fangkorb');

      expect(text).toContain('mit der Kennung der Person, die sie gespeichert hat, und dem Zeitpunkt');
      expect(text).toContain('der Zeitpunkt dieser Verknüpfung');
    });

    it('sagt, dass Sätze an fremden Einwürfen nach einer Kontolöschung bleiben und „ehemalige Person“ zeigen', () => {
      const text = abschnitt('Einwürfe in den Fangkorb');

      expect(text).toContain('Deine Sätze an Einwürfen anderer bleiben stehen');
      expect(text).toContain('„ehemalige Person“');
    });
  });

  describe('Kontolöschung (#278)', () => {
    it('nennt die Liste gelöschter Konten nur für den Netzbegrünung-Login, von Hand gepflegt', () => {
      const text = abschnitt('Deine Rechte');

      expect(text).toContain('Hast du dich über die Netzbegrünung angemeldet');
      expect(text).toContain('Liste gelöschter Konten');
      expect(text).toContain('von Hand wieder aus');
      expect(text).toContain('in der Regel 14 Tage nach der Kontolöschung');
      expect(ganzerText()).not.toContain('Sperrliste');
    });

    it('zählt die gespeicherte Zahl der Rückmeldung zu dem, was mit dem Konto geht', () => {
      expect(abschnitt('Deine Rechte')).toContain('die gespeicherte Zahl für die Rückmeldung zur Nutzung');
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

  describe('Rückschlüsse auf die politische Haltung (Art. 9, Entscheidung 29.10.2026)', () => {
    it('nennt Art. 9, ohne bis #429 eine Rechtsgrundlage zu behaupten', () => {
      const text = abschnitt('Rückschlüsse auf deine politische Haltung');

      expect(text).toContain('Artikel 9 DSGVO');
      expect(text).toContain('Wir werten deine Mitwirkung nicht danach aus, welche politische Haltung du hast');
      expect(text).not.toContain('Rechtsgrundlage');
      expect(text).not.toContain('Einwilligung');
    });
  });

  describe('Weitere Korrekturen am Ist-Stand', () => {
    it('Meldungen: Kennung und Sitzungskennung stehen bei angemeldeten Meldungen nebeneinander', () => {
      expect(abschnitt('Meldungen von Beiträgen')).toContain('stehen also beide nebeneinander');
      expect(abschnitt('Verwendung von Beiträgen')).toContain(
        'es sei denn, du hast aus demselben Browser angemeldet eine Meldung abgegeben',
      );
    });

    it('Verwendung: nicht gespeichert wird der User-Agent, die Sitzungskennung schon', () => {
      expect(abschnitt('Verwendung von Beiträgen')).toContain('die genaue Bezeichnung deines Browsers (User-Agent)');
    });

    it('Gerätespeicher: kein Kennzahlen-Eintrag, dafür Fangkorb-Filter, Teilen-Menü und Service Worker', () => {
      const text = abschnitt('Weitere Einträge');

      expect(text).not.toContain('Kennzahlen');
      expect(text).toContain('deine Filter im Fangkorb');
      expect(text).toContain('Teilen-Menü');
      expect(text).toContain('Service Worker');
    });

    it('Gerätespeicher: das Profilbild liegt nur nach eigener Wahl im Browser, bis zum Zurücksetzen (#437)', () => {
      const text = abschnitt('Weitere Einträge');

      expect(text).not.toContain('das Profilbild, das dir angezeigt wird');
      expect(text).toContain('wenn du es selbst wählst');
      expect(text).toContain('bis du die Wahl zurücksetzt');
      expect(text).toContain('Ohne eigene Wahl speichern wir nichts');
    });

    it('Anmelde-Cookie: Angaben des Identitätsdienstes nur bei der Anmeldung über die Netzbegrünung', () => {
      expect(abschnitt('Anmelde-Cookie')).toContain(
        'bei der Anmeldung über die Netzbegrünung dazu die übrigen Angaben, die ihr Identitätsdienst übermittelt',
      );
    });

    it('KI-Vorschlag für Bildunterschriften: abgeschaltet, vor dem Einschalten wird die Erklärung ergänzt', () => {
      const text = abschnitt('Keine Übermittlung außerhalb der EU');

      expect(text).toContain('Unterschrift');
      expect(text).toContain('ist auf dieser Plattform abgeschaltet');
    });
  });

  describe('Bilder von fremden Servern (#447)', () => {
    it('sagt, dass der Browser ein fremdes Bild erst auf Klick lädt und ohne Klick nichts an den Server geht', () => {
      const text = abschnitt('Bilder von fremden Servern');

      expect(text).toContain('Platzhalter „Bild laden“');
      expect(text).toContain('Erst wenn du darauf klickst, lädt dein Browser dieses eine Bild');
      expect(text).toContain('Ohne deinen Klick erfährt der fremde Server nichts von dir');
      expect(text).toContain('Den Klick merken wir uns nicht');
      expect(text).toContain('ohne Konto');
      expect(text).toContain('Artikel 6 Absatz 1 Buchstabe f DSGVO');
      expect(text).not.toContain('Dein Browser lädt sie direkt von dem fremden Server');
    });
  });
});
