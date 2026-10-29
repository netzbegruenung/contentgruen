import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { SperrenDialogComponent, SperrenDialogDaten } from './sperren-dialog.component';

describe('SperrenDialogComponent', () => {
  let schliessen: jasmine.Spy;

  function erzeugen(daten: SperrenDialogDaten) {
    schliessen = jasmine.createSpy('close');
    TestBed.configureTestingModule({
      imports: [SperrenDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: daten },
        { provide: MatDialogRef, useValue: { close: schliessen } },
      ],
    });
    const fixture = TestBed.createComponent(SperrenDialogComponent);
    fixture.detectChanges();
    return fixture;
  }

  function sperrknopf(fixture: any): HTMLButtonElement {
    const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((b) => b.textContent?.includes('Sperre'))!;
  }

  it('lässt ohne Sperrgrund und Begründung nicht sperren', () => {
    const fixture = erzeugen({ art: 'sperren', titel: 'T' });
    const c = fixture.componentInstance;

    expect(sperrknopf(fixture).disabled).toBeTrue();

    c.sperrgrund = 'unterstellung';
    c.begruendung = '   ';
    fixture.detectChanges();
    expect(sperrknopf(fixture).disabled).toBeTrue();

    c.begruendung = 'Unterstellt Bosheit.';
    fixture.detectChanges();
    expect(sperrknopf(fixture).disabled).toBeFalse();
  });

  it('gibt Sperrgrund und Begründung ohne Leerraum zurück', () => {
    const fixture = erzeugen({ art: 'sperren', titel: 'T' });
    const c = fixture.componentInstance;
    c.sperrgrund = 'ohne_bezug';
    c.begruendung = ' Werbung ';

    c.bestaetigen();

    expect(schliessen).toHaveBeenCalledWith({ sperrgrund: 'ohne_bezug', begruendung: 'Werbung' });
  });

  it('verlangt beim Bestätigen nur die Begründung', () => {
    const fixture = erzeugen({ art: 'bestaetigen', titel: 'T' });
    const c = fixture.componentInstance;
    expect(fixture.nativeElement.textContent).not.toContain('Sperrgrund');

    c.begruendung = 'Bleibt.';
    c.bestaetigen();

    expect(schliessen).toHaveBeenCalledWith({ sperrgrund: null, begruendung: 'Bleibt.' });
  });

  it('nennt dem Admin, dass der Autor Grund und Begründung liest', () => {
    const fixture = erzeugen({ art: 'sperren', titel: 'T' });

    expect(fixture.nativeElement.textContent).toContain('Meine Beiträge');
  });
});
