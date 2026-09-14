import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MobileMenuComponent } from './mobile-menu';

describe('MobileMenuComponent', () => {
  let component: MobileMenuComponent;
  let fixture: ComponentFixture<MobileMenuComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MobileMenuComponent],
      providers: [provideRouter([])]
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
});
