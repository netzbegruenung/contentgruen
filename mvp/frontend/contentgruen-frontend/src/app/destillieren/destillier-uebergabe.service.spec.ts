import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { DestillierUebergabeService, Vorbefuellung } from './destillier-uebergabe.service';
import { RawInput, RawInputService } from '../services/raw-input.service';
import { LoggingService } from '../services/logging.service';

describe('DestillierUebergabeService', () => {
  let service: DestillierUebergabeService;
  let rawInputService: jasmine.SpyObj<RawInputService>;
  let router: jasmine.SpyObj<Router>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(() => {
    rawInputService = jasmine.createSpyObj('RawInputService', ['getRawInput', 'updateStatus']);
    router = jasmine.createSpyObj('Router', ['navigate']);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      providers: [
        DestillierUebergabeService,
        { provide: RawInputService, useValue: rawInputService },
        { provide: Router, useValue: router },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error']) },
      ],
    });
    service = TestBed.inject(DestillierUebergabeService);
  });

  it('macht den eigenen Satz zum Titel und den bereinigten Link zur Herkunft', () => {
    rawInputService.getRawInput.and.returnValue(
      of({
        id: 'id-1',
        url: 'https://www.instagram.com/reel/ABC/?igsh=xyz&utm_source=ig',
        own_draft: 'Waermepumpe lohnt sich auch im Altbau',
      } as RawInput),
    );
    let ergebnis: Vorbefuellung | undefined;

    service.vorbefuellungLaden('id-1').subscribe((v) => (ergebnis = v));

    expect(ergebnis).toEqual(jasmine.objectContaining({
      rohinputId: 'id-1',
      titel: 'Waermepumpe lohnt sich auch im Altbau',
      url: 'https://www.instagram.com/reel/ABC/',
    }));
    // Der Kopf ueber dem Formular: der Einwurf als Rohling mit dem einen Satz
    expect(ergebnis!.kopf!.rohling!.einwurfId).toBe('id-1');
    expect(ergebnis!.kopf!.rohling!.kopfSatz).toBe('Waermepumpe lohnt sich auch im Altbau');
  });

  it('markiert ohne Sprung und meldet, ob es geklappt hat', () => {
    rawInputService.updateStatus.and.returnValues(of({} as any), throwError(() => new Error('500')));
    const ergebnisse: boolean[] = [];

    service.alsVerarbeitetMarkieren('id-1', 'k-1', 'commentary').subscribe((ok) => ergebnisse.push(ok));
    service.alsVerarbeitetMarkieren('id-1', 'k-1', 'commentary').subscribe((ok) => ergebnisse.push(ok));

    expect(rawInputService.updateStatus).toHaveBeenCalledWith('id-1', 'processed', 'k-1', 'commentary');
    expect(ergebnisse).toEqual([true, false]);
    expect(router.navigate).not.toHaveBeenCalled();
    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('laesst Titel und Herkunft leer, wenn es keinen Entwurf und keinen Link gibt', () => {
    rawInputService.getRawInput.and.returnValue(
      of({ id: 'id-1', url: null, own_draft: null } as RawInput),
    );
    let ergebnis: Vorbefuellung | undefined;

    service.vorbefuellungLaden('id-1').subscribe((v) => (ergebnis = v));

    expect(ergebnis).toEqual(jasmine.objectContaining({ rohinputId: 'id-1', titel: '', url: null }));
    expect(ergebnis!.kopf!.rohling!.kopfSatz).toBeUndefined();
  });

  it('markiert nach dem Speichern mit Beitragstyp als verarbeitet und springt weiter', () => {
    rawInputService.updateStatus.and.returnValue(of({ id: 'id-1' } as RawInput));

    service.nachSpeichern('id-1', 'beitrag-1', 'generic_text');

    expect(rawInputService.updateStatus).toHaveBeenCalledWith(
      'id-1',
      'processed',
      'beitrag-1',
      'generic_text',
    );
    // Der Beitrag steht: Der Einwurf liegt danach unter "Erledigt".
    expect(router.navigate).toHaveBeenCalledWith(['/destillieren'], {
      queryParams: { nach: 'id-1', tab: 'erledigt' },
    });
  });

  it('springt auch weiter, wenn das Markieren scheitert, und sagt es', () => {
    rawInputService.updateStatus.and.returnValue(throwError(() => new Error('kaputt')));

    service.nachSpeichern('id-1', 'beitrag-1', 'commentary');

    expect(snackBar.open).toHaveBeenCalled();
    expect(snackBar.open.calls.mostRecent().args[0]).toContain('Beitrag ist gespeichert');
    // Ohne Verknuepfung bleibt der Einwurf bei seinen Saetzen - Tab "Ausformulieren".
    expect(router.navigate).toHaveBeenCalledWith(['/destillieren'], {
      queryParams: { nach: 'id-1', tab: 'ausformulieren' },
    });
  });

  it('fuehrt beim Abbrechen zurueck zum Einwurf', () => {
    service.zurueckZumEinwurf('id-1');

    expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-1']);
  });
});
