import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormControl, FormGroup } from '@angular/forms';
import { Router } from '@angular/router';

import { ENTWURF_PRAEFIX, EinwilligungHinweisComponent } from './einwilligung-hinweis.component';
import { Art9EinwilligungZustand } from '../services/art9-einwilligung-zustand';

/** UX-Review B4: Hinweis mit „Einwilligen“ über dem Formular, die Eingabe übersteht den Umweg. */
describe('EinwilligungHinweisComponent', () => {
  const ADRESSE = '/einwerfen?von=fangkorb';
  let fixture: ComponentFixture<EinwilligungHinweisComponent>;
  let zustand: Art9EinwilligungZustand;
  let router: { url: string; navigate: jasmine.Spy };
  let formular: FormGroup;

  function erstellen(): void {
    fixture = TestBed.createComponent(EinwilligungHinweisComponent);
    fixture.componentInstance.formular = formular;
    fixture.detectChanges();
  }

  function kasten(): HTMLElement | null {
    return (fixture.nativeElement as HTMLElement).querySelector('[data-testid=einwilligung-hinweis]');
  }

  beforeEach(() => {
    sessionStorage.removeItem(ENTWURF_PRAEFIX + ADRESSE);
    router = { url: ADRESSE, navigate: jasmine.createSpy('navigate') };
    TestBed.configureTestingModule({
      imports: [EinwilligungHinweisComponent],
      providers: [{ provide: Router, useValue: router }],
    });
    zustand = TestBed.inject(Art9EinwilligungZustand);
    formular = new FormGroup({ link: new FormControl(''), hinweis: new FormControl('') });
  });

  afterEach(() => sessionStorage.removeItem(ENTWURF_PRAEFIX + ADRESSE));

  it('zeigt nichts, solange die Einwilligung da oder unbekannt ist', () => {
    erstellen();
    expect(kasten()).toBeNull();

    zustand.setzen('eingewilligt');
    fixture.detectChanges();
    expect(kasten()).toBeNull();
  });

  it('zeigt ohne Einwilligung den Hinweis mit „Einwilligen“, auch wenn sie erst ein 403 meldet', () => {
    erstellen();
    zustand.setzen('fehlt');
    fixture.detectChanges();

    expect(kasten()?.textContent).toContain('Zum Beitragen brauchst du deine Einwilligung.');
    expect(kasten()?.querySelector('button')?.textContent?.trim()).toBe('Einwilligen');
  });

  it('meldet sich an, damit der Interceptor keinen zweiten Hinweis zeigt, und beim Zerstoeren wieder ab', () => {
    erstellen();
    expect(zustand.hinweisDa).toBeTrue();

    fixture.destroy();
    expect(zustand.hinweisDa).toBeFalse();
  });

  it('sichert die Eingabe und fuehrt zur Einwilligung mit Rueckweg', () => {
    zustand.setzen('fehlt');
    erstellen();
    formular.setValue({ link: 'https://example.org/a', hinweis: 'Schon getippt' });

    (kasten()!.querySelector('button') as HTMLButtonElement).click();

    expect(JSON.parse(sessionStorage.getItem(ENTWURF_PRAEFIX + ADRESSE)!)).toEqual({
      link: 'https://example.org/a',
      hinweis: 'Schon getippt',
    });
    expect(router.navigate).toHaveBeenCalledWith(['/einwilligung'], { queryParams: { returnUrl: ADRESSE } });
  });

  it('setzt eine gesicherte Eingabe beim Zurueckkommen wieder ein, einmal, und laesst Vorbelegtes bei leeren Feldern', () => {
    sessionStorage.setItem(ENTWURF_PRAEFIX + ADRESSE, JSON.stringify({ link: '', hinweis: 'Schon getippt' }));
    formular.setValue({ link: 'https://vorbelegt.example/', hinweis: '' });

    erstellen();

    expect(formular.value).toEqual({ link: 'https://vorbelegt.example/', hinweis: 'Schon getippt' });
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + ADRESSE)).toBeNull();
  });

  it('setzt auch den Wert eines einzelnen Felds wieder ein (Satz beim Destillieren)', () => {
    const satz = new FormControl('');
    sessionStorage.setItem(ENTWURF_PRAEFIX + ADRESSE, JSON.stringify('Mein Satz'));
    fixture = TestBed.createComponent(EinwilligungHinweisComponent);
    fixture.componentInstance.formular = satz;
    fixture.detectChanges();

    expect(satz.value).toBe('Mein Satz');
  });

  it('fuehrt auch ohne Speicher zur Einwilligung', () => {
    zustand.setzen('fehlt');
    erstellen();
    spyOn(Storage.prototype, 'setItem').and.throwError('gesperrt');

    (kasten()!.querySelector('button') as HTMLButtonElement).click();

    expect(router.navigate).toHaveBeenCalled();
  });
});
