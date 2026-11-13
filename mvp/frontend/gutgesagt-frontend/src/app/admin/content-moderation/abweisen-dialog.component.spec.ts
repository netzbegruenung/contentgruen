import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ANDERER_GRUND, AbweisenDialogComponent, AbweisenDialogDaten } from './abweisen-dialog.component';

describe('AbweisenDialogComponent', () => {
  let schliessen: jasmine.Spy;

  function erzeugen(daten: AbweisenDialogDaten = { titel: 'Titel', meldegrund: 'Unangemessener Inhalt', mitMail: true }) {
    schliessen = jasmine.createSpy('close');
    TestBed.configureTestingModule({
      imports: [AbweisenDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: daten },
        { provide: MatDialogRef, useValue: { close: schliessen } },
      ],
    });
    const fixture = TestBed.createComponent(AbweisenDialogComponent);
    fixture.detectChanges();
    return fixture;
  }

  function abweisknopf(fixture: any): HTMLButtonElement {
    const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((b) => b.textContent?.includes('Meldung abweisen'))!;
  }

  it('lässt ohne Grund nicht abweisen und sagt, was die meldende Person erfährt', () => {
    const fixture = erzeugen();

    expect(abweisknopf(fixture).disabled).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('Gemeldet als: Unangemessener Inhalt');
    expect(fixture.nativeElement.textContent).toContain('per Mail mit einem festen Text');
    expect(fixture.nativeElement.textContent).toContain('nicht rückgängig');
  });

  it('schließt mit dem Grund und dem optionalen Satz als Begründung', () => {
    const fixture = erzeugen();
    const c = fixture.componentInstance;

    c.grund = 'Zulässige Meinungsäußerung';
    fixture.detectChanges();
    abweisknopf(fixture).click();
    expect(schliessen).toHaveBeenCalledWith('Zulässige Meinungsäußerung');

    c.satz = '  Zuspitzung, kein Angriff ';
    abweisknopf(fixture).click();
    expect(schliessen).toHaveBeenCalledWith('Zulässige Meinungsäußerung: Zuspitzung, kein Angriff');
  });

  it('verlangt bei „Anderer Grund“ einen eigenen Satz', () => {
    const fixture = erzeugen();
    const c = fixture.componentInstance;

    c.grund = ANDERER_GRUND;
    fixture.detectChanges();
    expect(abweisknopf(fixture).disabled).toBeTrue();

    c.satz = 'Meldung betrifft einen anderen Beitrag';
    fixture.detectChanges();
    expect(abweisknopf(fixture).disabled).toBeFalse();
  });

  it('begrenzt die ganze Begründung auf 500 Zeichen, sie steht in der Adresse', () => {
    const fixture = erzeugen();
    const c = fixture.componentInstance;
    c.grund = 'Zulässige Meinungsäußerung';
    fixture.detectChanges();

    expect(c.maxLaenge).toBe(500 - 'Zulässige Meinungsäußerung'.length - 2);
    expect(fixture.nativeElement.querySelector('textarea').getAttribute('maxlength')).toBe(String(c.maxLaenge));
  });

  it('sagt ohne Mail-Adresse, dass niemand benachrichtigt wird', () => {
    const fixture = erzeugen({ titel: 'T', meldegrund: 'Spam', mitMail: false });

    expect(fixture.nativeElement.textContent).toContain('keine E-Mail-Adresse angegeben');
  });
});
