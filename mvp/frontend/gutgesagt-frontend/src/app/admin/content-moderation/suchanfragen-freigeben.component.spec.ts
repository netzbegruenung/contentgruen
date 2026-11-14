import { ComponentFixture, TestBed, discardPeriodicTasks, fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { Subject, of, throwError } from 'rxjs';
import { FREIGEBEN_FRAGE, SuchanfragenFreigebenComponent } from './suchanfragen-freigeben.component';
import { NACHLADEN_MS } from '../../shared/selbst-nachladen';
import { ZuTunService } from '../../services/zu-tun.service';
import {
  SuchanfragenFreigabeService,
  ZuPruefendeSuchanfrage,
  ZuPruefendeSuchanfragenResponse,
} from '../../services/suchanfragen-freigabe.service';

function suchanfrage(id: string, text: string, personen: number): ZuPruefendeSuchanfrage {
  return { statement_id: id, statement_text: text, personen_ohne_treffer: personen };
}

describe('SuchanfragenFreigebenComponent', () => {
  let fixture: ComponentFixture<SuchanfragenFreigebenComponent>;
  let service: jasmine.SpyObj<SuchanfragenFreigabeService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let dialog: jasmine.SpyObj<MatDialog>;
  /** Was die Rückfrage vor dem Freigeben ergibt; Standard: bestätigt. */
  let antwort: boolean | undefined;
  let sichtbarkeit: DocumentVisibilityState;
  let zuTun: jasmine.SpyObj<ZuTunService>;

  function element(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function knoepfe(text: string): HTMLButtonElement[] {
    return (Array.from(element().querySelectorAll('button')) as HTMLButtonElement[]).filter((b) =>
      b.textContent?.includes(text),
    );
  }

  function erzeugen(aktiv = true) {
    fixture = TestBed.createComponent(SuchanfragenFreigebenComponent);
    fixture.componentRef.setInput('aktiv', aktiv);
    fixture.detectChanges();
  }

  beforeEach(() => {
    zuTun = jasmine.createSpyObj('ZuTunService', ['aktualisieren']);
    sichtbarkeit = 'visible';
    spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);
    service = jasmine.createSpyObj('SuchanfragenFreigabeService', ['zuPruefen', 'anzahl', 'freigeben', 'ablehnen']);
    service.anzahl.and.returnValue(of({ anzahl: 5 }));
    service.zuPruefen.and.returnValue(
      of({ suchanfragen: [suchanfrage('a', 'Sind Wärmepumpen laut?', 3), suchanfrage('b', 'Ist Solar teuer?', 1)] }),
    );
    service.freigeben.and.returnValue(of({ statement_id: 'a', freigegeben: true }));
    service.ablehnen.and.returnValue(of({ statement_id: 'a', freigegeben: false }));
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    antwort = true;
    dialog = jasmine.createSpyObj('MatDialog', ['open']);
    dialog.open.and.callFake(() => ({ afterClosed: () => of(antwort) }) as any);

    TestBed.configureTestingModule({
      imports: [SuchanfragenFreigebenComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: SuchanfragenFreigabeService, useValue: service },
        { provide: ZuTunService, useValue: zuTun },
      ],
    });
    TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });
    TestBed.overrideProvider(MatDialog, { useValue: dialog });
  });

  afterEach(() => fixture?.destroy());

  it('zeigt beim ersten Laden einen Spinner mit Text, nicht „bitte neu laden“', () => {
    service.zuPruefen.and.returnValue(new Subject<ZuPruefendeSuchanfragenResponse>());
    erzeugen();

    expect(element().querySelector('mat-spinner')).not.toBeNull();
    expect(element().textContent).toContain('Suchanfragen werden geladen');
    expect(element().textContent).not.toContain('neu laden');
  });

  it('listet die Suchanfragen mit der Zahl der Personen, still geladen', fakeAsync(() => {
    erzeugen();
    flushMicrotasks();
    fixture.detectChanges();

    expect(element().textContent).toContain('„Sind Wärmepumpen laut?“');
    expect(element().textContent).toContain('3 Personen suchten das ohne Treffer');
    expect(element().textContent).toContain('1 Person suchte das ohne Treffer');
    // Still: ohne Sprung auf /login bei 401
    expect(service.zuPruefen).toHaveBeenCalledWith(true);
    discardPeriodicTasks();
  }));

  it('lädt ohne gewählten Umschalter nichts, auch die Zahl nicht (die kommt aus dem ZuTunService)', fakeAsync(() => {
    erzeugen(false);
    flushMicrotasks();

    expect(service.zuPruefen).not.toHaveBeenCalled();
    expect(service.anzahl).not.toHaveBeenCalled();
    expect(element().textContent).not.toContain('Sind Wärmepumpen laut?');

    tick(NACHLADEN_MS * 4);
    expect(service.zuPruefen).not.toHaveBeenCalled();
    discardPeriodicTasks();
  }));

  it('hört beim Wechsel auf einen anderen Umschalter auf nachzuladen', fakeAsync(() => {
    erzeugen();
    service.zuPruefen.calls.reset();

    fixture.componentRef.setInput('aktiv', false);
    fixture.detectChanges();
    tick(NACHLADEN_MS * 4);

    expect(service.zuPruefen).not.toHaveBeenCalled();
    discardPeriodicTasks();
  }));

  it('zeigt nach 401/403 „Sitzung abgelaufen – Anmelden“ und fragt nicht weiter', fakeAsync(() => {
    service.zuPruefen.and.returnValue(throwError(() => ({ status: 401 })));
    erzeugen();
    fixture.detectChanges();

    const link = element().querySelector('[data-testid="suchanfragen-abgelaufen"] a') as HTMLAnchorElement;
    expect(link.textContent!.trim()).toBe('Sitzung abgelaufen – Anmelden');
    expect(link.getAttribute('href')).toContain('/login');
    expect(element().textContent).not.toContain('Es wird gleich noch einmal versucht');

    tick(NACHLADEN_MS * 8);
    expect(service.zuPruefen).toHaveBeenCalledTimes(1);
    discardPeriodicTasks();
  }));

  it('bricht laufende Anfragen beim Aushängen ab', () => {
    const liste = new Subject<ZuPruefendeSuchanfragenResponse>();
    service.zuPruefen.and.returnValue(liste);
    erzeugen();

    fixture.destroy();

    expect(liste.observed).toBeFalse();
  });

  it('gibt frei, nimmt den Eintrag aus der Liste und stößt die Zahl an', fakeAsync(() => {
    erzeugen();
    flushMicrotasks();
    fixture.detectChanges();

    knoepfe('Freigeben')[0].click();
    flushMicrotasks();
    fixture.detectChanges();

    expect(service.freigeben).toHaveBeenCalledWith('a');
    expect(element().textContent).not.toContain('Sind Wärmepumpen laut?');
    expect(zuTun.aktualisieren).toHaveBeenCalledTimes(1);
    expect(snackBar.open).toHaveBeenCalledWith('Freigegeben', 'OK', jasmine.any(Object));
    discardPeriodicTasks();
  }));

  it('fragt vor dem Freigeben nach und gibt bei Abbrechen nichts frei (M1)', fakeAsync(() => {
    antwort = false;
    erzeugen();
    flushMicrotasks();

    knoepfe('Freigeben')[0].click();
    flushMicrotasks();
    fixture.detectChanges();

    expect(dialog.open.calls.mostRecent().args[1]!.data).toBe(FREIGEBEN_FRAGE);
    expect(service.freigeben).not.toHaveBeenCalled();
    expect(element().textContent).toContain('Sind Wärmepumpen laut?');
    expect(knoepfe('Freigeben')[0].disabled).toBeFalse();
    discardPeriodicTasks();
  }));

  it('fragt nach dem vereinbarten Muster', () => {
    expect(FREIGEBEN_FRAGE).toEqual({
      titel: 'Suchanfrage freigeben?',
      text: 'Die Suchanfrage ist danach für alle sichtbar, etwa in „Hier fehlt eine Antwort“.',
      ja: 'Freigeben',
      nein: 'Abbrechen',
    });
  });

  it('lehnt ohne Rückfrage ab; eine ältere Antwort bringt den Eintrag nicht zurück', fakeAsync(() => {
    erzeugen();
    flushMicrotasks();

    knoepfe('Ablehnen')[0].click();
    fixture.componentInstance.laden();
    flushMicrotasks();
    fixture.detectChanges();

    expect(service.ablehnen).toHaveBeenCalledWith('a');
    expect(dialog.open).not.toHaveBeenCalled();
    expect(element().textContent).not.toContain('Sind Wärmepumpen laut?');
    expect(element().textContent).toContain('Ist Solar teuer?');
    discardPeriodicTasks();
  }));

  it('lädt nach einem Fehler beim Entscheiden die Liste neu', fakeAsync(() => {
    erzeugen();
    flushMicrotasks();
    service.freigeben.and.returnValue(throwError(() => ({ status: 409 })));
    service.zuPruefen.calls.reset();

    knoepfe('Freigeben')[0].click();
    flushMicrotasks();

    expect(service.zuPruefen).toHaveBeenCalledTimes(1);
    expect(snackBar.open).toHaveBeenCalledWith(
      'Die Suchanfrage gibt es so nicht mehr; die Liste wird aktualisiert',
      'OK',
      jasmine.any(Object),
    );
    discardPeriodicTasks();
  }));

  it('lädt alle 30 Sekunden nach, solange die Seite sichtbar ist', fakeAsync(() => {
    erzeugen();
    service.zuPruefen.calls.reset();

    tick(NACHLADEN_MS);
    expect(service.zuPruefen).toHaveBeenCalledTimes(1);

    sichtbarkeit = 'hidden';
    tick(NACHLADEN_MS);
    expect(service.zuPruefen).toHaveBeenCalledTimes(1);
    discardPeriodicTasks();
  }));

  it('lädt nach, wenn die Seite wieder sichtbar wird', fakeAsync(() => {
    erzeugen();
    service.zuPruefen.calls.reset();

    sichtbarkeit = 'visible';
    document.dispatchEvent(new Event('visibilitychange'));

    expect(service.zuPruefen).toHaveBeenCalledTimes(1);
    discardPeriodicTasks();
  }));

  it('lädt beim Wechsel auf ihren Umschalter nach', fakeAsync(() => {
    erzeugen(false);
    service.zuPruefen.calls.reset();

    fixture.componentRef.setInput('aktiv', true);
    fixture.detectChanges();

    expect(service.zuPruefen).toHaveBeenCalledTimes(1);
    discardPeriodicTasks();
  }));

  it('sagt beim Ladefehler, dass es gleich noch einmal versucht wird', fakeAsync(() => {
    service.zuPruefen.and.returnValue(throwError(() => new Error('weg')));
    erzeugen();

    expect(element().textContent).toContain('Es wird gleich noch einmal versucht');
    discardPeriodicTasks();
  }));
});
