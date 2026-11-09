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
    navigation = jasmine.createSpyObj('NavigationService', ['goBack', 'navigateHome']);

    await TestBed.configureTestingModule({
      imports: [MobileHeaderComponent],
      providers: [
        provideRouter([
          { path: 'search', component: LeerComponent },
          { path: 'fangkorb', component: LeerComponent },
          { path: 'login', component: LeerComponent },
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
   * ist er kein Link. Zur Startseite fuehren das Logo links und der erste
   * Menueeintrag (#620).
   */
  it('laesst den Titel reinen Text, auch abseits der Startseite', fakeAsync(() => {
    oeffnen('/fangkorb');

    expect(titel().querySelector('a')).toBeNull();
    expect(titel().textContent!.trim()).toBe('Fangkorb');
  }));

  it('zeigt ohne Pfeil links das Logo als Link "Startseite", das Bild ohne eigenen Namen (#416, #620)', fakeAsync(() => {
    oeffnen('/search');

    const link: HTMLAnchorElement = fixture.nativeElement.querySelector('.mobile-header-left a.logo-link');
    expect(link.getAttribute('aria-label')).toBe('Startseite');
    expect(link.getAttribute('href')).toBe('/');
    const logo = link.querySelector('img.kopf-logo') as HTMLImageElement;
    expect(logo.getAttribute('src')).toBe('marke/logo.svg');
    expect(logo.getAttribute('alt')).toBe('');
  }));

  it('fuehrt mit dem Logo ueber den NavigationService zur Startseite', fakeAsync(() => {
    oeffnen('/search');
    navigation.navigateHome.and.resolveTo();

    fixture.nativeElement.querySelector('a.logo-link').click();

    expect(navigation.navigateHome).toHaveBeenCalledTimes(1);
  }));

  it('zeigt mit Pfeil kein Logo, der Pfeil steht an seiner Stelle', fakeAsync(() => {
    fixture.componentInstance.showBackButton = true;
    fixture.componentRef.changeDetectorRef.markForCheck();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.kopf-logo')).toBeNull();
    expect(fixture.nativeElement.querySelector('.back-button')).not.toBeNull();
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

  it('zeigt am Beitragen-Knopf einen Neu-Punkt, solange Mitmachen offen ist (#587)', () => {
    const komponente = fixture.componentInstance;
    komponente.userInfo = { isAuthenticated: true, userId: 'u1', userName: 'Kim', claims: null };
    komponente.showContributeButton = true;
    komponente.beitragenNeu = true;
    fixture.detectChanges();
    const knopf: HTMLElement = fixture.nativeElement.querySelector('.contribute-button');
    expect(knopf.querySelector('.neu-punkt')).not.toBeNull();
    expect(knopf.getAttribute('aria-label')).toBe('Beitragen');

    komponente.beitragenNeu = false;
    fixture.detectChanges();
    expect(knopf.querySelector('.neu-punkt')).toBeNull();
    expect(knopf.getAttribute('aria-label')).toBe('Beitragen');
  });

  // R58 (#644): Anonym wirkte der graue Avatar wie ein Konto, "+" fuehrte nur zur Anmeldung
  it('zeigt anonym einen Text-Knopf "Anmelden" statt Avatar und ohne "+"', () => {
    const komponente = fixture.componentInstance;
    komponente.userInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };
    komponente.showContributeButton = true;
    fixture.detectChanges();
    const anmelden = spyOn(komponente.login, 'emit');

    const knopf: HTMLButtonElement = fixture.nativeElement.querySelector('.anmelden-knopf');
    expect(knopf.textContent!.trim()).toBe('Anmelden');
    expect(fixture.nativeElement.querySelector('.mobile-header-avatar-container')).toBeNull();
    expect(fixture.nativeElement.querySelector('.contribute-button')).toBeNull();
    expect(fixture.nativeElement.querySelector('.menu-button')).not.toBeNull();

    knopf.click();
    expect(anmelden).toHaveBeenCalled();
  });

  it('zeigt auf der Anmeldeseite keinen Anmelden-Knopf im Kopf', fakeAsync(() => {
    fixture.componentInstance.userInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };
    oeffnen('/login');
    expect(fixture.nativeElement.querySelector('.anmelden-knopf')).toBeNull();
    expect(fixture.nativeElement.querySelector('.mobile-header-avatar-container')).toBeNull();
  }));

  it('zeigt angemeldet Avatar und "+", keinen Anmelden-Knopf', () => {
    const komponente = fixture.componentInstance;
    komponente.userInfo = { isAuthenticated: true, userId: 'u1', userName: 'Kim', claims: null };
    komponente.showContributeButton = true;
    fixture.detectChanges();
    const menue = spyOn(komponente.openMenu, 'emit');

    expect(fixture.nativeElement.querySelector('.anmelden-knopf')).toBeNull();
    expect(fixture.nativeElement.querySelector('.contribute-button')).not.toBeNull();
    (fixture.nativeElement.querySelector('.mobile-header-avatar-container') as HTMLButtonElement).click();
    expect(menue).toHaveBeenCalled();
  });

  it('gibt den Pfeil an den NavigationService weiter', fakeAsync(() => {
    oeffnen('/fangkorb');

    fixture.nativeElement.querySelector('button.back-button').click();

    expect(navigation.goBack).toHaveBeenCalledTimes(1);
  }));
});

/**
 * Layout bei 360 px: Ein langer Titel darf nichts aus dem Kopf schieben. Frueher
 * war der Titel ein Flex-Element ohne min-width: 0 - seine Mindestbreite war die
 * Textbreite, und Avatar, Ordner und Menue rutschten rechts hinaus.
 */
describe('MobileHeaderComponent: Kopfzeile bei 360 px', () => {
  let fixture: ComponentFixture<MobileHeaderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MobileHeaderComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(MobileHeaderComponent);
    const host: HTMLElement = fixture.nativeElement;
    host.style.display = 'block';
    host.style.width = '360px';
    document.body.appendChild(host);

    // Gemessen wird mit der Hausschrift des Titels. Ohne diese Zeile misst der Test,
    // je nach Reihenfolge der Suite, die breitere Ersatzschrift (#552).
    await document.fonts.load('28px GrueneType');
  });

  afterEach(() => fixture.nativeElement.remove());

  function aufbauen(titel: string): void {
    const komponente = fixture.componentInstance;
    fixture.detectChanges();
    komponente.userInfo = { isAuthenticated: true } as any;
    komponente.pageTitle = titel;
    komponente.showBackButton = true;
    komponente.showContributeButton = true;
    fixture.componentRef.changeDetectorRef.markForCheck();
    fixture.detectChanges();
  }

  function rechteck(selektor: string): DOMRect {
    return (fixture.nativeElement.querySelector(selektor) as HTMLElement).getBoundingClientRect();
  }

  for (const titel of ['Beitrag verfassen', 'Ein sehr langer Seitentitel, der niemals passt']) {
    it(`zeigt Avatar, Beitragen und Menue vollstaendig bei "${titel}"`, () => {
      aufbauen(titel);
      const kopf = rechteck('.mobile-header');

      for (const selektor of ['.mobile-header-avatar-container', '.contribute-button', '.menu-button']) {
        const r = rechteck(selektor);
        expect(r.width).withContext(`${selektor} Breite`).toBeGreaterThan(0);
        expect(r.left).withContext(`${selektor} links`).toBeGreaterThanOrEqual(kopf.left);
        expect(r.right).withContext(`${selektor} rechts`).toBeLessThanOrEqual(kopf.right);
      }
      expect(rechteck('.mobile-header-title').right).toBeLessThanOrEqual(rechteck('.mobile-header-actions').left);
    });
  }

  it('zeigt anonym "Anmelden" und Menue vollstaendig neben einem langen Titel (#644)', () => {
    const komponente = fixture.componentInstance;
    fixture.detectChanges();
    komponente.userInfo = { isAuthenticated: false } as any;
    komponente.pageTitle = 'Hier fehlt eine Antwort';
    komponente.showBackButton = true;
    fixture.componentRef.changeDetectorRef.markForCheck();
    fixture.detectChanges();
    const kopf = rechteck('.mobile-header');

    for (const selektor of ['.anmelden-knopf', '.menu-button']) {
      const r = rechteck(selektor);
      expect(r.width).withContext(`${selektor} Breite`).toBeGreaterThan(0);
      expect(r.right).withContext(`${selektor} rechts`).toBeLessThanOrEqual(kopf.right);
    }
    expect(rechteck('.mobile-header-title').right).toBeLessThanOrEqual(rechteck('.mobile-header-actions').left);
  });

  // A8 aus dem Design-Audit (#512): "Suchergebnisse" und "Hier fehlt eine Antwort"
  // waren abgeschnitten. Lange Titel werden kleiner und duerfen zweizeilig stehen.
  for (const titel of ['Suchergebnisse', 'Hier fehlt eine Antwort', 'Kommentar']) {
    it(`zeigt "${titel}" ganz, ohne Auslassung`, () => {
      aufbauen(titel);
      const text: HTMLElement = fixture.nativeElement.querySelector('.mobile-header-title-text');

      // Toleranz fuer Unterlaengen; eine abgeschnittene dritte Zeile waere > 20 px
      expect(text.scrollWidth).toBeLessThanOrEqual(text.clientWidth);
      expect(text.scrollHeight).toBeLessThanOrEqual(text.clientHeight + 4);
    });
  }

  it('setzt kurze Titel in voller Groesse, lange kleiner', () => {
    aufbauen('Fangkorb');
    const kurz = parseFloat(getComputedStyle(fixture.nativeElement.querySelector('.mobile-header-title-text')).fontSize);
    aufbauen('Hier fehlt eine Antwort');
    const lang = parseFloat(getComputedStyle(fixture.nativeElement.querySelector('.mobile-header-title-text')).fontSize);

    expect(kurz).toBe(28);
    expect(lang).toBe(22);
  });

  it('kuerzt einen Titel, der auch zweizeilig nicht passt, mit Auslassungszeichen', () => {
    aufbauen('Ein sehr langer Seitentitel, der niemals passt, auch nicht in zwei Zeilen');
    const text: HTMLElement = fixture.nativeElement.querySelector('.mobile-header-title-text');
    const stil = getComputedStyle(text);

    expect(text.scrollHeight).toBeGreaterThan(text.clientHeight);
    expect(stil.overflow).toBe('hidden');
    expect(stil.getPropertyValue('-webkit-line-clamp')).toBe('2');
  });
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
    expect(pfeilVon('/workflow/add-commentary?einwurf=e-9')).toBe('/destillieren/e-9');
  }));

  it('fuehrt aus dem Einwerfen auf die Beitragen-Seite, aus dem Fangkorb heraus zurueck', fakeAsync(() => {
    expect(pfeilVon('/einwerfen')).toBe('/contribute');
    expect(pfeilVon('/einwerfen?von=fangkorb')).toBe('/fangkorb');
  }));

  it('fuehrt aus der Destille in den Fangkorb', fakeAsync(() => {
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
