import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subject, of } from 'rxjs';

import { MEILENSTEINE_GESEHEN_SCHLUESSEL, MeilensteinHinweisService } from './meilenstein-hinweis.service';
import { Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';

describe('MeilensteinHinweisService (#351)', () => {
  let meilensteine: Meilenstein[];
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let aktion: Subject<void>;
  let router: jasmine.SpyObj<Router>;
  let laden: jasmine.Spy;

  function meilenstein(kennung: string, erreicht: boolean, name = kennung): Meilenstein {
    return { kennung, name, untertitel: '', beschreibung: '', bild: '', bildnachweis: '', art: 'weg', schwelle: 1, stand: erreicht ? 1 : 0, erreicht };
  }

  function dienst(): MeilensteinHinweisService {
    aktion = new Subject<void>();
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    snackBar.open.and.returnValue({ onAction: () => aktion.asObservable() } as never);
    router = jasmine.createSpyObj<Router>('Router', ['navigateByUrl']);
    laden = jasmine.createSpy('getEigeneMeilensteine').and.callFake(() => of(meilensteine));
    TestBed.configureTestingModule({
      providers: [
        { provide: UsageTrackingService, useValue: { getEigeneMeilensteine: laden } },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: Router, useValue: router },
      ],
    });
    return TestBed.inject(MeilensteinHinweisService);
  }

  function gesehen(): string[] {
    return JSON.parse(localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL) ?? '[]');
  }

  beforeEach(() => localStorage.removeItem(MEILENSTEINE_GESEHEN_SCHLUESSEL));
  afterEach(() => localStorage.removeItem(MEILENSTEINE_GESEHEN_SCHLUESSEL));

  it('nennt einen neu erreichten Meilenstein einmal und merkt ihn sich', () => {
    meilensteine = [meilenstein('einwurf-1', true, 'Erster Einwurf'), meilenstein('nutzung-1', false)];
    const hinweis = dienst();

    hinweis.pruefen();
    hinweis.pruefen();

    expect(snackBar.open).toHaveBeenCalledOnceWith('Meilenstein erreicht: Erster Einwurf', 'Ansehen', jasmine.any(Object));
    expect(gesehen()).toEqual(['einwurf-1']);
  });

  it('fasst mehrere neue zusammen, statt sie einzeln aufzuzählen', () => {
    meilensteine = [meilenstein('einwurf-1', true), meilenstein('ausformuliert-1', true)];

    dienst().pruefen();

    expect(snackBar.open).toHaveBeenCalledOnceWith('2 Meilensteine erreicht', 'Ansehen', jasmine.any(Object));
  });

  it('schweigt ohne neue Meilensteine (auch bei ausgeschalteten Punkten: leere Liste)', () => {
    localStorage.setItem(MEILENSTEINE_GESEHEN_SCHLUESSEL, JSON.stringify(['einwurf-1']));
    meilensteine = [meilenstein('einwurf-1', true)];
    const hinweis = dienst();

    hinweis.pruefen();
    meilensteine = [];
    hinweis.pruefen();

    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('führt mit "Ansehen" zu Meine Beiträge', () => {
    meilensteine = [meilenstein('einwurf-1', true)];

    dienst().pruefen();
    aktion.next();

    expect(router.navigateByUrl).toHaveBeenCalledWith('/contributions');
  });

  it('fragt ohne Speicher gar nicht erst: Der Hinweis käme sonst jedes Mal wieder', () => {
    meilensteine = [meilenstein('einwurf-1', true)];
    const hinweis = dienst();
    spyOn(Storage.prototype, 'getItem').and.throwError('gesperrt');

    hinweis.pruefen();

    expect(laden).not.toHaveBeenCalled();
    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('übersteht einen kaputten Eintrag im Speicher', () => {
    localStorage.setItem(MEILENSTEINE_GESEHEN_SCHLUESSEL, '{kaputt');
    meilensteine = [meilenstein('einwurf-1', true)];

    dienst().pruefen();

    expect(snackBar.open).not.toHaveBeenCalled();
  });
});
