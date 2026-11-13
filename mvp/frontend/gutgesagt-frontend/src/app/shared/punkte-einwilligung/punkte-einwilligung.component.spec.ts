import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { environment } from '../../../environments/environment';
import { LoggingService } from '../../services/logging.service';
import { PunkteEinwilligungComponent } from './punkte-einwilligung.component';
import { PunkteEinwilligungStand } from './punkte-einwilligung.service';

describe('PunkteEinwilligungComponent (#351)', () => {
  const URL = `${environment.baseUrl}/api/v1/usage/users/me/punkte-einwilligung`;
  const WORTLAUT = { kennung: '2026-11-13', text: 'Freiwillig: Ich willige ausdrücklich ein, …' };
  let http: HttpTestingController;

  function erstellen(ueberschrift: string | null = null) {
    TestBed.configureTestingModule({
      imports: [PunkteEinwilligungComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error']) },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(PunkteEinwilligungComponent);
    fixture.componentInstance.ueberschrift = ueberschrift;
    fixture.detectChanges();
    return fixture;
  }

  function stand(eingewilligt: boolean): PunkteEinwilligungStand {
    return { eingewilligt, wortlaut: eingewilligt ? '2026-11-13' : null, aktueller_wortlaut: WORTLAUT };
  }

  afterEach(() => http.verify());

  it('bietet ohne eingeschaltete Punkte (404) nichts an', () => {
    const fixture = erstellen();
    http.expectOne(URL).flush('', { status: 404, statusText: 'Not Found' });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('mat-checkbox')).toBeNull();
  });

  it('zeigt den Wortlaut am Häkchen, nichts vorausgewählt', () => {
    const fixture = erstellen('Punkte und Meilensteine');
    http.expectOne(URL).flush(stand(false));
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('h3')?.textContent).toContain('Punkte und Meilensteine');
    expect(element.querySelector('mat-checkbox')?.textContent).toContain('Freiwillig: Ich willige ausdrücklich ein');
    expect(element.querySelector<HTMLInputElement>('input[type="checkbox"]')!.checked).toBeFalse();
  });

  it('willigt mit dem Haken ein und widerruft mit dem Entfernen, je mit Wortlaut', () => {
    const fixture = erstellen();
    http.expectOne(URL).flush(stand(false));
    fixture.detectChanges();
    const haken = fixture.nativeElement.querySelector('input[type="checkbox"]') as HTMLInputElement;

    haken.click();
    const ja = http.expectOne({ method: 'PUT', url: URL });
    expect(ja.request.body).toEqual({ eingewilligt: true, wortlaut: '2026-11-13' });
    ja.flush(null);
    fixture.detectChanges();

    haken.click();
    const nein = http.expectOne({ method: 'PUT', url: URL });
    expect(nein.request.body).toEqual({ eingewilligt: false, wortlaut: '2026-11-13' });
    nein.flush(null);
  });

  it('meldet einen Fehler und setzt den Haken zurück', () => {
    const fixture = erstellen();
    http.expectOne(URL).flush(stand(false));
    fixture.detectChanges();
    const haken = fixture.nativeElement.querySelector('input[type="checkbox"]') as HTMLInputElement;

    haken.click();
    fixture.detectChanges(); // wie in der App: nach dem Klick läuft die Änderungserkennung
    expect(haken.checked).toBeTrue();
    http.expectOne({ method: 'PUT', url: URL }).flush('', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[role="status"]')?.textContent).toContain('nicht geklappt');
    expect(haken.checked).toBeFalse();
  });
});
