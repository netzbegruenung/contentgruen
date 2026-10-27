import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { DestillierUebergabeService, Vorbefuellung } from './destillier-uebergabe.service';
import { Einwurf, EinwurfService } from '../services/einwurf.service';
import { LoggingService } from '../services/logging.service';

describe('DestillierUebergabeService', () => {
  let service: DestillierUebergabeService;
  let einwurfService: jasmine.SpyObj<EinwurfService>;
  let router: jasmine.SpyObj<Router>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(() => {
    einwurfService = jasmine.createSpyObj('EinwurfService', ['einwurfLaden', 'updateStatus']);
    router = jasmine.createSpyObj('Router', ['navigate']);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      providers: [
        DestillierUebergabeService,
        { provide: EinwurfService, useValue: einwurfService },
        { provide: Router, useValue: router },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error']) },
      ],
    });
    service = TestBed.inject(DestillierUebergabeService);
  });

  it('macht den eigenen Satz zum Titel und den bereinigten Link zur Herkunft', () => {
    einwurfService.einwurfLaden.and.returnValue(
      of({
        id: 'id-1',
        url: 'https://www.instagram.com/reel/ABC/?igsh=xyz&utm_source=ig',
        own_draft: 'Waermepumpe lohnt sich auch im Altbau',
      } as Einwurf),
    );
    let ergebnis: Vorbefuellung | undefined;

    service.vorbefuellungLaden('id-1').subscribe((v) => (ergebnis = v));

    expect(ergebnis).toEqual(jasmine.objectContaining({
      einwurfId: 'id-1',
      titel: 'Waermepumpe lohnt sich auch im Altbau',
      url: 'https://www.instagram.com/reel/ABC/',
    }));
    // Der Kopf ueber dem Formular: der Einwurf als Karte mit dem einen Satz
    expect(ergebnis!.kopf!.einwurfAngaben!.einwurfId).toBe('id-1');
    expect(ergebnis!.kopf!.einwurfAngaben!.kopfSatz).toBe('Waermepumpe lohnt sich auch im Altbau');
  });

  it('verknuepft ohne Sprung und meldet, ob es geklappt hat', () => {
    einwurfService.updateStatus.and.returnValues(of({} as any), throwError(() => new Error('500')));
    const ergebnisse: boolean[] = [];

    service.mitBeitragVerknuepfen('id-1', 'k-1', 'commentary').subscribe((ok) => ergebnisse.push(ok));
    service.mitBeitragVerknuepfen('id-1', 'k-1', 'commentary').subscribe((ok) => ergebnisse.push(ok));

    expect(einwurfService.updateStatus).toHaveBeenCalledWith('id-1', 'processed', 'k-1', 'commentary');
    expect(ergebnisse).toEqual([true, false]);
    expect(router.navigate).not.toHaveBeenCalled();
    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('laesst Titel und Herkunft leer, wenn es keinen eigenen Satz und keinen Link gibt', () => {
    einwurfService.einwurfLaden.and.returnValue(
      of({ id: 'id-1', url: null, own_draft: null } as Einwurf),
    );
    let ergebnis: Vorbefuellung | undefined;

    service.vorbefuellungLaden('id-1').subscribe((v) => (ergebnis = v));

    expect(ergebnis).toEqual(jasmine.objectContaining({ einwurfId: 'id-1', titel: '', url: null }));
    expect(ergebnis!.kopf!.einwurfAngaben!.kopfSatz).toBeUndefined();
  });

  it('reicht den Tab der Handlung an die Destillier-Ansicht weiter', () => {
    service.zumNaechsten('id-1', 'destillieren');

    expect(router.navigate).toHaveBeenCalledOnceWith(['/destillieren'], {
      queryParams: { nach: 'id-1', tab: 'destillieren' },
    });
  });

});
