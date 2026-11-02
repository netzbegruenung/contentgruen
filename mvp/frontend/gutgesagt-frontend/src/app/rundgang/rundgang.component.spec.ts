import { ComponentFixture, TestBed, fakeAsync, flush, tick } from '@angular/core/testing';
import { signal } from '@angular/core';
import { RundgangComponent, ZIEL_WARTEZEIT_MS } from './rundgang.component';
import { RundgangService, RundgangStand } from './rundgang.service';
import { Rundgang } from './rundgang-daten';

/** Ein Rundgang über zwei Elemente, die der Test selbst auf die Seite legt. */
const PROBE: Rundgang = {
  id: 'antwort-finden',
  name: 'Rundgang Probe',
  schritte: [
    { titel: 'Erster', text: 'Text eins', ziel: '#probe-eins' },
    { titel: 'Zweiter', text: { desktop: 'Text breit', mobil: 'Text schmal' }, ziel: '#probe-fehlt, #probe-zwei' },
    { titel: 'Dritter', text: 'Ohne Ziel', ziel: '#gibt-es-nicht' },
  ],
};

class FakeRundgangService {
  readonly aktiv = signal<RundgangStand | null>(null);
  weiter = jasmine.createSpy('weiter').and.callFake(() => {
    const s = this.aktiv();
    if (!s) return;
    this.aktiv.set(s.index < s.rundgang.schritte.length - 1 ? { ...s, index: s.index + 1 } : null);
  });
  zurueck = jasmine.createSpy('zurueck').and.callFake(() => {
    const s = this.aktiv();
    if (s && s.index > 0) this.aktiv.set({ ...s, index: s.index - 1 });
  });
  beenden = jasmine.createSpy('beenden').and.callFake(() => this.aktiv.set(null));
}

function matchMediaMit(treffer: Record<string, boolean>): void {
  const echt = window.matchMedia.bind(window);
  spyOn(window, 'matchMedia').and.callFake(
    (q: string) => (q in treffer ? ({ matches: treffer[q], media: q } as MediaQueryList) : echt(q)),
  );
}

