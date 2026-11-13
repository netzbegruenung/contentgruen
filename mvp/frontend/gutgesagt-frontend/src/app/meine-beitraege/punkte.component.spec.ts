import { ComponentFixture, TestBed, discardPeriodicTasks, fakeAsync, tick } from '@angular/core/testing';
import { of } from 'rxjs';

import { PUNKTE_NACHLADEN_MS, PunkteComponent } from './punkte.component';
import { Punktestand, UsageTrackingService } from '../services/usage-tracking.service';

describe('PunkteComponent (#352)', () => {
  let fixture: ComponentFixture<PunkteComponent>;
  let holen: jasmine.Spy<() => ReturnType<UsageTrackingService['getEigenePunkte']>>;
  let sichtbarkeit: DocumentVisibilityState;

  function stand(felder: Partial<Punktestand> = {}): Punktestand {
    return { tun: 2, quests: 0, wirkung: 30, gesamt: 32, ...felder };
  }

  function erstellen(...antworten: (Punktestand | null)[]): HTMLElement {
    holen = jasmine.createSpy('getEigenePunkte').and.returnValues(...antworten.map((a) => of(a)));
    TestBed.configureTestingModule({
      imports: [PunkteComponent],
      providers: [{ provide: UsageTrackingService, useValue: { getEigenePunkte: holen } }],
    });
    fixture = TestBed.createComponent(PunkteComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => {
    sichtbarkeit = 'visible';
    spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);
  });

  afterEach(() => fixture?.destroy());

  it('zeigt nichts bei ausgeschalteten Punkten oder einem Fehler', () => {
    const element = erstellen(null);

    expect(element.querySelector('.punkte')).toBeNull();
  });

  it('zeigt den Stand gesamt und je Stufe und sagt, dass nur die Person ihn sieht', () => {
    const element = erstellen(stand());

    expect(element.querySelector('h2')?.textContent).toContain('32');
    expect(element.querySelector('[data-stufe="wirkung"]')?.textContent).toContain('30');
    expect(element.querySelector('[data-stufe="tun"]')?.textContent).toContain('2');
    expect(element.querySelector('.punkte-hinweis')?.textContent).toContain('Nur du siehst deine Punkte');
  });

  it('zeigt Quests erst, wenn sie etwas bringen', () => {
    expect(erstellen(stand()).querySelector('[data-stufe="quests"]')).toBeNull();
    fixture.destroy();
    TestBed.resetTestingModule();

    const element = erstellen(stand({ quests: 4, gesamt: 36 }));
    expect(element.querySelector('[data-stufe="quests"]')?.textContent).toContain('4');
  });

  it('zeigt auch 0 Punkte (neu, Startkonto, ohne Einwilligung)', () => {
    const element = erstellen(stand({ tun: 0, wirkung: 0, gesamt: 0 }));

    expect(element.querySelector('h2')?.textContent).toContain('0');
  });

  it('lädt beim Zurückkehren in den Tab nach', () => {
    const element = erstellen(stand(), stand({ wirkung: 40, gesamt: 42 }));

    document.dispatchEvent(new Event('visibilitychange'));
    fixture.detectChanges();

    expect(holen).toHaveBeenCalledTimes(2);
    expect(element.querySelector('h2')?.textContent).toContain('42');
  });

  it('lädt nicht nach, wenn der Tab verborgen wird', () => {
    erstellen(stand());

    sichtbarkeit = 'hidden';
    document.dispatchEvent(new Event('visibilitychange'));

    expect(holen).toHaveBeenCalledTimes(1);
  });

  it('lädt in Abständen nach, aber nur solange die Seite sichtbar ist', fakeAsync(() => {
    const element = erstellen(stand(), stand({ wirkung: 50, gesamt: 52 }), stand());

    tick(PUNKTE_NACHLADEN_MS);
    fixture.detectChanges();
    expect(holen).toHaveBeenCalledTimes(2);
    expect(element.querySelector('h2')?.textContent).toContain('52');

    sichtbarkeit = 'hidden';
    tick(PUNKTE_NACHLADEN_MS * 3);
    expect(holen).toHaveBeenCalledTimes(2);

    fixture.destroy();
    discardPeriodicTasks();
  }));
});
