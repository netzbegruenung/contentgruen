import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Observable, of } from 'rxjs';

import { MeilensteineComponent } from './meilensteine.component';
import { AbzeichenSichtbarkeit, Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';

describe('MeilensteineComponent (#351)', () => {
  let fixture: ComponentFixture<MeilensteineComponent>;
  let speichern: jasmine.Spy<(zeigen: boolean, wortlaut: string) => Observable<boolean>>;

  function meilenstein(felder: Partial<Meilenstein>): Meilenstein {
    return { kennung: 'nutzung-1', name: 'Erste Nutzung durch andere', art: 'wirkung', schwelle: 1, stand: 0, erreicht: false, ...felder };
  }

  function erstellen(meilensteine: Meilenstein[], sichtbarkeit: AbzeichenSichtbarkeit | null = null): HTMLElement {
    speichern = jasmine.createSpy('speichern').and.returnValue(of(true));
    TestBed.configureTestingModule({
      imports: [MeilensteineComponent],
      providers: [
        {
          provide: UsageTrackingService,
          useValue: {
            getEigeneMeilensteine: () => of(meilensteine),
            getAbzeichenSichtbarkeit: () => of(sichtbarkeit),
            setAbzeichenSichtbarkeit: speichern,
          },
        },
      ],
    });
    fixture = TestBed.createComponent(MeilensteineComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('zeigt nichts ohne Meilensteine (Punkte aus, Startkonto, keine Einwilligung)', () => {
    const element = erstellen([]);

    expect(element.querySelector('.meilensteine')).toBeNull();
  });

  it('zeigt erreichte als Abzeichen und offene mit Stand', () => {
    const element = erstellen([
      meilenstein({ stand: 3, erreicht: true }),
      meilenstein({ kennung: 'nutzung-10', name: '10 Nutzungen', schwelle: 10, stand: 3 }),
    ]);

    const eintraege = Array.from(element.querySelectorAll('.meilenstein'));
    expect(eintraege.length).toBe(2);
    expect(eintraege[0].classList).toContain('erreicht');
    expect(eintraege[0].textContent).toContain('Erste Nutzung durch andere');
    expect(eintraege[0].querySelector('.meilenstein-stand')).toBeNull();
    expect(eintraege[1].classList).not.toContain('erreicht');
    expect(eintraege[1].querySelector('.meilenstein-stand')?.textContent).toContain('3/10');
    expect(element.querySelector('h2')?.textContent).toContain('1 von 2');
  });

  it('sagt, dass nur die Person selbst sie sieht', () => {
    const element = erstellen([meilenstein({})]);

    expect(element.textContent).toContain('Nur du siehst deine Meilensteine.');
  });

  it('nennt den Zustand auch Screenreadern', () => {
    const element = erstellen([meilenstein({ erreicht: true, stand: 1 }), meilenstein({ kennung: 'x', schwelle: 10, stand: 2 })]);

    const versteckt = Array.from(element.querySelectorAll('.visually-hidden')).map((e) => e.textContent?.trim());
    expect(versteckt).toEqual([', erreicht', ', noch nicht erreicht: 2 von 10']);
  });

  describe('Zustimmung zur Sichtbarkeit', () => {
    const WORTLAUT = { kennung: '2026-11-09', text: 'Sollen andere Angemeldete an deinem Namen sehen …?' };
    const NIE_GEFRAGT: AbzeichenSichtbarkeit = { gefragt: false, zeigen: null, aktueller_wortlaut: WORTLAUT };

    function knopf(element: HTMLElement, text: string): HTMLButtonElement {
      const treffer = Array.from(element.querySelectorAll('button')).find((b) => b.textContent?.includes(text));
      expect(treffer).withContext(text).toBeDefined();
      return treffer as HTMLButtonElement;
    }

    it('fragt ab dem ersten erreichten Meilenstein mit zwei gleichwertigen Knöpfen', () => {
      const element = erstellen([meilenstein({ erreicht: true, stand: 1 })], NIE_GEFRAGT);

      const frage = element.querySelector('.sichtbarkeit-frage');
      expect(frage?.textContent).toContain(WORTLAUT.text);
      const knoepfe = Array.from(frage!.querySelectorAll('button'));
      expect(knoepfe.map((b) => b.textContent?.trim())).toEqual(['Ja, zeigen', 'Nein, nur für mich']);
      expect(knoepfe[0].className).toEqual(knoepfe[1].className);
    });

    it('fragt nicht, solange kein Meilenstein erreicht ist', () => {
      const element = erstellen([meilenstein({})], NIE_GEFRAGT);

      expect(element.querySelector('.sichtbarkeit-frage')).toBeNull();
    });

    it('fragt nicht ohne Schalter (Server ohne Sichtbarkeit)', () => {
      const element = erstellen([meilenstein({ erreicht: true, stand: 1 })], null);

      expect(element.querySelector('.sichtbarkeit-frage')).toBeNull();
      expect(element.textContent).toContain('Nur du siehst deine Meilensteine.');
    });

    it('speichert ein Ja mit dem Wortlaut und sagt danach, wer es sieht', () => {
      const element = erstellen([meilenstein({ erreicht: true, stand: 1 })], NIE_GEFRAGT);

      knopf(element, 'Ja, zeigen').click();
      fixture.detectChanges();

      expect(speichern).toHaveBeenCalledWith(true, '2026-11-09');
      expect(element.querySelector('.sichtbarkeit-frage')).toBeNull();
      expect(element.textContent).toContain('Andere Angemeldete sehen an deinem Namen');
      expect(element.querySelector('.sichtbarkeit-stand')?.textContent).toContain('für Angemeldete sichtbar');
    });

    it('nimmt mit einem Klick zurück', () => {
      const element = erstellen([meilenstein({ erreicht: true, stand: 1 })], { ...NIE_GEFRAGT, gefragt: true, zeigen: true });

      knopf(element, 'Nicht mehr zeigen').click();
      fixture.detectChanges();

      expect(speichern).toHaveBeenCalledWith(false, '2026-11-09');
      expect(element.textContent).toContain('Nur du siehst deine Meilensteine.');
    });

    it('zeigt vor einer späteren Zustimmung den Wortlaut noch einmal', () => {
      const element = erstellen([meilenstein({ erreicht: true, stand: 1 })], { ...NIE_GEFRAGT, gefragt: true, zeigen: false });

      knopf(element, 'Anderen zeigen').click();
      fixture.detectChanges();

      expect(speichern).not.toHaveBeenCalled();
      expect(element.querySelector('.sichtbarkeit-frage')?.textContent).toContain(WORTLAUT.text);
    });

    it('setzt nach der Antwort den Fokus auf "Nicht mehr zeigen" und sagt den Stand an', () => {
      const element = erstellen([meilenstein({ erreicht: true, stand: 1 })], NIE_GEFRAGT);
      document.body.appendChild(element);

      knopf(element, 'Ja, zeigen').click();
      fixture.detectChanges();

      expect(document.activeElement?.textContent).toContain('Nicht mehr zeigen');
      expect(element.querySelector('[role="status"]')?.textContent).toContain('für Angemeldete sichtbar');
      element.remove();
    });

    it('meldet einen Fehler und bleibt bei der alten Antwort', () => {
      const element = erstellen([meilenstein({ erreicht: true, stand: 1 })], NIE_GEFRAGT);
      speichern.and.returnValue(of(false));

      knopf(element, 'Ja, zeigen').click();
      fixture.detectChanges();

      expect(element.querySelector('.sichtbarkeit-fehler')).not.toBeNull();
      expect(element.querySelector('.sichtbarkeit-frage')).not.toBeNull();
    });
  });
});
