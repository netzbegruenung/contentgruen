import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { CONSENT_HINWEIS, CONSENT_HINWEIS_SATZ } from '../shared/consent-hinweis';
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

  it('nennt in Abschnitt 1 den KI-Vorschlag auf Klick statt einer automatischen Bildbeschreibung (#281)', () => {
    const text = abschnittNummer('1.');

    expect(text).toContain('auf Klick einen Vorschlag für die Unterschrift');
    expect(text).not.toContain('automatisiert beschreibt');
  });

  it('nennt in Abschnitt 2 Einwerfen, Einstellen von Beiträgen und Bewerten statt Kommentieren', () => {
    expect(abschnittNummer('2.')).toContain(
      'Zum Einwerfen, Einstellen von Beiträgen und Bewerten meldest du dich an',
    );
  });

  it('sagt nirgends „unwiderruflich“, weder im Text noch im CC0-Hinweis (Entscheidung 29.10.2026)', () => {
    expect(normalisiert(seite.textContent)).not.toContain('unwiderruflich');
    expect(CONSENT_HINWEIS.vorLink).not.toContain('unwiderruflich');
    expect(CONSENT_HINWEIS_SATZ.vorLink).not.toContain('unwiderruflich');
    expect(abschnittNummer('4.')).toContain('Was andere einmal übernommen haben');
  });

  it('sagt in Abschnitt 4, womit die CC0-Freigabe erklärt wird, auch beim Satz (#431)', () => {
    const text = abschnittNummer('4.');

    expect(text).toContain('Das erklärst du mit dem Absenden');
    expect(text).toContain('beim Satz, den du beim Destillieren festhältst, schon mit dem Speichern beim Tippen');
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
