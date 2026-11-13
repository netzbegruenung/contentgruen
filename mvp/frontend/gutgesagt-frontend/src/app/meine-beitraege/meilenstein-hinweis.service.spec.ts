import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subject, of } from 'rxjs';

import { AuthService } from '../auth/auth.service';
import { MeilensteinHinweisService, SAMMELN_MS } from './meilenstein-hinweis.service';
import { merkerSchluessel } from './meilenstein-merker';
import { Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';

describe('MeilensteinHinweisService (#351)', () => {
  const SCHLUESSEL = merkerSchluessel('kim-1');
  let meilensteine: Meilenstein[];
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let aktion: Subject<void>;
  let router: jasmine.SpyObj<Router>;
  let laden: jasmine.Spy;
  let kennung: string | null;

  function meilenstein(k: string, erreicht: boolean, name = k): Meilenstein {
    return { kennung: k, name, untertitel: '', beschreibung: '', bild: '', bildnachweis: '', art: 'weg', schwelle: 1, stand: erreicht ? 1 : 0, erreicht };
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
        { provide: AuthService, useValue: { getCurrentUserId: () => kennung } },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: Router, useValue: router },
      ],
    });
    return TestBed.inject(MeilensteinHinweisService);
  }

  function gesehen(): string[] {
    return JSON.parse(localStorage.getItem(SCHLUESSEL) ?? '[]');
  }

  beforeEach(() => {
    kennung = 'kim-1';
    localStorage.removeItem(SCHLUESSEL);
  });
  afterEach(() => localStorage.removeItem(SCHLUESSEL));

  it('nennt einen neu erreichten Meilenstein einmal und merkt ihn erst danach', fakeAsync(() => {
    meilensteine = [meilenstein('einwurf-1', true, 'Erster Einwurf'), meilenstein('nutzung-1', false)];
    const hinweis = dienst();

    hinweis.pruefen();
    tick(SAMMELN_MS);
    hinweis.pruefen();
    tick(SAMMELN_MS);

    expect(snackBar.open).toHaveBeenCalledOnceWith('Meilenstein erreicht: Erster Einwurf', 'Ansehen', jasmine.any(Object));
    expect(gesehen()).toEqual(['einwurf-1']);
  }));

  it('fasst Anstöße kurz hintereinander zu einer Abfrage und einem Hinweis zusammen', fakeAsync(() => {
    meilensteine = [meilenstein('einwurf-1', true), meilenstein('ausformuliert-1', true)];
    const hinweis = dienst();

    hinweis.pruefen();
    hinweis.pruefen();
    tick(SAMMELN_MS);

    expect(laden).toHaveBeenCalledTimes(1);
    expect(snackBar.open).toHaveBeenCalledOnceWith('2 Meilensteine erreicht', 'Ansehen', jasmine.any(Object));
  }));

  it('neueErreichte merkt nichts: gemerkt wird erst, was angezeigt wurde', () => {
    meilensteine = [meilenstein('einwurf-1', true)];
    const hinweis = dienst();
    let neu: Meilenstein[] = [];

    hinweis.neueErreichte().subscribe((liste) => (neu = liste));

    expect(neu.map((m) => m.kennung)).toEqual(['einwurf-1']);
    expect(gesehen()).toEqual([]);
    hinweis.merken(neu);
    expect(gesehen()).toEqual(['einwurf-1']);
  });

  it('merkt je Konto: ein anderes Konto im selben Browser bekommt seinen Hinweis', fakeAsync(() => {
    localStorage.setItem(SCHLUESSEL, JSON.stringify(['einwurf-1']));
    meilensteine = [meilenstein('einwurf-1', true)];
    kennung = 'bo-2';
    const hinweis = dienst();

    hinweis.pruefen();
    tick(SAMMELN_MS);

    expect(snackBar.open).toHaveBeenCalledTimes(1);
    localStorage.removeItem(merkerSchluessel('bo-2'));
  }));

  it('schweigt ohne neue Meilensteine (auch bei ausgeschalteten Punkten: leere Liste)', fakeAsync(() => {
    localStorage.setItem(SCHLUESSEL, JSON.stringify(['einwurf-1']));
    meilensteine = [meilenstein('einwurf-1', true)];
    const hinweis = dienst();

    hinweis.pruefen();
    tick(SAMMELN_MS);
    meilensteine = [];
    hinweis.pruefen();
    tick(SAMMELN_MS);

    expect(snackBar.open).not.toHaveBeenCalled();
  }));

  it('führt mit "Ansehen" zu Meine Beiträge', fakeAsync(() => {
    meilensteine = [meilenstein('einwurf-1', true)];

    dienst().pruefen();
    tick(SAMMELN_MS);
    aktion.next();

    expect(router.navigateByUrl).toHaveBeenCalledWith('/contributions');
  }));

  it('fragt ohne Speicher oder ohne Konto gar nicht erst', fakeAsync(() => {
    meilensteine = [meilenstein('einwurf-1', true)];
    kennung = null;
    const hinweis = dienst();

    hinweis.pruefen();
    tick(SAMMELN_MS);
    kennung = 'kim-1';
    spyOn(Storage.prototype, 'getItem').and.throwError('gesperrt');
    hinweis.pruefen();
    tick(SAMMELN_MS);

    expect(laden).not.toHaveBeenCalled();
    expect(snackBar.open).not.toHaveBeenCalled();
  }));
});
