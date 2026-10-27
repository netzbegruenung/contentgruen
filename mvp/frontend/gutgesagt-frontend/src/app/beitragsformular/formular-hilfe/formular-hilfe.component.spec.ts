import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FormularHilfeComponent } from './formular-hilfe.component';
import { SCHREIBHILFEN, SCHREIBREGELN, TITEL_BEISPIELE } from '../../shared/schreibregeln';

describe('FormularHilfeComponent', () => {
  let fixture: ComponentFixture<FormularHilfeComponent>;

  async function mitTyp(typ: string): Promise<void> {
    await TestBed.configureTestingModule({ imports: [FormularHilfeComponent] }).compileComponents();
    fixture = TestBed.createComponent(FormularHilfeComponent);
    // 'post' kennt FormularTyp erst mit dem Post-Formular (#297)
    fixture.componentRef.setInput('typ', typ);
    fixture.detectChanges();
  }

  function seite(): HTMLElement {
    return fixture.nativeElement;
  }

  function aufklappen(): void {
    (seite().querySelector('.erklaerung-umschalter') as HTMLButtonElement).click();
    fixture.detectChanges();
  }

  function texte(selektor: string): string[] {
    return Array.from(seite().querySelectorAll(selektor)).map((e) => e.textContent!.replace(/\s+/g, ' ').trim());
  }

  describe('Kommentar', () => {
    beforeEach(() => mitTyp('commentary'));

    it('zeigt die Schreibregeln erst nach dem ?', () => {
      expect(seite().querySelector('.schreibregeln')).toBeNull();

      aufklappen();

      expect(texte('.schreibregeln li').length).toBe(6);
    });

    it('nennt die sechs Schreibregeln in der Reihenfolge der Vision', () => {
      aufklappen();

      const regeln = texte('.schreibregeln li');
      expect(regeln[0]).toContain('Unentschiedenen');
      expect(regeln[1]).toContain('Vorwurf nicht');
      expect(regeln[2]).toContain('gemeinsam');
      expect(regeln[3]).toContain('wofür');
      expect(regeln[4]).toContain('Erfinde nichts');
      expect(regeln[4]).toContain('[Hier ein eigenes Erlebnis: …]');
      expect(regeln[5]).toContain('ohne Belehrung, ohne Häme');
    });

    it('zeigt die Schreibhilfen mit dem Küchenzuruf als Leitfrage für die Kurzfassung', () => {
      aufklappen();

      const hilfen = texte('.schreibhilfen li');
      expect(hilfen.length).toBe(SCHREIBHILFEN.length);
      expect(hilfen.join(' ')).toContain('Was würdest du in einem Satz durch die Küche rufen?');
      expect(hilfen.join(' ')).toContain('Kurzfassung');
      expect(hilfen.join(' ')).toContain('Aufhänger');
      expect(hilfen.join(' ')).toContain('Hauptfigur');
      expect(hilfen.join(' ')).toContain('Alltag');
    });

    it('zeigt gute und schwache Titel, die schwachen mit Grund', () => {
      aufklappen();

      const gut = texte('.titel-gut');
      const schwach = texte('.titel-schwach');
      expect(gut.length).toBe(TITEL_BEISPIELE.gut.length);
      expect(gut[0]).toContain('Wärmepumpe lohnt sich auch im Altbau');
      expect(schwach.length).toBe(TITEL_BEISPIELE.schwach.length);
      expect(schwach.some((t) => t.includes('Lohnt sich die Wärmepumpe im Altbau?') && t.includes('Frage'))).toBeTrue();
      expect(schwach.some((t) => t.includes('Thema'))).toBeTrue();
    });

    it('sagt, dass nicht jede Aussage eine Antwort braucht, und nennt Erfundenes als Meldegrund', () => {
      aufklappen();

      const panel = seite().querySelector('.hilfe-panel')!.textContent!;
      expect(panel).toContain('Nicht jede Aussage braucht eine Antwort');
      expect(panel).toContain('Erfundene Erlebnisse oder Zahlen');
      expect(panel).toContain('„Andere“');
    });

    it('behält die Beschreibung des Typs über den Schreibregeln', () => {
      aufklappen();

      expect(seite().querySelector('.hilfe-panel')!.textContent).toContain('Nimmt die Sorge hinter der Aussage ernst');
    });
  });

  describe('Post', () => {
    // Das Post-Formular bringt #297 mit seiner eigenen Formularhilfe; bis dahin gibt es kein Panel.
    beforeEach(() => mitTyp('post'));

    it('gilt als Typ mit Schreibregeln, aber ohne Titelbeispiele', () => {
      const komponente = fixture.componentInstance;
      expect(komponente.mitSchreibregeln).toBeTrue();
      expect(komponente.mitTitelbeispielen).toBeFalse();
    });
  });

  describe('Hintergrundinfo', () => {
    beforeEach(() => mitTyp('generictext'));

    it('zeigt keine Schreibregeln', () => {
      aufklappen();

      expect(seite().querySelector('.hilfe-panel')).toBeTruthy();
      expect(seite().querySelector('.schreibregeln')).toBeNull();
      expect(seite().querySelector('.titel-beispiele')).toBeNull();
    });
  });

  it('pflegt genau sechs Schreibregeln', () => {
    expect(SCHREIBREGELN.length).toBe(6);
  });
});
