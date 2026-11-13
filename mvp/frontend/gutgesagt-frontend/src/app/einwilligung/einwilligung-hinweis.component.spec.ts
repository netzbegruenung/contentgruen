import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { FormControl, FormGroup } from '@angular/forms';
import { Router } from '@angular/router';

import { ENTWURF_PRAEFIX, EinwilligungHinweisComponent } from './einwilligung-hinweis.component';
import { Art9EinwilligungZustand } from '../services/art9-einwilligung-zustand';
import { ENTWURF_HOECHSTENS_MS } from './entwurf-vor-einwilligung';

function ablegen(werte: unknown, zeit = Date.now()): void {
  sessionStorage.setItem(ENTWURF_PRAEFIX + '/einwerfen?von=fangkorb', JSON.stringify({ zeit, werte }));
}

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

    const abgelegt = JSON.parse(sessionStorage.getItem(ENTWURF_PRAEFIX + ADRESSE)!);
    expect(abgelegt.werte).toEqual({ link: 'https://example.org/a', hinweis: 'Schon getippt' });
    expect(typeof abgelegt.zeit).toBe('number');
    expect(router.navigate).toHaveBeenCalledWith(['/einwilligung'], { queryParams: { returnUrl: ADRESSE } });
  });

  it('setzt eine gesicherte Eingabe beim Zurueckkommen wieder ein, einmal, und laesst Vorbelegtes bei leeren Feldern', () => {
    ablegen({ link: '', hinweis: 'Schon getippt' });
    formular.setValue({ link: 'https://vorbelegt.example/', hinweis: '' });

    erstellen();

    expect(formular.value).toEqual({ link: 'https://vorbelegt.example/', hinweis: 'Schon getippt' });
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + ADRESSE)).toBeNull();
  });

  it('setzt auch den Wert eines einzelnen Felds wieder ein (Satz beim Destillieren)', () => {
    const satz = new FormControl('');
    ablegen('Mein Satz');
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
  // Review zu #670: Entwuerfe von vor der Einwilligung liegen nicht laenger als noetig
  it('verwirft einen Entwurf, der aelter als eine Stunde ist, und einen ohne Zeitpunkt', () => {
    ablegen({ link: '', hinweis: 'Von gestern' }, Date.now() - ENTWURF_HOECHSTENS_MS - 1000);
    erstellen();
    expect(formular.value.hinweis).toBe('');
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + ADRESSE)).toBeNull();

    sessionStorage.setItem(ENTWURF_PRAEFIX + ADRESSE, JSON.stringify({ link: '', hinweis: 'Altes Format' }));
    fixture.destroy();
    erstellen();
    expect(formular.value.hinweis).toBe('');
  });

  // Review zu #670: Absenden mit Kasten soll sichtbar etwas tun
  it('holt sich bei einem weiteren 403 in den Blick und nimmt den Fokus', fakeAsync(() => {
    zustand.setzen('fehlt');
    erstellen();
    const kastenElement = kasten()!;
    const scroll = jasmine.createSpy('scrollIntoView');
    kastenElement.scrollIntoView = scroll;

    zustand.hinweisZeigen();
    tick();

    expect(scroll).toHaveBeenCalled();
    expect(document.activeElement).toBe(kastenElement);
  }));
});