describe('RundgangComponent', () => {
  let fixture: ComponentFixture<RundgangComponent>;
  let service: FakeRundgangService;
  let seite: HTMLElement;
  let ausloeser: HTMLButtonElement;

  function aufbauen(): void {
    TestBed.configureTestingModule({
      imports: [RundgangComponent],
      providers: [{ provide: RundgangService, useClass: FakeRundgangService }],
    });
    service = TestBed.inject(RundgangService) as unknown as FakeRundgangService;
    fixture = TestBed.createComponent(RundgangComponent);
    document.body.appendChild(fixture.nativeElement);
    fixture.detectChanges();
  }

  beforeEach(() => {
    seite = document.createElement('div');
    seite.innerHTML = `
      <button id="ausloeser">Hilfe</button>
      <div id="probe-eins" style="position:absolute;left:40px;top:60px;width:200px;height:40px">eins</div>
      <div id="probe-zwei" style="position:absolute;left:300px;top:200px;width:120px;height:30px">zwei</div>`;
    document.body.appendChild(seite);
    ausloeser = seite.querySelector('#ausloeser') as HTMLButtonElement;
  });

  afterEach(() => {
    seite.remove();
    fixture?.nativeElement.remove();
  });

  function starten(index = 0): void {
    service.aktiv.set({ rundgang: PROBE, index });
    fixture.detectChanges();
    tick();
  }

  const blase = () => fixture.nativeElement.querySelector('.blase') as HTMLElement | null;
  const kegel = () => fixture.nativeElement.querySelector('.kegel') as HTMLElement | null;
  const taste = (key: string, ziel: EventTarget = document.activeElement ?? document) =>
    ziel.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));

  describe('Darstellung', () => {
    beforeEach(() => {
      matchMediaMit({ '(max-width: 599px)': false, '(max-width: 959px)': false, '(prefers-reduced-motion: reduce)': false });
      aufbauen();
    });

    it('zeigt nichts, solange kein Rundgang läuft', () => {
      expect(blase()).toBeNull();
    });

    it('hebt das Ziel mit dem Lichtkegel hervor und zeigt Titel, Text und Fortschritt', fakeAsync(() => {
      starten();
      expect(blase()?.querySelector('h3')?.textContent).toContain('Erster');
      expect(blase()?.textContent).toContain('Text eins');
      expect(blase()?.textContent).toContain('Schritt 1 von 3');
      const r = (seite.querySelector('#probe-eins') as HTMLElement).getBoundingClientRect();
      const k = kegel()!.getBoundingClientRect();
      expect(k.left).toBeCloseTo(r.left - 8, 0);
      expect(k.width).toBeCloseTo(r.width + 16, 0);
      flush();
    }));

    it('ist ein modaler Dialog mit Namen und Beschreibung für Screenreader', fakeAsync(() => {
      starten();
      const b = blase()!;
      expect(b.getAttribute('role')).toBe('dialog');
      expect(b.getAttribute('aria-modal')).toBe('true');
      expect(b.getAttribute('aria-label')).toBe('Rundgang Probe: Erster');
      expect(document.getElementById(b.getAttribute('aria-describedby')!)?.textContent).toContain('Text eins');
      expect(fixture.nativeElement.querySelector('[aria-live]').textContent).toContain('Schritt 1 von 3: Erster');
      flush();
    }));

    it('nimmt bei mehreren Selektoren das erste sichtbare Ziel und den Desktop-Text', fakeAsync(() => {
      starten(1);
      const r = (seite.querySelector('#probe-zwei') as HTMLElement).getBoundingClientRect();
      expect(kegel()!.getBoundingClientRect().top).toBeCloseTo(r.top - 8, 0);
      expect(blase()?.textContent).toContain('Text breit');
      flush();
    }));

    it('zeigt den Schritt ohne Lichtkegel, wenn das Ziel nicht erscheint', fakeAsync(() => {
      starten(2);
      expect(blase()).toBeNull();
      tick(ZIEL_WARTEZEIT_MS);
      fixture.detectChanges();
      expect(blase()?.textContent).toContain('Ohne Ziel');
      expect(kegel()).toBeNull();
      expect(fixture.nativeElement.querySelector('.schleier')).not.toBeNull();
      flush(200); // sucht das fehlende Ziel noch eine Weile nach
    }));

    it('beschriftet den letzten Schritt mit „Fertig“, den ersten ohne „Zurück“', fakeAsync(() => {
      starten();
      expect(blase()?.querySelector('.zurueck')).toBeNull();
      expect(blase()?.querySelector('.weiter')?.textContent?.trim()).toBe('Weiter');
      service.aktiv.set({ rundgang: PROBE, index: 2 });
      fixture.detectChanges();
      tick(ZIEL_WARTEZEIT_MS);
      fixture.detectChanges();
      expect(blase()?.querySelector('.weiter')?.textContent?.trim()).toBe('Fertig');
      expect(blase()?.querySelector('.zurueck')).not.toBeNull();
      flush(200);
    }));
  });

  describe('Tastatur und Fokus', () => {
    beforeEach(() => {
      matchMediaMit({ '(max-width: 599px)': false, '(max-width: 959px)': false, '(prefers-reduced-motion: reduce)': false });
      aufbauen();
    });

    it('setzt den Fokus in die Sprechblase', fakeAsync(() => {
      ausloeser.focus();
      starten();
      expect(document.activeElement).toBe(blase());
      flush();
    }));

    it('fängt den Fokus in der Sprechblase (Fokusfalle mit Ankern davor und danach)', fakeAsync(() => {
      starten();
      const b = blase()!;
      const vor = b.previousElementSibling;
      const nach = b.nextElementSibling;
      expect(vor?.classList).toContain('cdk-focus-trap-anchor');
      expect(nach?.classList).toContain('cdk-focus-trap-anchor');
      // Der Anker hinter der Blase führt zurück auf den ersten Knopf darin
      (nach as HTMLElement).focus();
      expect(b.contains(document.activeElement)).toBeTrue();
      flush();
    }));

    it('blättert mit den Pfeiltasten', fakeAsync(() => {
      starten();
      taste('ArrowRight', blase()!);
      expect(service.weiter).toHaveBeenCalled();
      tick();
      fixture.detectChanges();
      taste('ArrowLeft', blase()!);
      expect(service.zurueck).toHaveBeenCalled();
      flush();
    }));

    it('beendet mit Escape und gibt den Fokus zurück', fakeAsync(() => {
      ausloeser.focus();
      starten();
      taste('Escape', blase()!);
      expect(service.beenden).toHaveBeenCalled();
      tick();
      fixture.detectChanges();
      expect(blase()).toBeNull();
      expect(document.activeElement).toBe(ausloeser);
      expect(fixture.nativeElement.querySelector('[aria-live]').textContent).toContain('Rundgang beendet');
      flush();
    }));

    it('bricht mit „Beenden“ in jedem Schritt ab', fakeAsync(() => {
      starten(1);
      (blase()!.querySelector('.beenden') as HTMLButtonElement).click();
      tick();
      fixture.detectChanges();
      expect(service.beenden).toHaveBeenCalled();
      expect(blase()).toBeNull();
      flush();
    }));

    it('sperrt die Seite darunter', fakeAsync(() => {
      starten();
      const sperre = fixture.nativeElement.querySelector('.sperre') as HTMLElement;
      expect(getComputedStyle(sperre).position).toBe('fixed');
      const r = (seite.querySelector('#probe-eins') as HTMLElement).getBoundingClientRect();
      const oben = document.elementFromPoint(r.left + 5, r.top + 5);
      expect(seite.contains(oben)).toBeFalse();
      flush();
    }));
  });

  describe('mobil', () => {
    beforeEach(() => {
      matchMediaMit({ '(max-width: 599px)': true, '(max-width: 959px)': true, '(prefers-reduced-motion: reduce)': false });
      aufbauen();
    });

    it('stellt die Sprechblase als Karte an den unteren Rand und nimmt den mobilen Text', fakeAsync(() => {
      starten(1);
      const b = blase()!;
      expect(fixture.nativeElement.classList).toContain('schmal');
      // Gemessen am Stil: Die Einblende-Animation verschiebt das Rechteck noch
      const stil = getComputedStyle(b);
      expect(stil.position).toBe('fixed');
      expect(stil.bottom).toBe('12px');
      expect(stil.left).toBe('12px');
      expect(stil.right).toBe('12px');
      expect(b.querySelector('.pfeil')).toBeNull();
      expect(b.textContent).toContain('Text schmal');
      flush();
    }));
  });

  describe('weniger Bewegung', () => {
    beforeEach(() => {
      matchMediaMit({ '(max-width: 599px)': false, '(max-width: 959px)': false, '(prefers-reduced-motion: reduce)': true });
      aufbauen();
    });

    it('lässt Kegel und Sprechblase ohne Animation erscheinen', fakeAsync(() => {
      starten();
      expect(fixture.nativeElement.classList).toContain('ruhig');
      expect(getComputedStyle(kegel()!).transitionDuration).toBe('0s');
      expect(getComputedStyle(blase()!).animationName).toBe('none');
      flush();
    }));
  });
});
