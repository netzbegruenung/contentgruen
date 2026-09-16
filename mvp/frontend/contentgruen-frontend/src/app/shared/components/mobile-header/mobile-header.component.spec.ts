import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { MobileHeaderComponent } from './mobile-header.component';
import { NavigationService } from '../../../services/navigation.service';
import { routes } from '../../../app.routes';
import { LeerComponent, ohneWaechter } from '../../../testing/routen-ohne-waechter';

describe('MobileHeaderComponent', () => {
  let fixture: ComponentFixture<MobileHeaderComponent>;
  let router: Router;
  let navigation: jasmine.SpyObj<NavigationService>;

  beforeEach(async () => {
    navigation = jasmine.createSpyObj('NavigationService', ['goBack']);

    await TestBed.configureTestingModule({
      imports: [MobileHeaderComponent],
      providers: [
        provideRouter([
          { path: 'search', component: LeerComponent },
          { path: 'fangkorb', component: LeerComponent },
          { path: 'workflow/add-commentary', component: LeerComponent },
        ]),
        { provide: NavigationService, useValue: navigation },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(MobileHeaderComponent);
    fixture.detectChanges();
  });

  function oeffnen(adresse: string): void {
    router.navigateByUrl(adresse);
    tick();
    fixture.detectChanges();
  }

  function titel(): HTMLElement {
    return fixture.nativeElement.querySelector('.mobile-header-title');
  }

  /**
   * Mobil steht im Kopf der Name der aktuellen Seite, nicht die Marke - deshalb
   * ist er kein Link. Zur Startseite fuehrt hier der erste Menueeintrag; den
   * Titel-Link gibt es nur im Desktop-Kopf, wo "Gut gesagt" steht.
   */
  it('laesst den Titel reinen Text, auch abseits der Startseite', fakeAsync(() => {
    oeffnen('/fangkorb');

    expect(titel().querySelector('a')).toBeNull();
    expect(titel().textContent!.trim()).toBe('Fangkorb');
  }));

  it('nennt auf einer Formularseite nur den Typ', fakeAsync(() => {
    oeffnen('/workflow/add-commentary');

    expect(titel().textContent!.trim()).toBe('Kommentar');
  }));

  it('zeigt auf der Startseite den Namen der App', fakeAsync(() => {
    oeffnen('/search');

    expect(titel().querySelector('a')).toBeNull();
    expect(titel().textContent!.trim()).toBe('Gut gesagt');
  }));

  it('gibt den Pfeil an den NavigationService weiter', fakeAsync(() => {
    oeffnen('/fangkorb');

    fixture.nativeElement.querySelector('button.back-button').click();

    expect(navigation.goBack).toHaveBeenCalledTimes(1);
  }));
});

/**
 * Derselbe Klick, aber gegen die echte Routentabelle und den echten Dienst: Nicht
 * nur "der Pfeil meldet sich", sondern "der Pfeil landet dort, wo er soll".
 * Geprueft wird damit die Kette Kopf -> NavigationService -> data.parent.
 */
describe('MobileHeaderComponent – Pfeil an der echten Routentabelle', () => {
  let fixture: ComponentFixture<MobileHeaderComponent>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MobileHeaderComponent],
      providers: [provideRouter(ohneWaechter(routes))],
    }).compileComponents();

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(MobileHeaderComponent);
    fixture.detectChanges();
  });

  /** Den Pfeil im Kopf klicken und zurueckgeben, wo man landet. */
  function pfeilKlicken(): string {
    const pfeil: HTMLButtonElement = fixture.nativeElement.querySelector('button.back-button');
    expect(pfeil).withContext(`kein Pfeil im Kopf auf ${router.url}`).toBeTruthy();
    pfeil.click();
    tick();
    fixture.detectChanges();

    return router.url;
  }

  /** Adresse oeffnen, dann den Pfeil klicken. */
  function pfeilVon(adresse: string): string {
    router.navigateByUrl(adresse);
    tick();
    fixture.detectChanges();

    return pfeilKlicken();
  }

  it('fuehrt aus dem Beitragsformular auf die Beitragen-Seite', fakeAsync(() => {
    expect(pfeilVon('/workflow/add-commentary')).toBe('/contribute');
  }));

  it('fuehrt aus dem Formular im Destillier-Ablauf zurueck zum Einwurf', fakeAsync(() => {
    expect(pfeilVon('/workflow/add-commentary?rohinput=e-9')).toBe('/destillieren/e-9');
  }));

  it('fuehrt aus dem Einwerfen in den Fangkorb und aus der Destille ebenso', fakeAsync(() => {
    expect(pfeilVon('/einwerfen')).toBe('/fangkorb');
    expect(pfeilVon('/destillieren/e-1')).toBe('/fangkorb');
  }));

  it('fuehrt aus den Rechtstexten auf die Startseite', fakeAsync(() => {
    expect(pfeilVon('/impressum')).toBe('/search');
  }));

  it('fuehrt aus dem Formular mit Aussage auf die Beitragen-Seite', fakeAsync(() => {
    expect(pfeilVon('/workflow/add-commentary?aussage=a-1')).toBe('/contribute');
  }));
});

/**
 * Die schliesst-Mechanik hat nach dem Umzug der Formulare keinen Nutzer in der
 * Routentabelle mehr. Sie bleibt, deshalb wird sie hier an einer Testroute geprueft.
 */
describe('MobileHeaderComponent – Unter-Screen per data.schliesst', () => {
  let fixture: ComponentFixture<MobileHeaderComponent>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MobileHeaderComponent],
      providers: [
        provideRouter([
          { path: 'search', component: LeerComponent },
          {
            path: 'mit-unterscreen',
            component: LeerComponent,
            data: { parent: '/search', schliesst: ['blatt'] },
          },
        ]),
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(MobileHeaderComponent);
    fixture.detectChanges();
  });

  function pfeilKlicken(): string {
    fixture.nativeElement.querySelector('button.back-button').click();
    tick();
    fixture.detectChanges();
    return router.url;
  }

  it('schliesst erst den Unter-Screen und geht erst dann eine Ebene hoch', fakeAsync(() => {
    router.navigateByUrl('/mit-unterscreen?blatt=1&suche=x');
    tick();
    fixture.detectChanges();

    expect(pfeilKlicken()).toBe('/mit-unterscreen?suche=x');
    expect(pfeilKlicken()).toBe('/search');
  }));
});
