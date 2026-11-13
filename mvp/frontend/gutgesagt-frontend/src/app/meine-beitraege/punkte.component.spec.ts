import { ComponentFixture, TestBed, discardPeriodicTasks, fakeAsync, tick } from '@angular/core/testing';
import { Observable, Subject, of } from 'rxjs';

import { PUNKTE_NACHLADEN_MS, PUNKTE_PLATZHALTER_MS, PunkteComponent } from './punkte.component';
import { PUNKTE_NICHT_GELADEN, Punktestand, UsageTrackingService } from '../services/usage-tracking.service';

type Antwort = Punktestand | null | typeof PUNKTE_NICHT_GELADEN;

describe('PunkteComponent (#352)', () => {
  let fixture: ComponentFixture<PunkteComponent>;
  let holen: jasmine.Spy<() => Observable<Antwort>>;
  let sichtbarkeit: DocumentVisibilityState;

  function stand(felder: Partial<Punktestand> = {}): Punktestand {
    return { tun: 2, quests: 0, wirkung: 30, gesamt: 32, sammelt: true, ...felder };
  }

  function erstellen(...antworten: (Antwort | Observable<Antwort>)[]): HTMLElement {
    holen = jasmine
      .createSpy('getEigenePunkte')
      .and.returnValues(...antworten.map((a) => (a instanceof Observable ? a : of(a))));
    TestBed.configureTestingModule({
      imports: [PunkteComponent],
      providers: [{ provide: UsageTrackingService, useValue: { getEigenePunkte: holen } }],
    });
    fixture = TestBed.createComponent(PunkteComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function titel(element: HTMLElement): string | undefined {
    return element.querySelector('h2')?.textContent ?? undefined;
  }

  beforeEach(() => {
    sichtbarkeit = 'visible';
    spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);
  });

  afterEach(() => fixture?.destroy());

  it('zeigt nichts bei ausgeschalteten Punkten (404)', () => {
    const element = erstellen(null);

    expect(element.querySelector('.punkte')).toBeNull();
  });

  it('zeigt nichts für Konten, die keine Punkte sammeln (Startkonto, ohne Einwilligung)', () => {
    const element = erstellen(stand({ tun: 0, wirkung: 0, gesamt: 0, sammelt: false }));

    expect(element.querySelector('.punkte')).toBeNull();
    expect(element.querySelector('.punkte-platzhalter')).toBeNull();
  });

  it('zeigt den Stand gesamt und je Stufe und sagt, dass nur die Person ihn sieht', () => {
    const element = erstellen(stand());

    expect(titel(element)).toContain('32');
    expect(element.querySelector('[data-stufe="wirkung"]')?.textContent).toContain('30');
    expect(element.querySelector('[data-stufe="tun"]')?.textContent).toContain('2');
    expect(element.querySelector('.punkte-hinweis')?.textContent).toContain('Nur du siehst deine Punkte');
  });

  it('zeigt 0 Punkte, wenn das Konto sammelt, aber noch nichts hat', () => {
    const element = erstellen(stand({ tun: 0, wirkung: 0, gesamt: 0 }));

    expect(titel(element)).toContain('0');
  });

  it('zeigt Quests erst, wenn sie etwas bringen', () => {
    expect(erstellen(stand()).querySelector('[data-stufe="quests"]')).toBeNull();
    fixture.destroy();
    TestBed.resetTestingModule();

    const element = erstellen(stand({ quests: 4, gesamt: 36 }));
    expect(element.querySelector('[data-stufe="quests"]')?.textContent).toContain('4');
  });

  it('lädt beim Zurückkehren in den Tab nach', () => {
    const element = erstellen(stand(), stand({ wirkung: 40, gesamt: 42 }));

    document.dispatchEvent(new Event('visibilitychange'));
    fixture.detectChanges();

    expect(holen).toHaveBeenCalledTimes(2);
    expect(titel(element)).toContain('42');
  });

  it('lädt nicht nach, wenn der Tab verborgen wird', () => {
    erstellen(stand());

    sichtbarkeit = 'hidden';
    document.dispatchEvent(new Event('visibilitychange'));

    expect(holen).toHaveBeenCalledTimes(1);
  });

  it('behält den letzten Stand, wenn ein Nachladen scheitert', () => {
    const element = erstellen(stand(), PUNKTE_NICHT_GELADEN);

    document.dispatchEvent(new Event('visibilitychange'));
    fixture.detectChanges();

    expect(holen).toHaveBeenCalledTimes(2);
    expect(titel(element)).toContain('32');
  });

  it('lädt in Abständen nach, aber nur solange die Seite sichtbar ist', fakeAsync(() => {
    const element = erstellen(stand(), stand({ wirkung: 50, gesamt: 52 }), stand());

    tick(PUNKTE_NACHLADEN_MS);
    fixture.detectChanges();
    expect(holen).toHaveBeenCalledTimes(2);
    expect(titel(element)).toContain('52');

    sichtbarkeit = 'hidden';
    tick(PUNKTE_NACHLADEN_MS * 3);
    expect(holen).toHaveBeenCalledTimes(2);

    fixture.destroy();
    discardPeriodicTasks();
  }));

  it('fragt hinter einem anderen Tab ([hidden]) nicht nach', fakeAsync(() => {
    erstellen(stand(), stand());
    const huelle = document.createElement('div');
    huelle.hidden = true;
    document.body.appendChild(huelle);
    huelle.appendChild(fixture.nativeElement);

    tick(PUNKTE_NACHLADEN_MS * 2);
    expect(holen).toHaveBeenCalledTimes(1);

    huelle.hidden = false;
    tick(PUNKTE_NACHLADEN_MS);
    expect(holen).toHaveBeenCalledTimes(2);

    fixture.destroy();
    huelle.remove();
    discardPeriodicTasks();
  }));

  it('fragt nach dem Zerstören nicht mehr nach', fakeAsync(() => {
    erstellen(stand(), stand());

    fixture.destroy();
    document.dispatchEvent(new Event('visibilitychange'));
    tick(PUNKTE_NACHLADEN_MS * 2);

    expect(holen).toHaveBeenCalledTimes(1);
  }));

  it('zeigt den Platzhalter erst nach einer Weile und nur, solange der Stand unbekannt ist', fakeAsync(() => {
    const antwort = new Subject<Antwort>();
    const element = erstellen(antwort);

    tick(PUNKTE_PLATZHALTER_MS - 1);
    fixture.detectChanges();
    expect(element.querySelector('.punkte-platzhalter')).toBeNull();

    tick(1);
    fixture.detectChanges();
    expect(element.querySelector('.punkte-platzhalter')?.textContent).toContain('Punkte werden berechnet');

    antwort.next(stand());
    fixture.detectChanges();
    expect(element.querySelector('.punkte-platzhalter')).toBeNull();
    expect(titel(element)).toContain('32');

    fixture.destroy();
    discardPeriodicTasks();
  }));

  it('zeigt keinen Platzhalter, wenn der Stand schnell da ist', fakeAsync(() => {
    const element = erstellen(stand());

    tick(PUNKTE_PLATZHALTER_MS * 2);
    fixture.detectChanges();

    expect(element.querySelector('.punkte-platzhalter')).toBeNull();
    fixture.destroy();
    discardPeriodicTasks();
  }));
});
