import { ComponentFixture, TestBed, fakeAsync, flush, tick } from '@angular/core/testing';
import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
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

/** Ein Suchfeld wie app-search: OnPush, Wert über ngModel. */
@Component({
  selector: 'app-probe-suche',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div id="probe-feld" style="position:absolute;left:40px;top:300px;width:200px;height:40px">
    <input [(ngModel)]="suche" name="suche"></div>`,
})
class ProbeSucheComponent {
  suche = '';
}

/** Ein Schritt, der ein Beispiel in das Feld im Ziel schreibt. */
const MIT_BEISPIEL: Rundgang = {
  id: 'antwort-finden',
  name: 'Rundgang mit Beispiel',
  schritte: [{ titel: 'Eingeben', text: 'Mit Beispiel', ziel: '#probe-feld', vorbelegen: 'Ein Beispiel' }],
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
      <div id="probe-zwei" style="position:absolute;left:300px;top:200px;width:120px;height:30px">zwei</div>
      <div id="probe-feld" style="position:absolute;left:40px;top:300px;width:200px;height:40px"><input></div>`;
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
      expect(b.getAttribute('aria-label')).toBe('Rundgang Probe, Schritt 1 von 3: Erster');
      expect(document.getElementById(b.getAttribute('aria-describedby')!)?.textContent).toContain('Text eins');
      // nicht doppelt: Den Schritt sagt der Fokus auf der Blase, die Live-Region schweigt
      expect(fixture.nativeElement.querySelector('[aria-live]').textContent.trim()).toBe('');
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

    it('füllt ein leeres Eingabefeld im Ziel mit dem Beispiel, wie beim Tippen (#601)', fakeAsync(() => {
      const feld = seite.querySelector('#probe-feld input') as HTMLInputElement;
      const getippt = jasmine.createSpy('input');
      feld.addEventListener('input', getippt);
      service.aktiv.set({ rundgang: MIT_BEISPIEL, index: 0 });
      fixture.detectChanges();
      tick();
      expect(feld.value).toBe('Ein Beispiel');
      expect(getippt).toHaveBeenCalledTimes(1);
      flush();
    }));

    it('übergibt das Beispiel an ngModel eines OnPush-Suchfelds, auch direkt nach dem Laden', fakeAsync(() => {
      seite.querySelector('#probe-feld')!.remove();
      const suche = TestBed.createComponent(ProbeSucheComponent);
      document.body.appendChild(suche.nativeElement);
      // Rundgang startet, bevor das Feld seine erste Änderungserkennung hatte
      service.aktiv.set({ rundgang: MIT_BEISPIEL, index: 0 });
      fixture.detectChanges();
      suche.detectChanges();
      tick();
      suche.detectChanges();
      tick();
      const feld = suche.nativeElement.querySelector('input') as HTMLInputElement;
      expect(suche.componentInstance.suche).toBe('Ein Beispiel');
      expect(feld.value).toBe('Ein Beispiel');
      suche.nativeElement.remove();
      flush();
    }));

    it('lässt stehen, was schon im Eingabefeld steht', fakeAsync(() => {
      const feld = seite.querySelector('#probe-feld input') as HTMLInputElement;
      feld.value = 'Eigener Text';
      service.aktiv.set({ rundgang: MIT_BEISPIEL, index: 0 });
      fixture.detectChanges();
      tick();
      expect(feld.value).toBe('Eigener Text');
      flush();
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

    it('gibt den Fokus an den Hilfe-Knopf, wenn der Ausgangspunkt weg ist (Start aus der Hilfe)', fakeAsync(() => {
      const hilfe = document.createElement('button');
      hilfe.className = 'hilfe-knopf';
      seite.appendChild(hilfe);
      ausloeser.focus();
      starten();
      ausloeser.remove();
      taste('Escape', blase()!);
      tick();
      fixture.detectChanges();
      expect(document.activeElement).toBe(hilfe);
      flush();
    }));

    it('vergisst den Ausgangspunkt, wenn schon beim Suchen des ersten Ziels beendet wird', fakeAsync(() => {
      ausloeser.focus();
      starten(2); // Ziel fehlt, der Schritt wartet noch
      service.aktiv.set(null);
      fixture.detectChanges();
      tick(ZIEL_WARTEZEIT_MS);
      const anderer = document.createElement('button');
      seite.appendChild(anderer);
      anderer.focus();
      starten();
      taste('Escape', blase()!);
      tick();
      fixture.detectChanges();
      expect(document.activeElement).toBe(anderer);
      flush(200);
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
