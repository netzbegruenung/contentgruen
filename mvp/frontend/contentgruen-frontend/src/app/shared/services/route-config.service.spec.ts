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
});
