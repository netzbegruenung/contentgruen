import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { LeerComponent } from '../../../testing/routen-ohne-waechter';
import { of } from 'rxjs';
import { ZuTunService } from '../../../services/zu-tun.service';

import { MobileMenuComponent } from './mobile-menu';

describe('MobileMenuComponent', () => {
  let component: MobileMenuComponent;
  let fixture: ComponentFixture<MobileMenuComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MobileMenuComponent],
      providers: [provideRouter([
        { path: 'fangkorb', component: LeerComponent },
        { path: 'impressum', component: LeerComponent },
      ]),
      {
        provide: ZuTunService,
        useValue: { meldungen$: of({ daten: { anzahl: 2, mehr: false, aelteste: null }, fehler: false }) },
      }]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MobileMenuComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  function link(selektor: string): HTMLAnchorElement {
    return fixture.nativeElement.querySelector(selektor) as HTMLAnchorElement;
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('bietet Feedback auch ohne Anmeldung an und schliesst danach das Menue', () => {
    const feedback = spyOn(component.feedback, 'emit');
    const schliessen = spyOn(component.closeMenu, 'emit');

    const knopf = fixture.nativeElement.querySelector('.mobile-menu-feedback') as HTMLButtonElement;
    expect(knopf.textContent).toContain('Feedback');
    knopf.click();

    expect(feedback).toHaveBeenCalled();
    expect(schliessen).toHaveBeenCalled();
  });

  // Rundgaenge wieder aufrufen (#389)
  describe('Rundgang', () => {
    it('bietet „Antwort finden“ auch ohne Anmeldung an und schliesst danach das Menue', () => {
      const rundgang = spyOn(component.rundgang, 'emit');
      const schliessen = spyOn(component.closeMenu, 'emit');

      const eintrag = fixture.nativeElement.querySelector('.mobile-menu-rundgang') as HTMLButtonElement;
      expect(eintrag.textContent).toContain('Antwort finden (5 Schritte)');
      eintrag.click();

      expect(rundgang).toHaveBeenCalledWith('antwort-finden');
      expect(schliessen).toHaveBeenCalled();
      expect(fixture.nativeElement.querySelector('.mobile-menu-rundgang-mitmachen')).toBeNull();
    });

    it('bietet Angemeldeten zusaetzlich den Rundgang Selbst beitragen an', () => {
      component.userInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Anna B.', claims: null };
      fixture.detectChanges();
      const rundgang = spyOn(component.rundgang, 'emit');

      const eintrag = fixture.nativeElement.querySelector('.mobile-menu-rundgang-mitmachen') as HTMLButtonElement;
      expect(eintrag.textContent).toContain('Selbst beitragen (4 Schritte)');
      eintrag.click();

      expect(rundgang).toHaveBeenCalledWith('mitmachen');
    });

    // R61 (#644): Zwei Rundgaenge hatten dasselbe Faehnchen
    it('gibt beiden Rundgaengen je ein eigenes Icon', () => {
      component.userInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Anna B.', claims: null };
      fixture.detectChanges();
      const icon = (sel: string) => fixture.nativeElement.querySelector(`${sel} mat-icon`).textContent.trim();

      expect(icon('.mobile-menu-rundgang')).not.toBe(icon('.mobile-menu-rundgang-mitmachen'));
    });
  });

  describe('Rechtstexte', () => {
    const eintraege: Array<[string, string]> = [
      ['.legal-impressum', '/impressum'],
      ['.legal-datenschutz', '/datenschutz'],
      ['.legal-nutzungsbedingungen', '/nutzungsbedingungen'],
    ];

    for (const [selektor, pfad] of eintraege) {
      it(`verlinkt ${pfad} und schliesst danach das Menue`, () => {
        const eintrag = link(selektor);
        expect(eintrag).withContext(selektor).toBeTruthy();
        expect(eintrag.getAttribute('href')).toBe(pfad);

        spyOn(component.closeMenu, 'emit');
        eintrag.click();
        expect(component.closeMenu.emit).toHaveBeenCalled();
      });
    }

    it('zeigt die Rechtstexte auch ohne Anmeldung', () => {
      component.userInfo = null;
      fixture.detectChanges();
      expect(link('.legal-impressum')).toBeTruthy();
      expect(link('.legal-datenschutz')).toBeTruthy();
      expect(link('.legal-nutzungsbedingungen')).toBeTruthy();
    });
  });

  it('nennt im Fusstext zuerst den Anbieter, dann den Entwickler', () => {
    const text = (fixture.nativeElement.querySelector('.mobile-menu-about') as HTMLElement)
      .textContent!.replace(/\s+/g, ' ')
      .trim();
    expect(text).toBe('Ein Projekt von Netzbegrünung e.V., entwickelt von Sebastian Banach');
    expect(link('.anbieter-link').getAttribute('href')).toBe('https://netzbegruenung.de/');
  });

  it('verlinkt den Entwickler auf /about statt auf eine leere Adresse im neuen Tab', () => {
    const about = link('.about-link');
    expect(about.getAttribute('href')).toBe('/about');
    expect(about.getAttribute('target')).toBeNull();
  });

  it('verlinkt Angemeldete auf "Hier fehlt eine Antwort" und schliesst danach das Menue', () => {
    component.userInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Anna B.', claims: null };
    fixture.detectChanges();

    const eintrag = link('.mobile-menu-fehlt-antwort');
    expect(eintrag.getAttribute('href')).toBe('/hier-fehlt-eine-antwort');
    expect(eintrag.textContent).toContain('Hier fehlt eine Antwort');

    spyOn(component.closeMenu, 'emit');
    eintrag.click();
    expect(component.closeMenu.emit).toHaveBeenCalled();
  });

  it('zeigt "Hier fehlt eine Antwort" ohne Anmeldung nicht', () => {
    component.userInfo = null;
    fixture.detectChanges();
    expect(link('.mobile-menu-fehlt-antwort')).toBeNull();
  });

  // Design-Audit A4 (#512): Mobil fuehrte kein Weg in den Admin-Bereich.
  it('verlinkt Admins auf den Admin-Bereich und schliesst danach das Menue', () => {
    component.userInfo = { isAuthenticated: true, isAdmin: true, userId: 'u-1', userName: 'Anna B.', claims: null };
    fixture.detectChanges();

    const eintrag = link('.mobile-menu-admin');
    expect(eintrag.getAttribute('href')).toBe('/admin/dashboard');
    expect(eintrag.textContent).toContain('Admin');

    spyOn(component.closeMenu, 'emit');
    eintrag.click();
    expect(component.closeMenu.emit).toHaveBeenCalled();
  });

  it('zeigt am Admin-Link die Zahl offener Meldungen', () => {
    component.userInfo = { isAuthenticated: true, isAdmin: true, userId: 'u-1', userName: 'Anna B.', claims: null };
    fixture.detectChanges();

    const eintrag = link('.mobile-menu-admin');
    expect(eintrag.querySelector('.zahl')!.textContent!.trim()).toBe('2');
    expect(eintrag.textContent!.replace(/\s+/g, ' ')).toContain('Admin2, 2 offene Meldungen');
  });

  it('zeigt den Admin-Bereich nur Admins', () => {
    component.userInfo = { isAuthenticated: true, isAdmin: false, userId: 'u-1', userName: 'Anna B.', claims: null };
    fixture.detectChanges();
    expect(link('.mobile-menu-admin')).toBeNull();
  });

  it('bietet Angemeldeten "Profilbild wählen" an und schliesst danach das Menue', () => {
    component.userInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Anna B.', claims: null };
    fixture.detectChanges();
    const profilbild = spyOn(component.profilbild, 'emit');
    const schliessen = spyOn(component.closeMenu, 'emit');

    const eintrag = fixture.nativeElement.querySelector('.mobile-menu-profilbild') as HTMLButtonElement;
    expect(eintrag.textContent).toContain('Profilbild wählen');
    eintrag.click();

    expect(profilbild).toHaveBeenCalled();
    expect(schliessen).toHaveBeenCalled();
  });

  it('bietet Angemeldeten die Art.-9-Einwilligung als "Datenschutz-Einstellungen" an (#489, #644)', () => {
    component.userInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Anna B.', claims: null };
    fixture.detectChanges();

    const eintrag = link('.mobile-menu-einwilligung');
    expect(eintrag?.getAttribute('href')).toBe('/einwilligung');
    expect(eintrag?.textContent!.trim()).toBe('fact_check Datenschutz-Einstellungen');
  });

  // R61 (#644): Emojis und Linien-Icons standen gemischt
  it('nimmt fuer alle Eintraege Material-Icons, keine Emojis', () => {
    component.userInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Anna B.', claims: null };
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.menu-emoji')).toBeNull();
    for (const sel of ['.mobile-menu-einwerfen', '.mobile-menu-fangkorb', '.mobile-menu-beitraege']) {
      expect(fixture.nativeElement.querySelector(`${sel} mat-icon`)).withContext(sel).not.toBeNull();
      expect(fixture.nativeElement.querySelector(sel).textContent).not.toMatch(/\p{Extended_Pictographic}/u);
    }
  });

  // R61 (#644): Die aktuelle Seite war nicht markiert
  it('hebt die aktuelle Seite hervor und setzt aria-current', async () => {
    component.userInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Anna B.', claims: null };
    await TestBed.inject(Router).navigateByUrl('/fangkorb?x=1');
    fixture.detectChanges();

    const fangkorb = fixture.nativeElement.querySelector('.mobile-menu-fangkorb') as HTMLElement;
    expect(fangkorb.classList).toContain('aktiv');
    expect(fangkorb.getAttribute('aria-current')).toBe('page');
    expect(fixture.nativeElement.querySelectorAll('[aria-current="page"]').length).toBe(1);

    await TestBed.inject(Router).navigateByUrl('/impressum');
    fixture.detectChanges();
    expect(fangkorb.getAttribute('aria-current')).toBeNull();
    expect(link('.legal-impressum').getAttribute('aria-current')).toBe('page');
  });

  it('zeigt "Profilbild wählen" ohne Anmeldung nicht', () => {
    component.userInfo = null;
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.mobile-menu-profilbild')).toBeNull();
  });
});
