import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Clipboard } from '@angular/cdk/clipboard';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { PlatzhalterDialogComponent } from './platzhalter-dialog.component';

describe('PlatzhalterDialogComponent (Persona-Test Dennis)', () => {
  const EIN = 'Vögel und Klima. [Hier ein eigenes Erlebnis: Windpark in deiner Gegend] Deshalb ja.';

  let fixture: ComponentFixture<PlatzhalterDialogComponent>;
  let clipboard: jasmine.SpyObj<Clipboard>;
  let dialogRef: jasmine.SpyObj<MatDialogRef<PlatzhalterDialogComponent>>;

  function oeffnen(text: string): void {
    clipboard = jasmine.createSpyObj('Clipboard', ['copy']);
    clipboard.copy.and.returnValue(true);
    dialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);
    TestBed.configureTestingModule({
      imports: [PlatzhalterDialogComponent],
      providers: [
        provideNoopAnimations(),
        { provide: MAT_DIALOG_DATA, useValue: { text } },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: Clipboard, useValue: clipboard },
      ],
    });
    fixture = TestBed.createComponent(PlatzhalterDialogComponent);
    fixture.detectChanges();
  }

  function seite(): HTMLElement {
    return fixture.nativeElement;
  }

  function knopf(klasse: string): HTMLButtonElement {
    return seite().querySelector(`button.${klasse}`) as HTMLButtonElement;
  }

  function tippen(index: number, wert: string): void {
    const feld = seite().querySelectorAll<HTMLTextAreaElement>('.platzhalter-eingabe')[index];
    feld.value = wert;
    feld.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  it('zeigt je Platzhalter ein leeres Feld mit dem Hinweis aus der Klammer', () => {
    oeffnen(EIN);

    expect(seite().querySelector('h2')!.textContent!.trim()).toBe('Fülle den Platzhalter aus');
    expect(seite().querySelectorAll('.platzhalter-eingabe').length).toBe(1);
    expect(seite().querySelector<HTMLTextAreaElement>('.platzhalter-eingabe')!.value).toBe('');
    expect(seite().querySelector('.platzhalter-hinweis')!.textContent!.trim()).toBe(
      'Hier ein eigenes Erlebnis: Windpark in deiner Gegend',
    );
    expect(seite().querySelector('.platzhalter-eingabe')!.getAttribute('aria-describedby')).toBe('platzhalter-hinweis-0');
  });

  it('kopiert erst, wenn der Platzhalter gefüllt ist; Leerzeichen zählen nicht', () => {
    oeffnen(EIN);
    expect(knopf('mit-satz').disabled).toBeTrue();

    tippen(0, '   ');
    expect(knopf('mit-satz').disabled).toBeTrue();

    tippen(0, 'Bei uns stehen drei Windräder.');
    expect(knopf('mit-satz').disabled).toBeFalse();
    knopf('mit-satz').click();

    const erwartet = 'Vögel und Klima. Bei uns stehen drei Windräder. Deshalb ja.';
    expect(clipboard.copy).toHaveBeenCalledOnceWith(erwartet);
    expect(dialogRef.close).toHaveBeenCalledOnceWith({ text: erwartet });
  });

  it('kopiert auf Wunsch ohne Platzhalter, die Klammer-Stelle sauber entfernt', () => {
    oeffnen(EIN);

    knopf('ohne-platzhalter').click();

    expect(clipboard.copy).toHaveBeenCalledOnceWith('Vögel und Klima. Deshalb ja.');
    expect(dialogRef.close).toHaveBeenCalledOnceWith({ text: 'Vögel und Klima. Deshalb ja.' });
  });

  it('kopiert beim Abbrechen nichts', () => {
    oeffnen(EIN);

    expect(knopf('abbrechen').textContent!.trim()).toBe('Abbrechen');
    expect(knopf('abbrechen').hasAttribute('mat-dialog-close')).toBeTrue();
    expect(clipboard.copy).not.toHaveBeenCalled();
  });

  it('verlangt bei mehreren Platzhaltern alle und nummeriert die Felder', () => {
    oeffnen('A [Hier x] B [Hier y] C');

    expect(seite().querySelector('h2')!.textContent!.trim()).toBe('Fülle die Platzhalter aus');
    const beschriftungen = Array.from(seite().querySelectorAll('mat-label')).map((l) => l.textContent!.trim());
    expect(beschriftungen).toEqual(['Dein Satz 1', 'Dein Satz 2']);

    tippen(0, 'eins');
    expect(knopf('mit-satz').disabled).toBeTrue();
    tippen(1, 'zwei');
    knopf('mit-satz').click();

    expect(clipboard.copy).toHaveBeenCalledOnceWith('A eins B zwei C');
  });

  it('behält die Herkunft beim Kopieren mit Herkunft', () => {
    oeffnen(`${EIN}\n\nHerkunft: https://example.org/studie`);

    knopf('ohne-platzhalter').click();

    expect(clipboard.copy).toHaveBeenCalledOnceWith('Vögel und Klima. Deshalb ja.\n\nHerkunft: https://example.org/studie');
  });
});
