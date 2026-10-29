import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';

import { SiegelComponent } from './siegel.component';
import { HAND, SCHATTEN } from '../../marke/hand';

/**
 * Das Siegel zeigt die Güte eines Beitrags (#416, auf Karten #427): ohne Güte grau
 * und waagrecht, mit steigender Güte dreht der Daumen nach oben und die Farbe läuft
 * von Grau über Gelb nach Grün. Nie nach unten, nie rot.
 */
describe('SiegelComponent', () => {
  let fixture: ComponentFixture<SiegelComponent>;

  function zeige(guete: number | null, extras: { glanz?: boolean; krone?: boolean } = {}): HTMLElement {
    fixture.componentRef.setInput('guete', guete);
    if (extras.glanz !== undefined) fixture.componentRef.setInput('glanz', extras.glanz);
    if (extras.krone !== undefined) fixture.componentRef.setInput('krone', extras.krone);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function svg(): SVGElement {
    return (fixture.nativeElement as HTMLElement).querySelector('svg')!;
  }

  /** Drehung der Hand in Grad, aus dem gerenderten Stil gelesen. */
  function winkel(): number {
    const hand = (fixture.nativeElement as HTMLElement).querySelector<SVGGElement>('.siegel-hand')!;
    const treffer = /rotate\((-?[\d.]+)deg\)/.exec(hand.style.transform);
    return Number(treffer![1]);
  }

  /** Farbe der Blase als [Farbton, Sättigung, Helligkeit]. */
  function farbe(): [number, number, number] {
    const blase = (fixture.nativeElement as HTMLElement).querySelector('.siegel-blase-gruppe')!;
    const treffer = /hsl\(([\d.]+) ([\d.]+)% ([\d.]+)%\)/.exec(blase.getAttribute('fill')!);
    return [Number(treffer![1]), Number(treffer![2]), Number(treffer![3])];
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [SiegelComponent] }).compileComponents();
    fixture = TestBed.createComponent(SiegelComponent);
  });

  it('zeigt einen neuen Beitrag ohne Güte grau und waagrecht', () => {
    zeige(null);

    expect(svg().getAttribute('role')).toBe('img');
    expect(svg().getAttribute('aria-label')).toBe('Siegel: neu, noch keine Güte');
    expect(winkel()).toBe(90);
    const [, saettigung] = farbe();
    expect(saettigung).toBeLessThan(15);
  });

  it('zeigt Güte 10 grün und senkrecht', () => {
    zeige(10);

    expect(svg().getAttribute('aria-label')).toBe('Siegel: Güte 10 von 10');
    expect(winkel()).toBe(0);
    const [farbton, saettigung] = farbe();
    expect(farbton).toBeGreaterThan(120);
    expect(farbton).toBeLessThan(160);
    expect(saettigung).toBeGreaterThan(80);
  });

  it('dreht den Daumen je Punkt Güte um 9 Grad nach oben, nie nach unten', () => {
    const erwartet = [81, 72, 63, 54, 45, 36, 27, 18, 9, 0];
    const gesehen = erwartet.map((_, i) => {
      zeige(i + 1);
      return winkel();
    });
    expect(gesehen).toEqual(erwartet);
  });

  it('wird nie rot: gesättigte Farben liegen zwischen Gelb und Grün', () => {
    for (const guete of [null, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) {
      zeige(guete);
      const [farbton, saettigung] = farbe();
      if (saettigung >= 15) {
        expect(farbton).withContext(`Güte ${guete}`).toBeGreaterThanOrEqual(40);
        expect(farbton).withContext(`Güte ${guete}`).toBeLessThanOrEqual(150);
      }
    }
  });

  it('läuft von Grau über Gelb nach Grün', () => {
    zeige(1);
    const [, saettigungNiedrig] = farbe();
    zeige(4);
    const [farbtonMitte] = farbe();
    zeige(10);
    const [farbtonHoch] = farbe();

    expect(saettigungNiedrig).toBeLessThan(40);
    expect(farbtonMitte).toBeLessThan(60); // Gelb
    expect(farbtonHoch).toBeGreaterThan(120); // Grün
  });

  it('begrenzt eine Güte über 10 auf 10', () => {
    zeige(14);
    expect(svg().getAttribute('aria-label')).toBe('Siegel: Güte 10 von 10');
    expect(winkel()).toBe(0);
  });

  it('zeigt Güte 0 und darunter als neu, grau und waagrecht', () => {
    for (const guete of [0, -3]) {
      zeige(guete);
      expect(svg().getAttribute('aria-label')).withContext(`Güte ${guete}`).toBe('Siegel: neu, noch keine Güte');
      expect(winkel()).withContext(`Güte ${guete}`).toBe(90);
    }
  });

  it('zeigt Glanz und Krone nur, wenn sie gesetzt sind', () => {
    const el = zeige(7);
    expect(el.querySelector('.siegel-glanz')).toBeNull();
    expect(el.querySelector('.siegel-krone')).toBeNull();

    zeige(7, { glanz: true, krone: true });
    expect(el.querySelector('.siegel-glanz')).not.toBeNull();
    expect(el.querySelector('.siegel-krone')).not.toBeNull();
  });

  it('gibt jedem Siegel einen eigenen Glanz-Verlauf, damit mehrere auf einer Seite stehen können', () => {
    zeige(7, { glanz: true });
    const zweites = TestBed.createComponent(SiegelComponent);
    zweites.componentRef.setInput('glanz', true);
    zweites.detectChanges();

    const id1 = (fixture.nativeElement as HTMLElement).querySelector('linearGradient')!.id;
    const id2 = (zweites.nativeElement as HTMLElement).querySelector('linearGradient')!.id;
    expect(id1).not.toBe(id2);
    const fuellung = (fixture.nativeElement as HTMLElement).querySelector('.siegel-glanz > g')!.getAttribute('fill');
    expect(fuellung).toBe(`url(#${id1})`);
  });

  describe('Aufstieg', () => {
    function funken(): number {
      return (fixture.nativeElement as HTMLElement).querySelectorAll('.siegel-funke').length;
    }

    it('lässt Funken sprühen, wenn die Güte steigt, und räumt sie wieder weg', fakeAsync(() => {
      zeige(5);
      expect(funken()).toBe(0);

      zeige(6);
      expect(funken()).toBeGreaterThan(0);

      tick(1000);
      fixture.detectChanges();
      expect(funken()).toBe(0);
    }));

    it('funkelt auch beim ersten Datenpunkt eines neuen Beitrags', fakeAsync(() => {
      zeige(null);
      zeige(3);
      expect(funken()).toBeGreaterThan(0);
      tick(1000);
    }));

    it('funkelt nicht, wenn die Güte sinkt', () => {
      zeige(6);
      zeige(5);
      expect(funken()).toBe(0);
    });

    it('funkelt nicht bei prefers-reduced-motion, wechselt aber Winkel und Farbe', () => {
      spyOn(window, 'matchMedia').and.callFake(
        (anfrage: string) => ({ matches: anfrage.includes('reduce') }) as MediaQueryList,
      );
      zeige(5);
      zeige(6);

      expect(funken()).toBe(0);
      expect(winkel()).toBe(36);
    });
  });

  it('teilt die Zeichnung mit dem Logo, das als Datei ausgeliefert wird', async () => {
    const antwort = await fetch('/marke/logo.svg');
    expect(antwort.ok).withContext('logo.svg ausgeliefert').toBeTrue();
    const logo = await antwort.text();

    expect(logo).toContain(`d="${HAND}"`);
    expect(logo).toContain(`d="${SCHATTEN}"`);
    // Die Blase wie im Siegel
    expect(logo).toContain('<rect x="4" y="16" width="44" height="38" rx="11"/>');
    expect(logo).toContain('<path d="M11 51 L8 63 L24 53 Z"/>');
    expect(logo).toContain('Fluent Emoji');
  });
});
