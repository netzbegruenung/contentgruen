import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { CC0_ERKLAERUNG_URL, CONSENT_HINWEIS, CONSENT_HINWEIS_SATZ, hinweisText } from '../shared/consent-hinweis';
import { abschnitt, normalisiert } from '../testing/rechtstext';
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

  /** Der Abschnitt, dessen Ueberschrift mit der Nummer beginnt, etwa „7.“. */
  function abschnittNummer(nummer: string): string {
    return abschnitt(seite, new RegExp(`^${nummer.replace('.', '\\.')} `));
  }

  it('verwendet „Destillat“ nicht, das kein Glossarbegriff ist', () => {
    expect(normalisiert(seite.textContent)).not.toMatch(/Destillat/);
    expect(abschnittNummer('3.')).toContain('Dein Text');
  });

  it('nennt in Abschnitt 1 keinen KI-Vorschlag für die Unterschrift mehr (#393) und keine automatische Bildbeschreibung (#281)', () => {
    const text = abschnittNummer('1.');

    expect(text).toContain('Auch die Unterschrift eines Bildes schreibt ein Mensch.');
    expect(text).not.toContain('Vorschlag für die Unterschrift');
    expect(text).not.toContain('automatisiert beschreibt');
  });

  it('nennt in Abschnitt 2 Einwerfen, Einstellen von Beiträgen und Bewerten statt Kommentieren', () => {
    expect(abschnittNummer('2.')).toContain(
      'Zum Einwerfen, Einstellen von Beiträgen und Bewerten meldest du dich an',
    );
  });

  it('bezieht sich in Abschnitt 2 mit einem eigenen Häkchen bei der ersten Anmeldung ein, nicht durch bloße Nutzung (0.9.8)', () => {
    const text = abschnittNummer('2.');

    expect(text).toContain('Diesen Bedingungen stimmst du bei der ersten Anmeldung zu, mit einem eigenen Häkchen');
    expect(text).toContain('mit dem Absenden gibst du deinen Text nach Abschnitt 4 frei');
    expect(text).toContain('geschieht die Freigabe schon mit dem Speichern beim Tippen');
    expect(text).not.toContain('mit dem Absenden stimmst du ihnen zu');
    expect(normalisiert(seite.textContent)).not.toMatch(/mit der Nutzung|durch die Nutzung/);
  });

  it('verlinkt in Abschnitt 4 dieselbe CC0-Erklärung wie der CC0-Hinweis (#415)', () => {
    expect(seite.querySelector(`a[href="${CC0_ERKLAERUNG_URL}"]`)).toBeTruthy();
  });

  it('verlinkt als CC0-Erklärung den deutschen Rechtstext, nicht die Kurzfassung (Stand 19.11.2026)', () => {
    expect(CC0_ERKLAERUNG_URL).toBe('https://creativecommons.org/publicdomain/zero/1.0/legalcode.de');
  });

  it('sagt nirgends „unwiderruflich“, weder im Text noch im CC0-Hinweis (Entscheidung 29.10.2026)', () => {
    expect(normalisiert(seite.textContent)).not.toContain('unwiderruflich');
    expect(hinweisText(CONSENT_HINWEIS)).not.toContain('unwiderruflich');
    expect(hinweisText(CONSENT_HINWEIS_SATZ)).not.toContain('unwiderruflich');
    expect(abschnittNummer('4.')).toContain('Was andere einmal übernommen haben');
  });

  it('sagt in Abschnitt 4, womit die CC0-Freigabe erklärt wird, auch beim Satz (#431)', () => {
    const text = abschnittNummer('4.');

    expect(text).toContain('Das erklärst du mit dem Absenden');
    expect(text).toContain('beim Satz, den du beim Destillieren festhältst, schon mit dem Speichern beim Tippen');
  });

  it('räumt in Abschnitt 4 ein Nutzungsrecht ein, wo der CC0-Verzicht nicht wirkt (#466)', () => {
    const text = abschnittNummer('4.');

    expect(text).toContain('Soweit der Verzicht nicht wirkt, räumst du mit derselben Erklärung jeder Person');
    expect(text).toContain('zeitlich, räumlich und inhaltlich unbeschränktes Nutzungsrecht');
    // Stand 19.11.2026: "ergänzt" statt "entspricht", denn CC0 Abschnitt 3 ist nicht
    // übertragbar und nicht unterlizenzierbar, das Nutzungsrecht hier schon.
    expect(text).toContain('Das ergänzt die Ersatzlizenz in Abschnitt 3 der CC0-Erklärung');
    expect(text).not.toContain('entspricht der Ersatzlizenz');
  });

  it('räumt das Nutzungsrecht in Abschnitt 4 wie CC0 für bekannte und heute noch unbekannte Nutzungsarten ein (#521, Stand 19.11.2026)', () => {
    const text = abschnittNummer('4.');

    expect(text).toContain('für bekannte und heute noch unbekannte Nutzungsarten');
    expect(text).not.toContain('alle bekannten Nutzungsarten');
  });

  it('nennt in Abschnitt 4 Urheberschaft und Verzicht wie die CC0-Erklärung (Stand 19.11.2026)', () => {
    const text = abschnittNummer('4.');

    expect(text).toContain('Alle dürfen deinen Text kopieren, verändern und veröffentlichen');
    expect(text).toContain('auch ohne deinen Namen zu nennen');
    expect(text).toContain(
      'Du bleibst Urheberin oder Urheber deines Textes, verzichtest jedoch darauf, seine Nutzung urheberrechtlich zu beschränken',
    );
    expect(text).toContain('Eine Pflicht zur Namensnennung für Weiterverwendende entsteht daraus nicht');
    expect(text).not.toContain('Du behältst deine Urheberschaft');
  });

  it('lässt in Abschnitt 5 nur frei zugängliche fremde Bilder einbinden und sperrt andere erst nach Prüfung (#521)', () => {
    const text = abschnittNummer('5.');

    expect(text).toContain('Binde ein fremdes Bild nur ein, wenn es an seinem ursprünglichen Ort frei zugänglich ist');
    expect(text).toContain('ohne Anmeldung, Bezahlschranke oder technischen Schutz');
    // Wie in Abschnitt 7: Eine Meldung allein sperrt nichts, erst die Prüfung.
    expect(text).toContain('sperren wir den Beitrag, sobald wir es geprüft haben');
    expect(text).not.toContain('sobald wir davon erfahren');
  });

  it('lässt geänderte Bedingungen in Abschnitt 10 erst mit Zustimmung gelten (#466)', () => {
    const text = abschnittNummer('10.');

    expect(text).not.toContain('Widersprichst du nicht');
    expect(text).toContain('Geänderte Bedingungen gelten für dich erst, wenn du ihnen zustimmst');
    expect(text).toContain('Bis dahin gilt für dich der Stand, der vorher für dich galt');
    expect(text).toContain('Schweigen oder bloßes Weiternutzen, etwa Lesen, gilt nicht als Zustimmung');
    expect(text).not.toContain('etwa Lesen oder Bewerten');
    expect(text).toContain('Ab diesem Stand bewahren wir jeden Stand dieser Bedingungen');
  });

  it('fragt in Abschnitt 10 mit einem Häkchen neu, wenn sich die Bedingungen ändern (0.9.8)', () => {
    const text = abschnittNummer('10.');

    expect(text).toContain('Bei der ersten Anmeldung stimmst du mit einem Häkchen zu');
    expect(text).toContain(
      'fragen wir dich mit einem Häkchen neu, wenn du Gut gesagt das nächste Mal mit deinem Konto nutzt',
    );
    expect(text).toContain('Willst du nicht zustimmen, kannst du mit deinem Konto nichts mehr einstellen und nichts bewerten');
    // Die Zustimmung kommt nicht mehr über das Absenden und nicht über die Keycloak-Pflichtaktion.
    expect(text).not.toContain('wenn du das nächste Mal etwas einstellst');
    expect(text).not.toContain('Fragen wir dich schon vorher, etwa bei der Anmeldung');
    expect(text).not.toContain('kommst du ohne Zustimmung nicht mehr hinein');
    expect(text).not.toContain('melden wir beim Wechsel alle ab');
  });

  it('nimmt in Abschnitt 10 reine Korrekturen von der Zustimmung aus (#466)', () => {
    const text = abschnittNummer('10.');

    expect(text).toContain('Reine Korrekturen, die deine Rechte und Pflichten nicht ändern');
    expect(text).toContain('gelten ohne erneute Zustimmung');
  });

  it('beschreibt Sperren als Regelweg der Moderation und behält die Mitteilung an die Person', () => {
    const text = abschnittNummer('7.');

    expect(text).toContain('sperren wir ihn');
    expect(text).toContain('Eine Meldung allein sperrt nichts');
    expect(text).toContain('teilen wir dir die Entscheidung und ihre Gründe mit');
    expect(text).not.toContain('entfernen rechtswidrige Inhalte, sobald wir Kenntnis erlangen');
  });

  it('nennt in Abschnitt 7 Grund, Mitteilung in „Meine Beiträge“ und den Widerspruch dort (#448)', () => {
    const text = abschnittNummer('7.');

    expect(text).toContain('muss einen Grund aus Abschnitt 6 wählen und die Entscheidung begründen');
    expect(text).toContain('den Grund und die Begründung oben in „Meine Beiträge“ mit');
    expect(text).toContain('Gegen die Sperre kannst du dort oder formlos an die genannte Adresse widersprechen');
    expect(text).toContain('prüft sie dann erneut');
    // Ein Ergebnis in der App gibt es nur nach einem Widerspruch in der App.
    expect(text).toContain('wenn du dort widersprochen hast');
    expect(text).toContain('auf einen Widerspruch per E-Mail antworten wir per E-Mail');
  });

  it('nennt in Abschnitt 7 die Angaben einer Meldung nach Art. 16 DSA und die Bestätigung in der App (#438)', () => {
    const text = abschnittNummer('7.');

    expect(text).toContain('in gutem Glauben davon überzeugt bist, dass deine Angaben richtig und vollständig sind');
    expect(text).toContain('Name und E-Mail-Adresse kannst du angeben, musst es aber nicht');
    expect(text).toContain('Den Eingang bestätigen wir dir sofort in der App');
    // Art. 16 Abs. 4 DSA (#493): mit Adresse auch per E-Mail.
    expect(text).toContain('Hast du eine E-Mail-Adresse angegeben, bestätigen wir ihn dir auch per E-Mail');
    expect(text).toContain('teilen wir dir unsere Entscheidung über die Meldung per E-Mail mit');
    // Art. 16 Abs. 5 DSA: mit der Entscheidung die Rechtsbehelfe.
    expect(text).toContain('zusammen mit deinen Möglichkeiten, dagegen vorzugehen');
    // Art. 16 Abs. 2 lit. a DSA: beim Meldegrund „Rechtswidriger Inhalt“ ist die Begründung Pflicht.
    expect(text).toContain('Wählst du „Rechtswidriger Inhalt“, schreibst du dazu, warum der Beitrag rechtswidrig ist');
    expect(text).toContain('bei den anderen Gründen kannst du beschreiben, was nicht stimmt');
    // Die Meldefunktion ist selbst der Weg nach Art. 16 DSA, nicht nur die Mail.
    expect(text).not.toContain('richtest du bitte per E-Mail an');
  });
});
