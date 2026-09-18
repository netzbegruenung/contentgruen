import { TestBed } from '@angular/core/testing';

import { RouteConfigService } from './route-config.service';

describe('RouteConfigService', () => {
  let service: RouteConfigService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RouteConfigService);
  });

  it('nennt die Destillier-Ansicht im Schritt Typwahl "Ausformulieren"', () => {
    expect(service.getRouteConfig('/destillieren/id-1').pageTitle).toBe('Destillieren');
    expect(service.getRouteConfig('/destillieren/id-1?schritt=typwahl').pageTitle).toBe(
      'Ausformulieren',
    );
  });

  it('zeigt den Pfeil in der Kopfleiste dort in beiden Schritten', () => {
    // Seit dem Navigations-Umbau hat die Ansicht keinen eigenen Pfeil mehr: Der im
    // Kopf fuehrt in den Fangkorb (data.parent) und laesst die Ansicht vorher ihren
    // Satz speichern. Aus der Typwahl zum Satz fuehrt der Knopf im Ablauf.
    expect(service.getRouteConfig('/destillieren/id-1').showBackButton).toBeTrue();
    expect(service.getRouteConfig('/destillieren/id-1?schritt=typwahl').showBackButton).toBeTrue();
  });

  it('benennt die Formularseiten nach ihrem Typ, auch mit Parametern', () => {
    expect(service.getRouteConfig('/workflow/add-commentary').pageTitle).toBe('Kommentar verfassen');
    expect(service.getRouteConfig('/workflow/add-commentary?aussage=a-1').pageTitle).toBe('Kommentar verfassen');
    expect(service.getRouteConfig('/workflow/add-generictext?rohinput=e-1').pageTitle).toBe('Hintergrundinfo verfassen');
    expect(service.getRouteConfig('/workflow/add-image').pageTitle).toBe('Bild hinzufügen');
  });

  it('nennt die Formularseiten mobil nur nach dem Typ', () => {
    expect(service.getRouteConfig('/workflow/add-commentary?aussage=a-1').mobilePageTitle).toBe('Kommentar');
    expect(service.getRouteConfig('/workflow/add-generictext').mobilePageTitle).toBe('Hintergrundinfo');
    expect(service.getRouteConfig('/workflow/add-image').mobilePageTitle).toBe('Bild');
    expect(service.getRouteConfig('/fangkorb').mobilePageTitle).toBeUndefined();
  });

  it('zeigt auf den Formularseiten und /contribute nur den Pfeil, kein Beitragen', () => {
    for (const pfad of ['/workflow/add-commentary', '/workflow/add-generictext', '/workflow/add-image', '/contribute', '/workflow/add-commentary/gespeichert/k-1']) {
      const config = service.getRouteConfig(pfad);
      expect(config.showBackButton).withContext(pfad).toBeTrue();
      expect(config.showContributeButton).withContext(pfad).toBeFalse();
    }
  });

  it('nennt die Ergebnisseite nach dem Speichern "Gespeichert"', () => {
    expect(service.getRouteConfig('/workflow/add-generictext/gespeichert/h-1').pageTitle).toBe('Gespeichert');
    const config = service.getRouteConfig('/workflow/add-commentary/gespeichert/k-1');
    expect(config.pageTitle).toBe('Gespeichert');
    expect(config.mobilePageTitle).toBe('Gespeichert');
    expect(config.showBackButton).toBeTrue();
  });
});
