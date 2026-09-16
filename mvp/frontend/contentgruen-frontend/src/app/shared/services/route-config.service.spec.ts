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

  it('laesst den Pfeil in der Kopfleiste dort in beiden Schritten weg', () => {
    // Die Ansicht hat einen eigenen Pfeil: aus der Typwahl zum Satz, aus dem Satz
    // zum Fangkorb.
    expect(service.getRouteConfig('/destillieren/id-1').showBackButton).toBeFalse();
    expect(service.getRouteConfig('/destillieren/id-1?schritt=typwahl').showBackButton).toBeFalse();
  });
});
