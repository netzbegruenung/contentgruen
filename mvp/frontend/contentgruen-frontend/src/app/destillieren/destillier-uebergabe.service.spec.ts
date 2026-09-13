import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router';
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

  it('liest die Einwurf-ID aus ?rohinput', () => {
    const route = { snapshot: { queryParamMap: convertToParamMap({ rohinput: 'id-1' }) } };

    expect(service.rohinputId(route as unknown as ActivatedRoute)).toBe('id-1');
  });

  it('ist ausserhalb des Ablaufs null, auch ohne Snapshot', () => {
    expect(service.rohinputId({} as ActivatedRoute)).toBeNull();
    const route = { snapshot: { queryParamMap: convertToParamMap({ form: 'commentary' }) } };
    expect(service.rohinputId(route as unknown as ActivatedRoute)).toBeNull();
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

    expect(ergebnis).toEqual({
      rohinputId: 'id-1',
      titel: 'Waermepumpe lohnt sich auch im Altbau',
      url: 'https://www.instagram.com/reel/ABC/',
    });
  });

  it('laesst Titel und Herkunft leer, wenn es keinen Entwurf und keinen Link gibt', () => {
    rawInputService.getRawInput.and.returnValue(
      of({ id: 'id-1', url: null, own_draft: null } as RawInput),
    );
    let ergebnis: Vorbefuellung | undefined;

    service.vorbefuellungLaden('id-1').subscribe((v) => (ergebnis = v));

    expect(ergebnis).toEqual({ rohinputId: 'id-1', titel: '', url: null });
  });

  it('markiert nach dem Speichern als verarbeitet und springt weiter', () => {
    rawInputService.updateStatus.and.returnValue(of({ id: 'id-1' } as RawInput));

    service.nachSpeichern('id-1', 'beitrag-1');

    expect(rawInputService.updateStatus).toHaveBeenCalledWith('id-1', 'processed', 'beitrag-1');
    expect(router.navigate).toHaveBeenCalledWith(['/destillieren'], {
      queryParams: { nach: 'id-1' },
    });
  });

  it('springt auch weiter, wenn das Markieren scheitert, und sagt es', () => {
    rawInputService.updateStatus.and.returnValue(throwError(() => new Error('kaputt')));

    service.nachSpeichern('id-1', 'beitrag-1');

    expect(snackBar.open).toHaveBeenCalled();
    expect(snackBar.open.calls.mostRecent().args[0]).toContain('Beitrag ist gespeichert');
    expect(router.navigate).toHaveBeenCalledWith(['/destillieren'], {
      queryParams: { nach: 'id-1' },
    });
  });

  it('fuehrt beim Abbrechen zurueck zum Einwurf', () => {
    service.zurueckZumEinwurf('id-1');

    expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'id-1']);
  });
});
