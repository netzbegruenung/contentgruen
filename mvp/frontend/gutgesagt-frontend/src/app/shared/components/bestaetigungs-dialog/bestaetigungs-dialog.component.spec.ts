import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { BestaetigungsDialogComponent, BestaetigungsDialogDaten } from './bestaetigungs-dialog.component';
import { entfernenFrage } from '../../aussagekarte/aussage-entfernen';

describe('BestaetigungsDialogComponent', () => {
  function erstellen(daten: BestaetigungsDialogDaten): HTMLButtonElement {
    TestBed.configureTestingModule({
      imports: [BestaetigungsDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: daten },
        { provide: MatDialogRef, useValue: jasmine.createSpyObj('MatDialogRef', ['close']) },
      ],
    });
    const fixture = TestBed.createComponent(BestaetigungsDialogComponent);
    fixture.detectChanges();
    return fixture.nativeElement.querySelector('button.bestaetigen');
  }

  it('zeigt "ja" sonst als vollen Knopf in der Markenfarbe', () => {
    const ja = erstellen({ titel: 'T', text: 'X', ja: 'Ja', nein: 'Nein' });
    expect(ja.classList).not.toContain('mat-warn');
    expect(ja.classList).not.toContain('bestaetigen--warnung');
  });

  it('zeigt "Endgültig entfernen" einer Aussage im Warnstil', () => {
    const ja = erstellen(entfernenFrage('Windräder töten die Vögel'));
    expect(ja.textContent?.trim()).toBe('Endgültig entfernen');
    expect(ja.classList).toContain('mat-warn');
    expect(ja.classList).toContain('bestaetigen--warnung');
  });
});
