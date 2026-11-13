import { ComponentFixture, TestBed, discardPeriodicTasks, fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subject, of, throwError } from 'rxjs';
import { NACHLADEN_MS, SuchanfragenFreigebenComponent } from './suchanfragen-freigeben.component';
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
  let sichtbarkeit: DocumentVisibilityState;
  let gemeldet: number[];

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
    fixture.componentInstance.anzahl.subscribe((n) => gemeldet.push(n));
    fixture.detectChanges();
  }

  beforeEach(() => {
    gemeldet = [];
    sichtbarkeit = 'visible';
    spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);
    service = jasmine.createSpyObj('SuchanfragenFreigabeService', ['zuPruefen', 'freigeben', 'ablehnen']);
    service.zuPruefen.and.returnValue(
      of({ suchanfragen: [suchanfrage('a', 'Sind Wärmepumpen laut?', 3), suchanfrage('b', 'Ist Solar teuer?', 1)] }),
    );
    service.freigeben.and.returnValue(of({ statement_id: 'a', freigegeben: true }));
    service.ablehnen.and.returnValue(of({ statement_id: 'a', freigegeben: false }));
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [SuchanfragenFreigebenComponent, NoopAnimationsModule],
      providers: [{ provide: SuchanfragenFreigabeService, useValue: service }],
    });
    TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });
  });

  afterEach(() => fixture?.destroy());

  it('zeigt beim ersten Laden einen Spinner mit Text, nicht „bitte neu laden“', () => {
    service.zuPruefen.and.returnValue(new Subject<ZuPruefendeSuchanfragenResponse>());
    erzeugen();

    expect(element().querySelector('mat-spinner')).not.toBeNull();
    expect(element().textContent).toContain('Suchanfragen werden geladen');
    expect(element().textContent).not.toContain('neu laden');
  });

  it('listet die Suchanfragen mit der Zahl der Personen und meldet die Anzahl', fakeAsync(() => {
    erzeugen();
    flushMicrotasks();

    expect(element().textContent).toContain('„Sind Wärmepumpen laut?“');
    expect(element().textContent).toContain('3 Personen suchten das ohne Treffer');
    expect(element().textContent).toContain('1 Person suchte das ohne Treffer');
    expect(gemeldet).toEqual([2]);
    discardPeriodicTasks();
  }));

  it('zeigt die Liste nur, wenn ihr Umschalter gewählt ist, zählt aber trotzdem', fakeAsync(() => {
    erzeugen(false);
    flushMicrotasks();

    expect(element().textContent).not.toContain('Sind Wärmepumpen laut?');
    expect(gemeldet).toEqual([2]);
    discardPeriodicTasks();
  }));

  it('gibt frei, nimmt den Eintrag aus der Liste und meldet die neue Anzahl', fakeAsync(() => {
    erzeugen();
    flushMicrotasks();

    knoepfe('Freigeben')[0].click();
    flushMicrotasks();
    fixture.detectChanges();

    expect(service.freigeben).toHaveBeenCalledWith('a');
    expect(element().textContent).not.toContain('Sind Wärmepumpen laut?');
    expect(gemeldet).toEqual([2, 1]);
    expect(snackBar.open).toHaveBeenCalledWith('Freigegeben', 'OK', jasmine.any(Object));
    discardPeriodicTasks();
  }));

  it('lehnt ab; eine ältere Antwort bringt den Eintrag nicht zurück', fakeAsync(() => {
    erzeugen();
    flushMicrotasks();

    knoepfe('Ablehnen')[0].click();
    fixture.componentInstance.laden();
    flushMicrotasks();
    fixture.detectChanges();

    expect(service.ablehnen).toHaveBeenCalledWith('a');
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
