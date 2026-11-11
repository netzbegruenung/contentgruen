import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { abschnitt as abschnittIn, istTagesdatum, normalisiert, stand } from '../testing/rechtstext';
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

  describe('Stand (#498)', () => {
    it('trägt das Tagesdatum der letzten Änderung, nicht nur den Monat', () => {
      const text = stand(seite);
      expect(istTagesdatum(text)).withContext(text).toBeTrue();
    });

    it('lässt Monat ohne Tag und einen Tag, den es nicht gibt, nicht gelten', () => {
      expect(istTagesdatum('November 2026')).toBeFalse();
      expect(istTagesdatum('31. September 2026')).toBeFalse();
      expect(istTagesdatum('29. Februar 2028')).toBeTrue();
    });
  });

  describe('Rückmeldung „Ja, gepostet“ (#643)', () => {
    it('nennt Prüfwert statt Kennung, kein Beitrag, Wochenfrist, lit. f und die Art.-9-Einwilligung', () => {
      const text = abschnitt('Rückmeldung „Ja, gepostet“');

      expect(text).toContain('nur einen Prüfwert');
      expect(text).toContain('welchen Beitrag du gepostet hast, speichern wir nicht');
      expect(text).toContain('bis kurz nach Ende der Kalenderwoche');
      expect(text).toContain('Widerrufst du sie, erscheint die Frage nicht mehr');
      expect(text).toContain('Artikel 6 Absatz 1 Buchstabe f DSGVO');
      expect(text).toContain('Artikel 9 Absatz 2 Buchstabe a DSGVO');
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
      expect(text).toContain('n Personen suchten das ohne Treffer');
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
      expect(text).toContain('Zähler pro Beitrag (alle Kopien und die ersten Kopien je Person und Tag), bei Kommentaren auch je Fassung');
    });
  });

  describe('Entdoppelte Nutzung, Punkte und Muster-Hinweise (#476, #499)', () => {
    it('Verwendung: Vermerk der ersten Kopie je Person und Tag, ablesbar „dieselbe Person“, nicht wer', () => {
      const text = abschnitt('Verwendung von Beiträgen');

      expect(text).toContain('ob es an diesem Tag die erste Kopie dieses Beitrags durch dieselbe Person war');
      expect(text).toContain('dass mehrere Vorgänge an einem Beitrag am selben Tag von derselben Person');
      expect(text).toContain('aber nicht, von wem');
      expect(text).not.toContain('noch ob mehrere Vorgänge vom selben Gerät kamen');
      expect(text).not.toContain('und ein Pseudonym werden dabei nicht gespeichert');
    });

    it('Verwendung: Prüfwert bis Tagesende mit einem täglichen Schlüssel nur im Arbeitsspeicher', () => {
      const text = abschnitt('Verwendung von Beiträgen');

      expect(text).toContain('bis zum Ende des Tages einen Prüfwert');
      expect(text).toContain('jeden Tag neu zufällig erzeugt, nur im Arbeitsspeicher hält und nirgends speichert');
      expect(text).toContain('Prüfwerte bleiben nur bis zum Ende ihres Tages');
    });

    it('Verwendung: Kopien durch Startkonten zählen nicht', () => {
      expect(abschnitt('Verwendung von Beiträgen')).toContain('(Startkonten), zählen wir gar nicht');
    });

    it('Punkte: noch aus, nur für dich sichtbar, nicht gespeichert', () => {
      const text = abschnitt('Punkte');

      expect(text).toContain('Punkte sind noch nicht eingeschaltet');
      expect(text).toContain('siehst nur du');
      expect(text).toContain('Wir speichern ihn nicht, sondern berechnen ihn bei jedem Abruf');
    });

    it('Punkte: Paar-Prüfwert sieben Tage, Muster-Hinweis acht Wochen, nur für Admins, Einwilligung als Rechtsgrundlage', () => {
      const text = abschnitt('Punkte');

      expect(text).toContain('für sieben Tage einen Paar-Prüfwert');
      expect(text).toContain('ohne den Beitrag und ohne das Datum');
      expect(text).toContain('Muster-Hinweis');
      expect(text).toContain('nur unsere Administratorinnen und Administratoren');
      expect(text).toContain('Muster-Hinweise acht Wochen nach dem letzten auffälligen Tag');
      expect(text).toContain('Artikel 6 Absatz 1 Buchstabe a und Artikel 9 Absatz 2 Buchstabe a DSGVO');
    });

    it('Punkte: ohne Einwilligung keine Punkte, kein Paar-Prüfwert, kein Muster-Hinweis (#562)', () => {
      const text = abschnitt('Punkte');

      expect(text).toContain('Ohne diese Einwilligung (nie erteilt oder widerrufen) hat dein Konto keine Punkte');
      expect(text).toContain('weder ein Paar-Prüfwert noch ein Muster-Hinweis, der es nennt');
      expect(text).toContain('Kopien, die ein Konto ohne Einwilligung macht, bringen niemandem Punkte');
      expect(text).not.toContain('Bevor wir Punkte einschalten');
    });

    it('Verwendung: Kopien ohne Einwilligung ohne Prüfwert, nur im Zähler aller Kopien (#562)', () => {
      const text = abschnitt('Verwendung von Beiträgen');

      expect(text).toContain('Kopien angemeldeter Konten ohne Einwilligung');
      expect(text).toContain('bekommen keinen Prüfwert');
      expect(text).toContain('nicht für „Diese Woche oft genutzt“ und nicht für Punkte');
    });

    it('Rückmeldung: Muster-Hinweise als einzige Ausnahme von „wer genutzt hat, zeigen wir nicht“', () => {
      const text = abschnitt('Rückmeldung zur Nutzung deiner Beiträge');

      expect(text).toContain('Wer deine Beiträge genutzt hat, wissen wir nicht und zeigen wir nicht');
      expect(text).toContain('Einzige Ausnahme, sobald Punkte eingeschaltet sind');
      expect(text).toContain('ohne die genutzten Beiträge (siehe „Punkte“)');
    });

    it('Profiling: nur mit eingeschalteten Punkten, ohne Folgen', () => {
      const text = abschnitt('Keine automatisierte Entscheidungsfindung');

      expect(text).toContain('solange Punkte ausgeschaltet sind');
      expect(text).toContain('hat keine Folgen für dich');
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

    it('nennt den Kürzungsvorschlag: ohne KI, nicht gespeichert, erst beim Übernehmen in der Kurzfassung (#403, #550)', () => {
      const text = abschnitt('Gegenlesen beim Schreiben');

      expect(text).toContain('Kürzungsvorschlag');
      expect(text).toContain('der Vorschlag entsteht ohne KI, wird nicht gespeichert');
      expect(text).toContain('erst in der Kurzfassung, wenn du ihn übernimmst');
      expect(text).toContain('oder einen Kürzungsvorschlag anfragt');
    });

    it('nennt die Spracherkennung für Beiträge und neue Aussagen, auch beim Vorab-Anlegen (#405, #550)', () => {
      const text = abschnitt('Gegenlesen beim Schreiben');

      expect(text).toContain('lokale Spracherkennung');
      expect(text).toContain('zeigt dir dann einen Sprachhinweis');
      expect(text).toContain('neue Aussage');
      expect(text).toContain('„Aussage vorab anlegen“');
      expect(text).toContain('Titel und Text des Beitrags (beim Bild die Unterschrift)');
      expect(text).toContain('auch davon speichern wir nichts');
      expect(text).toContain('wie oft dein Konto gegenlesen lässt, die Spracherkennung fragt');
    });
  });

  describe('Ändern eigener Beiträge (#299, #550)', () => {
    it('beschreibt den Änderungsverlauf mit Kennung und Zeitpunkt, ohne den alten Wortlaut', () => {
      const text = abschnitt('Beiträge, die du einstellst');

      expect(text).toContain('Kommentar oder deine Hintergrundinfo kannst du unter „Meine Beiträge“ ändern');
      expect(text).toContain('Änderungsverlauf');
      expect(text).toContain('deine Kennung und den Zeitpunkt');
      expect(text).toContain('Den alten Wortlaut bewahren wir nicht auf');
      expect(text).not.toContain('Eine Bearbeitungsgeschichte führen wir nicht');
      expect(text).not.toContain('lassen sich derzeit gar nicht ändern');
      expect(text).not.toContain('Solange ein Beitrag nicht geändert werden kann');
    });

    it('nimmt die Kennung im Änderungsverlauf in die Anonymisierung bei Kontolöschung auf', () => {
      const text = abschnitt('Beiträge, die du einstellst');

      expect(text).toContain('an allen genannten Stellen, auch im Änderungsverlauf, durch einen Platzhalter');
    });

    it('stützt den Änderungsverlauf auch in der Zusammenfassung auf lit. f', () => {
      const text = abschnitt('Beiträge, die du einstellst');

      expect(text).toContain('für die Herkunftsangabe am Beitrag und den Änderungsverlauf');
    });

    it('sagt, dass eine entfernte Herkunft als Herkunft gespeichert bleibt', () => {
      const text = abschnitt('Beiträge, die du einstellst');

      expect(text).toContain('Eine Herkunft, die du dabei entfernst, verschwindet vom Beitrag, bleibt aber als Herkunft gespeichert');
    });

    it('nennt beim CC0-Wortlaut, dass Ändern die Kennung ersetzt', () => {
      const text = abschnitt('Beiträge, die du einstellst');

      expect(text).toContain('tritt die Kennung des Wortlauts, den dir das Formular zum Ändern gezeigt hat, an die Stelle der bisherigen');
      expect(text).toContain('Was du vor dem 29.10.2026 eingestellt und seither nicht geändert hast');
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

  describe('Eigener Realm und Einladungen (#490)', () => {
    it('nennt den eigenen Realm als Anmeldedienst und keine Selbstregistrierung ohne Einladung', () => {
      const text = abschnitt('Anmeldung und Zugang');

      expect(text).toContain('Realm „gutgesagt“');
      expect(text).toContain('Ohne Einladung kann niemand selbst ein Konto anlegen');
      expect(text).not.toContain('eine Selbstregistrierung gibt es nicht');
      // Bis zur Umstellung gilt noch die direkte Anmeldung bei der Netzbegrünung.
      expect(text).toContain('Bis wir die Anmeldung umgestellt haben');
    });

    it('Einladung: Mail-Adresse an den Anmeldedienst, Mail über dessen Mailserver, keine Adresse an der Einladung', () => {
      const text = abschnitt('Konto aus einer Einladung');

      expect(text).toContain('gibst du eine E-Mail-Adresse ein');
      expect(text).toContain('über seinen Mailserver');
      expect(text).toContain('Die Plattform selbst speichert und protokolliert deine E-Mail-Adresse nicht');
      expect(text).toContain('An der Einladung speichern wir nur, wie oft sie eingelöst wurde');
      expect(text).toContain('Am Konto steht nicht, über welche Einladung es entstand');
      expect(text).toContain('Artikel 6 Absatz 1 Buchstabe b DSGVO');
    });

    it('Einladung: IP-Adresse nur flüchtig für die Begrenzung der Aufrufe', () => {
      const text = abschnitt('Konto aus einer Einladung');

      expect(text).toContain('deine IP-Adresse');
      expect(text).toContain('nur flüchtig im Arbeitsspeicher');
      expect(text).toContain('spätestens 16 Minuten');
      expect(text).toContain('Artikel 6 Absatz 1 Buchstabe f DSGVO');
    });

    it('Netzbegrünung: Konto vorab mit der Mail-Adresse aus dem Realm der Netzbegrünung, ohne Mail (#527)', () => {
      const text = abschnitt('Anmeldung über die Netzbegrünung');

      expect(text).toContain('legen wir das Konto im Anmeldedienst vorab an');
      expect(text).toContain('mit deiner E-Mail-Adresse aus dem Identitätsdienst der Netzbegrünung');
      expect(text).toContain('Eine E-Mail bekommst du dabei nicht');
    });

    it('Wo deine Daten liegen: Anmeldedienst samt Mailversand beim Auftragsverarbeiter (Entscheidung 03.11.2026)', () => {
      const text = abschnitt('Wo deine Daten liegen');

      expect(text).toContain('Dazu gehört auch der Anmeldedienst samt Mailversand. Weitere Empfänger gibt es nicht.');
    });

    it('Pflichtangaben: E-Mail-Adresse bei jeder Kontoart', () => {
      expect(abschnitt('Was du angeben musst und was freiwillig ist')).toContain(
        'Kennung und eine E-Mail-Adresse, bei jeder Kontoart',
      );
    });

    it('Einladung: Kennung und Mail-Adresse beim Anmelden, kein Anzeigename aus der Adresse', () => {
      const text = abschnitt('Konto aus einer Einladung');

      expect(text).toContain('erhält die Plattform vom Anmeldedienst deine Kennung und deine E-Mail-Adresse');
      expect(text).toContain('aus deiner E-Mail-Adresse bilden wir keinen Anzeigenamen');
    });

    it('Einladung: Konto bleibt, bis wir es löschen; nie benutztes 30 Tage nach Ablauf des Links (#538)', () => {
      const text = abschnitt('Konto aus einer Einladung');

      expect(text).toContain('Das Konto im Anmeldedienst bleibt, bis wir es löschen');
      expect(text).toContain('dessen Link nie benutzt wurde');
      // NIE_BENUTZTES_KONTO_TAGE und MAIL_GUELTIG_SEKUNDEN im Semantic-Service
      expect(text).toContain('Wir löschen es automatisch 30 Tage nach Ablauf des Links, also etwa 33 Tage nach dem Einlösen');
      expect(text).not.toContain('bis du oder wir es löschen');
      expect(text).not.toContain('Es bleibt ohne Passwort stehen');
    });

    it('Netzbegrünung: Dauer für das vorab angelegte Konto, Angaben vom Anmeldedienst', () => {
      const text = abschnitt('Anmeldung über die Netzbegrünung');

      expect(text).toContain('Das Konto bleibt danach wie jedes andere, bis wir es löschen');
      expect(text).toContain('erhält diese Plattform vom Anmeldedienst');
      expect(text).toContain('Das gilt für alle Anmeldewege');
    });

    it('Anmelde-Cookie: alle drei Kontoarten', () => {
      expect(abschnitt('Anmelde-Cookie')).toContain('mit einem Konto aus einer Einladung und mit einem Zugang');
    });
  });

  describe('Suchvorgänge (#239, #289, #495)', () => {
    it('nennt den Tag statt eines Zeitpunkts und das Ende des Tages als Frist mit Tageszähler', () => {
      const text = abschnitt('Suchvorgänge');

      expect(text).toContain('den Tag (keine Uhrzeit)');
      expect(text).toContain('dieses nur bis zum Ende des Tages');
      expect(text).toContain('automatisch nach Ablauf ihres Tages');
      expect(text).not.toContain('nach 90 Tagen');
      expect(text).toContain(
        'je Tag nur, wie oft gesucht wurde, wie oft davon ohne Treffer und von wie vielen verschiedenen Pseudonymen',
      );
      expect(text).not.toContain('keine Löschfrist');
    });
  });

  describe('Tagespseudonym statt Kennung im Browser (#446)', () => {
    it('Suchvorgänge: Besucher über die IP-Adresse allein und einen täglich neuen, nicht gespeicherten Schlüssel', () => {
      const text = abschnitt('Suchvorgänge');

      expect(text).toContain('nichts in deinem Browser ab');
      expect(text).toContain('nur aus dem heutigen Datum und deiner IP-Adresse');
      // #495: kein User-Agent mehr im Pseudonym.
      expect(text).toContain('Die Bezeichnung deines Browsers (User-Agent) und andere Merkmale deines Geräts gehen nicht ein.');
      expect(text).toContain('hat deshalb an einem Tag dasselbe Pseudonym');
      expect(text).toContain('jeden Tag neu zufällig erzeugt, nur im Arbeitsspeicher hält und nirgends speichert');
      expect(text).toContain('Die IP-Adresse wird dabei weder gespeichert noch protokolliert');
      expect(text).not.toContain('Sitzungskennung');
      // Der Schlüssel wechselt mit der ersten Suche des neuen Tages, nicht um Mitternacht.
      expect(text).toContain('Mit der ersten Suche eines neuen Tages ersetzt er ihn');
      expect(text).not.toContain('mit dem Tag ist auch der Schlüssel weg');
      // "Kennung" ist im Glossar die Kontokennung, nicht der User-Agent.
      expect(text).not.toContain('Kennung deines Browsers');
      expect(text).toContain('siehe „Protokolldateien“');
    });

    it('Suchen ohne Treffer: Netzwechsel zählt neu, je Anschluss höchstens eine Person, auch mit anderem Browser', () => {
      const text = abschnitt('Suchen ohne Treffer');

      expect(text).toContain('anderes Netz');
      // #495: das Pseudonym selbst steht für den Anschluss; ein anderer Browser zählt nicht neu.
      expect(text).toContain('nur aus deinem Anschluss entsteht');
      expect(text).toContain('je Anschluss höchstens eine Person');
      expect(text).not.toContain('Zusätzlich merken wir uns');
      expect(text).toContain('Summe der Personen der einzelnen Tage');
      expect(text).toContain('als eine, auch mit verschiedenen Browsern');
      expect(text).not.toContain('anderen Browser</strong>');
      expect(text).not.toContain('anderen Browser oder');
      expect(text).not.toContain('neue Sitzungskennung');
    });

    it('Verwendung von Beiträgen: kein Pseudonym und kein Kontobezug', () => {
      const text = abschnitt('Verwendung von Beiträgen');

      expect(text).toContain('nicht ablesen, welches Konto einen Beitrag verwendet hat');
      expect(text).not.toContain('höchstens 30 Tage');
      // #495: der Prüfwert ohne Anmeldung nur aus dem Anschluss.
      expect(text).toContain('(ohne Anmeldung: vom selben Anschluss)');
      expect(text).not.toContain('mit demselben Browser');
      expect(text).not.toContain('und der Bezeichnung deines');
    });

    it('Meldungen: ohne Konto das Tagespseudonym, nur bis zum Abschluss', () => {
      const text = abschnitt('Meldungen von Beiträgen');

      expect(text).toContain('tritt an ihre Stelle dein Tagespseudonym');
      expect(text).toContain('Es bleibt nur, solange die Meldung offen ist');
      expect(text).toContain('mit dem Abschluss der Bearbeitung löschen wir es');
      expect(text).not.toContain('stehen also beide nebeneinander');
    });

    it('Speicherung auf deinem Gerät: keine Kennung zum Wiedererkennen, alte wird entfernt', () => {
      const text = abschnitt('Keine Kennung zum Wiedererkennen');

      expect(text).toContain('keine Kennung in deinem Browser ab');
      expect(text).toContain('aus deinem Browser entfernt');
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
    it('nennt die Liste gelöschter Konten für Netzbegrünung-Login und Konto aus einer Einladung, von Hand gepflegt', () => {
      const text = abschnitt('Deine Rechte');

      expect(text).toContain('Hast du dich über die Netzbegrünung oder mit einem Konto aus einer Einladung angemeldet');
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
    it('nennt Art. 9 und keine Auswertung nach politischer Haltung', () => {
      const text = abschnitt('Rückschlüsse auf deine politische Haltung');

      expect(text).toContain('Artikel 9 DSGVO');
      expect(text).toContain('Wir werten deine Mitwirkung nicht danach aus, welche politische Haltung du hast');
    });

    it('Art.-9-Einwilligung: Rechtsgrundlage lit. a, Zeitpunkt und Kennung des Wortlauts (#557)', () => {
      const text = abschnitt('Rückschlüsse auf deine politische Haltung');

      expect(text).toContain('Artikel 9 Absatz 2 Buchstabe a DSGVO');
      expect(text).toContain('eigenes Häkchen, getrennt von den Nutzungsbedingungen und nicht vorbelegt');
      expect(text).toContain('den Zeitpunkt und die Kennung des Wortlauts');
      expect(text).toContain('sein Stand-Datum, bei einem zweiten Wortlaut vom selben Tag mit einem Buchstaben dahinter');
      expect(text).toContain('Ohne Einwilligung kannst du suchen und lesen, aber nichts beitragen und nichts bewerten');
    });

    it('Art.-9-Einwilligung: Widerruf im Profilmenü, Folgen und Dauer bis zur Kontolöschung (#557)', () => {
      const text = abschnitt('Rückschlüsse auf deine politische Haltung');

      expect(text).toContain('Widerrufen kannst du jederzeit im Profilmenü unter „Datenschutz-Einstellungen“');
      expect(text).toContain('Was du schon gespeichert hast, bleibt, bis du es löschst oder dein Konto löschen lässt');
      expect(text).toContain('was bis zum Widerruf geschehen ist, bleibt rechtmäßig');
      expect(text).toContain('Deine Einwilligungen, auch widerrufene, bleiben bis zur Löschung deines Kontos');
      expect(abschnitt('Deine Rechte')).toContain('deine Einwilligungen samt Widerrufen und die Muster-Hinweise, die dein Konto nennen');
    });
  });

  describe('Weitere Korrekturen am Ist-Stand', () => {
    it('Verwendung: nicht gespeichert wird der User-Agent', () => {
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

    it('Gerätespeicher: Willkommen und Rundgang „Mitmachen“ als zwei Vermerke ohne Übertragung (#516)', () => {
      const text = abschnitt('Weitere Einträge');

      expect(text).toContain('Willkommen beim ersten Besuch');
      expect(text).toContain('Rundgangs „Mitmachen“');
      expect(text).toContain('zwei Vermerke ohne Angaben über dich');
      expect(text).toContain('bis du die Websitedaten dieser Seite löschst');
      expect(text).toContain('Sie gehen nicht an uns und werden nicht gezählt.');
    });

    it('Anmelde-Cookie: Angaben des Dienstes nur bei der Anmeldung über Anmeldedienst oder Netzbegrünung', () => {
      expect(abschnitt('Anmelde-Cookie')).toContain(
        'bei der Anmeldung über den Anmeldedienst oder die Netzbegrünung dazu die übrigen Angaben, die der Dienst übermittelt',
      );
    });

    it('kein KI-Vorschlag für Bildunterschriften mehr, also auch kein Anbieter in den USA (#393)', () => {
      const text = abschnitt('Keine Übermittlung außerhalb der EU');

      expect(text).toContain('Wir setzen keinen Sprach- oder Bilderkennungsdienst eines Anbieters außerhalb der EU ein.');
      expect(text).not.toContain('Vorschlag für die Unterschrift');
      expect(text).not.toContain('KI-Anbieter');
    });
  });

  describe('Meldungen nach Art. 16 DSA (#438)', () => {
    it('nennt Name, E-Mail-Adresse und Erklärung guten Glaubens und wofür die Adresse dient', () => {
      const text = abschnitt('Meldungen von Beiträgen');

      expect(text).toContain('deine Erklärung, in gutem Glauben zu melden');
      expect(text).toContain('dein Name und deine E-Mail-Adresse, falls du sie angibst');
      expect(text).toContain('Name und E-Mail-Adresse sind freiwillig');
      expect(text).toContain('teilen wir dir unsere Entscheidung über die Meldung mit');
      expect(text).toContain('Artikel 16 Absatz 5 DSA');
      // #493: die Adresse dient auch der Eingangsbestätigung per Mail (Art. 16 Abs. 4 DSA).
      expect(text).toContain('Gleich nach der Meldung bestätigen wir dir den Eingang');
      expect(text).toContain('Artikel 16 Absatz 4 DSA');
      expect(text).not.toContain('nur, um dir unsere Entscheidung');
      // Der Satz zu Name und E-Mail-Adresse steht hinter dem zu den Kennungen, damit
      // sich „beide“ nicht auf sie beziehen lässt.
      expect(text).not.toContain('stehen also beide nebeneinander');
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

    it('nennt den Klick auch beim Abruf außerhalb der EU', () => {
      expect(abschnitt('Keine Übermittlung außerhalb der EU')).toContain('erst nach deinem Klick auf „Bild laden“');
    });
  });
});
