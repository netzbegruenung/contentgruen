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
    expect(seite.querySelector('.hero-section img')!.getAttribute('src')).toBe('marke/logo-v2.svg');
  });

  it('richtet die Antworten an die Mitlesenden', () => {
    const abschnitt = seite.querySelector('.mitlesende')!;

    expect(abschnitt.querySelector('h2')!.textContent).toContain('Für die Mitlesenden');
    expect(abschnitt.textContent).toContain('Unentschiedenen');
  });

  // Designrunde 17.11.: Über sagt warum und wer, die Hilfe wie; Doppeltes steht nur an einer Stelle
  describe('getrennt von der Hilfe', () => {
    it('sagt im Zweck, wofür es Gut gesagt gibt, und verweist für die Bedienung auf die Hilfe', () => {
      const zweck = seite.querySelector('.zweck')!;

      expect(einzeilig(zweck)).toContain('findest du schnell eine passende Antwort');
      expect(einzeilig(zweck)).not.toContain('ganzen Satz');
      const soGehts = zweck.querySelector('.so-gehts-link') as HTMLButtonElement;
      expect(soGehts.textContent!.trim()).toBe("So geht’s");
      soGehts.click();
      expect(TestBed.inject(MatDialog).open).toHaveBeenCalled();
    });

    it('erklärt die Kette nicht selbst und lässt „Nicht jede Aussage“ der Hilfe', () => {
      expect(seite.querySelector('.kette')).toBeNull();
      expect(seite.querySelector('.nicht-jede-aussage')).toBeNull();
      expect(einzeilig(seite)).not.toContain('Nicht jede Aussage braucht eine Antwort');
    });

    it('nennt die Sätze zu KI nur einmal, unter der Technik', () => {
      const text = einzeilig(seite);

      expect(text.split(KEINE_GENERATIVE_KI).length - 1).toBe(1);
      expect(text.split(SUCHE_MIT_SPRACHMODELLEN).length - 1).toBe(1);
    });
  });

  it('erklärt unter „Wie Qualität entsteht“, dass viele schreiben und jeder Schritt von anderen kommen kann', () => {
    const abschnitt = seite.querySelector('.qualitaet')!;

    expect(abschnitt.querySelector('h2')!.textContent).toContain('Wie Qualität entsteht');
    expect(einzeilig(abschnitt)).toContain('Die Antworten schreiben viele Menschen gemeinsam');
    expect(einzeilig(abschnitt)).toContain('Jeden Schritt kann eine andere Person machen');
    expect(einzeilig(abschnitt)).toContain('Mitwirken können heute Mitglieder der');
    // Der Anker #siegel ist von der Karte verlinkt (beitragskarte.siegel.spec.ts)
    expect(abschnitt.querySelector('#siegel')).not.toBeNull();
  });

  it('zählt als Nutzung nur das Kopieren fremder Beiträge, Teilen gibt es noch nicht', () => {
    const text = einzeilig(seite.querySelector('.qualitaet')!);

    expect(text).toContain('Kopiert jemand einen fremden Beitrag, zählt das als Nutzung');
    expect(text).not.toContain('Teilen');
  });

  it('sagt, dass Menschen den Startbestand schreiben und jeder Beitrag bei 0 beginnt', () => {
    const text = einzeilig(seite.querySelector('.startbestand')!);

    expect(text).toContain('Gründungsteam');
    expect(text).not.toContain('Startkont');
    expect(text).toContain('Jeder Beitrag beginnt bei 0 Stimmen und 0 Nutzungen');
  });

  // Persona-Test Gerd: „KI schlägt höchstens etwas vor“ las er als Hintertür
  it('sagt zu KI dasselbe wie die Hilfe und nennt die Modelle unter #technik', () => {
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
    // Die Hilfe verlinkt „Mehr zur Technik“ hierher
    expect(seite.querySelector('#technik')!.contains(seite.querySelector('.technik-ki'))).toBeTrue();
  });

  it('erklärt unter der Technik, wie die Suche Treffer findet (vorher in der Hilfe)', () => {
    const suche = einzeilig(seite.querySelector('#technik .technik-suche')!);

    expect(suche).toContain('Dieselbe Aussage in anderen Worten führt zu denselben Antworten');
    expect(suche).toContain('Je mehr Mitwirkende beitragen und bewerten, desto besser werden die Treffer');
  });

  it('nennt CC0 und verlinkt die Nutzungsbedingungen', () => {
    const abschnitt = seite.querySelector('.cc0')!;

    expect(abschnitt.textContent).toContain('Die Texte der Beiträge stehen unter CC0');
    expect(abschnitt.querySelector('a')!.getAttribute('href')).toBe('/nutzungsbedingungen');
  });

  it('sagt, dass es keine offizielle Linie gibt', () => {
    const abschnitt = seite.querySelector('.linie')!;

    expect(seite.querySelector('.qualitaet .linie')).toBe(abschnitt);
    expect(abschnitt.querySelector('h3')!.textContent).toContain('Keine offizielle Linie');
    expect(abschnitt.textContent).toContain('nur als Herkunft');
  });

  describe('Die Menschen hinter Gut gesagt', () => {
    let abschnitt: Element;

    beforeEach(() => {
      abschnitt = seite.querySelector('.menschen')!;
    });

    it('stellt Sebastian und Aila je mit Karte vor', () => {
      expect(abschnitt.querySelector('h2')!.textContent).toContain('Die Menschen hinter Gut gesagt');
      const namen = Array.from(abschnitt.querySelectorAll('.personal-intro h3')).map((h) => h.textContent!.trim());
      expect(namen).toEqual(['Sebastian Banach', 'Aila Banach']);
    });

    it('nennt Ailas Rolle und zeigt ihr Foto', () => {
      const karte = abschnitt.querySelector('.person-aila')!;

      expect(karte.querySelector('.role')!.textContent!.trim()).toBe('Konzeption & Kommunikation');
      expect(einzeilig(karte)).toContain('Aila unterstützt Gut gesagt bei Konzeption und Kommunikation.');
      expect(einzeilig(karte)).toContain('Versteht man das sofort?');
      const foto = karte.querySelector('img.profile-image')!;
      expect(foto.getAttribute('src')).toBe('/profilbild-aila.jpg');
      expect(foto.getAttribute('alt')).toBe('Aila Banach');
    });

    it('dankt allen Helfenden ohne weitere Namen', () => {
      const danke = abschnitt.querySelector('.danke')!;

      expect(danke.querySelector('h3')!.textContent!.trim()).toBe('Danke');
      expect(einzeilig(danke)).toContain(
        `Danke an alle aus der ${ORGANISATION.name}, die mit Ideen, Tests und Hinweisen geholfen haben.`,
      );
      expect(einzeilig(danke)).toContain('Auch kleine Beiträge haben Gut gesagt besser gemacht.');
    });
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

  it('bietet unter „Mach mit!“ Kontakt und Hilfe an, die Hilfe öffnet sich', () => {
    const dialog = TestBed.inject(MatDialog);
    const knoepfe = Array.from(seite.querySelectorAll('.cta-buttons > a, .cta-buttons > button')).map((k) =>
      einzeilig(k).replace(/^\s*\S+\s/, '').trim(),
    );

    expect(knoepfe).toEqual(['Kontakt aufnehmen', 'Hilfe']);
    (seite.querySelector('.hilfe-knopf') as HTMLButtonElement).click();

    expect(dialog.open).toHaveBeenCalled();
  });

  it('erklärt unter „Bewerten“ das Siegel mit Beispielen von neu bis Güte 10 (#427)', () => {
    expect(seite.querySelector('.siegel-absatz')!.textContent).toContain('Das Siegel zeigt die Güte eines Beitrags');
    const beispiele = Array.from(seite.querySelectorAll('.siegel-beispiele app-siegel svg')).map((svg) =>
      svg.getAttribute('aria-label'),
    );
    expect(beispiele.length).toBe(12);
    expect(beispiele[0]).toBe('Siegel: neu, noch keine Güte');
    expect(beispiele[10]).toBe('Siegel: Güte 10 von 10');
    // Glanz als Beispiel (#351); eine Krone gibt es am Siegel nicht mehr
    expect(seite.querySelectorAll('.siegel-beispiele .siegel-glanz').length).toBe(1);
    expect(beispiele[11]).toBe('Siegel: Güte 10 von 10, mit Glanz');
    expect(seite.querySelector('.siegel-absatz')!.textContent).not.toContain('Krone');
  });

  // Designrunde 17.11.: alle zwölf Beispiele in einer Reihe, schmal (unter 600 px) zwei Reihen zu je sechs
  it('stellt die Siegelbeispiele in einer Reihe aus zwölf Spalten', () => {
    const reihe = seite.querySelector('.siegel-beispiele') as HTMLElement;
    const stil = getComputedStyle(reihe);
    expect(stil.display).toBe('grid');
    const spalten = stil.gridTemplateColumns.trim().split(/\s+/).length;
    expect(spalten).toBe(window.matchMedia('(max-width: 599px)').matches ? 6 : 12);
  });
});
