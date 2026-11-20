import { TestBed } from '@angular/core/testing';
import { MAT_SNACK_BAR_DATA, MatSnackBarRef } from '@angular/material/snack-bar';

import { IconSnackbarComponent } from './icon-snackbar.component';

describe('IconSnackbarComponent', () => {
  let ref: jasmine.SpyObj<MatSnackBarRef<IconSnackbarComponent>>;

  function erzeugen(): HTMLElement {
    ref = jasmine.createSpyObj('MatSnackBarRef', ['dismissWithAction']);
    TestBed.configureTestingModule({
      imports: [IconSnackbarComponent],
      providers: [
        { provide: MAT_SNACK_BAR_DATA, useValue: { icon: '🌱', text: 'Danke! Du bist unter den Ersten.', aktion: 'Schließen' } },
        { provide: MatSnackBarRef, useValue: ref },
      ],
    });
    const fixture = TestBed.createComponent(IconSnackbarComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('versteckt das Symbol vor Screenreadern und zeigt den Text', () => {
    const element = erzeugen();
    const icon = element.querySelector('.icon-snackbar-icon') as HTMLElement;

    expect(icon.textContent?.trim()).toBe('🌱');
    expect(icon.getAttribute('aria-hidden')).toBe('true');
    expect(element.textContent).toContain('Danke! Du bist unter den Ersten.');
  });

  it('schließt mit dem Knopf über die Aktion', () => {
    const element = erzeugen();
    const knopf = element.querySelector('button') as HTMLButtonElement;

    expect(knopf.textContent?.trim()).toBe('Schließen');
    knopf.click();
    expect(ref.dismissWithAction).toHaveBeenCalled();
  });
});
