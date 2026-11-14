import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';

import { SiegelComponent } from './siegel.component';
import { HAND, SCHATTEN } from '../../marke/hand';
import { aufgeloest, themaFarbe } from '../../../testing/farben';
import { FarbschemaService } from '../../../services/farbschema.service';

/** Tannengrün der Seite (`--primary-dark` in `custom-theme.scss`), gelesen aus dem geladenen Theme. */
function tannengruen(): string {
  return themaFarbe('--primary-dark').toLowerCase();
}

/**
 * Das Siegel zeigt die Güte eines Beitrags (#416, auf Karten #427): ohne Güte grau
 * und waagrecht, mit steigender Güte dreht der Daumen nach oben und die Farbe läuft
 * von Grau über Gelb nach Tannengrün. Nie nach unten, nie rot. Glanz ist ein eigenes
 * Abzeichen, keine Stufe der Güte; eine Krone gibt es nicht mehr.
 */
describe('SiegelComponent', () => {
  let fixture: ComponentFixture<SiegelComponent>;

  function zeige(guete: number | null, extras: { glanz?: boolean } = {}): HTMLElement {
    fixture.componentRef.setInput('guete', guete);
    if (extras.glanz !== undefined) fixture.componentRef.setInput('glanz', extras.glanz);
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

  it('zeigt Güte 10 im Tannengrün der Seite und senkrecht', () => {
    zeige(10);

    expect(svg().getAttribute('aria-label')).toBe('Siegel: Güte 10 von 10');
    expect(winkel()).toBe(0);
    expect(tannengruen()).toBe('#005437');
    const blase = (fixture.nativeElement as HTMLElement).querySelector('.siegel-blase-gruppe')!;
    expect(aufgeloest(blase.getAttribute('fill')!)).toBe(aufgeloest(tannengruen()));
  });

  it('dreht den Daumen je Punkt Güte um 9 Grad nach oben, nie nach unten', () => {
    const erwartet = [81, 72, 63, 54, 45, 36, 27, 18, 9, 0];
    const gesehen = erwartet.map((_, i) => {
      zeige(i + 1);
      return winkel();
    });
    expect(gesehen).toEqual(erwartet);
  });

  it('wird nie rot: gesättigte Farben liegen zwischen Gelb und Tannengrün', () => {
    for (const guete of [null, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) {
      zeige(guete);
      const [farbton, saettigung] = farbe();
      if (saettigung >= 15) {
        expect(farbton).withContext(`Güte ${guete}`).toBeGreaterThanOrEqual(40);
        expect(farbton).withContext(`Güte ${guete}`).toBeLessThanOrEqual(160);
      }
    }
  });

  it('läuft von Grau über Gelb nach Tannengrün', () => {
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

  it('laesst den Farbton nur in eine Richtung laufen, ohne Umweg ueber Orange (Ersteindruck-Test 14.11.)', () => {
    const farbtoene = [null, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((guete) => {
      zeige(guete);
      return farbe()[0];
    });
    for (let i = 1; i < farbtoene.length; i++) {
      expect(farbtoene[i]).withContext(`Güte ${i}`).toBeGreaterThanOrEqual(farbtoene[i - 1]);
    }
    expect(Math.min(...farbtoene)).toBeGreaterThanOrEqual(50); // kein Orange
  });

  it('gibt der Blase im Hellen einen dunkleren Rand im selben Farbton, im Dunkeln keinen', () => {
    const blase = () => (fixture.nativeElement as HTMLElement).querySelector('.siegel-blase-gruppe')!;
    zeige(4);
    const [farbton] = farbe();
    const rand = /hsl\(([\d.]+) ([\d.]+)% ([\d.]+)%\)/.exec(blase().getAttribute('stroke')!)!;
    expect(Number(rand[1])).toBe(farbton);
    expect(Number(rand[3])).toBeLessThan(farbe()[2]);

    spyOn(TestBed.inject(FarbschemaService), 'dunkel').and.returnValue(true);
    fixture = TestBed.createComponent(SiegelComponent);
    zeige(4);
    expect(blase().getAttribute('stroke')).toBe('none');
  });

  it('endet im Dunkelmodus in Klee, damit das Siegel sich vom dunklen Grund abhebt (#588)', () => {
    spyOn(TestBed.inject(FarbschemaService), 'dunkel').and.returnValue(true);
    fixture = TestBed.createComponent(SiegelComponent);

    zeige(10);

    const blase = (fixture.nativeElement as HTMLElement).querySelector('.siegel-blase-gruppe')!;
    expect(aufgeloest(blase.getAttribute('fill')!)).toBe(aufgeloest('#008939'));
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

  it('zeigt den Glanz nur, wenn er gesetzt ist', () => {
    const el = zeige(7);
    expect(el.querySelector('.siegel-glanz')).toBeNull();
    expect(el.querySelector('.siegel-sterne')).toBeNull();

    zeige(7, { glanz: true });
    expect(el.querySelector('.siegel-glanz')).not.toBeNull();
    // Ein grosser Stern und zwei kleine Funken (Ersteindruck-Test 14.11.)
    expect(el.querySelectorAll('.siegel-sterne .siegel-stern').length).toBe(1);
    expect(el.querySelectorAll('.siegel-sterne .siegel-funkler').length).toBe(2);
  });

  it('zeichnet keine Krone mehr: Sie beschrieb die Person, nicht den Beitrag (14.11.)', () => {
    const el = zeige(10, { glanz: true });
    expect(el.querySelector('.siegel-krone')).toBeNull();
    expect(svg().getAttribute('aria-label')).toBe('Siegel: Güte 10 von 10, mit Glanz');
  });

  it('zeigt den Glanz bei jeder Güte', () => {
    for (const guete of [null, 1, 3, 6, 8, 10]) {
      for (const glanz of [true, false]) {
        const el = zeige(guete, { glanz });
        expect(el.querySelector('.siegel-glanz') !== null).withContext(`Güte ${guete}, Glanz ${glanz}`).toBe(glanz);
      }
    }
  });

  it('lässt Winkel, Farbe und den Text der Güte vom Glanz unberührt; der Glanz hängt nur an (#351)', () => {
    for (const guete of [null, 3, 6, 8, 10]) {
      zeige(guete, { glanz: false });
      const ohne = [winkel(), farbe()];
      const text = svg().getAttribute('aria-label');
      zeige(guete, { glanz: true });
      expect([winkel(), farbe()]).withContext(`Güte ${guete}`).toEqual(ohne);
      expect(svg().getAttribute('aria-label')).withContext(`Güte ${guete}`).toBe(`${text}, mit Glanz`);
    }
  });

  it('legt das Sichtfeld eng an die Zeichnung, der Glanz-Stern ragt darüber hinaus', () => {
    const el = zeige(10, { glanz: true });
    document.body.appendChild(el);
    const [, oben] = svg().getAttribute('viewBox')!.split(' ').map(Number);
    const stern = el.querySelector<SVGPathElement>('.siegel-stern')!.getBBox();

    expect(stern.y).toBeLessThan(oben);
    expect(getComputedStyle(svg()).overflow).toBe('visible');
    // Die Blase sitzt unten am Rand: kein Streifen unter der Spitze.
    const blase = el.querySelector<SVGGElement>('.siegel-blase-gruppe')!.getBBox();
    const [, , , hoehe] = svg().getAttribute('viewBox')!.split(' ').map(Number);
    expect(oben + hoehe - (blase.y + blase.height)).toBeLessThan(1);
    el.remove();
  });

  it('hält die Glanz-Sterne in jedem Winkel der Hand frei vom Daumen', () => {
    /** Punkte auf dem Umriss eines Pfads, im Koordinatensystem des Sichtfelds. */
    function umriss(pfad: SVGPathElement, wurzel: SVGSVGElement): DOMPoint[] {
      const m = wurzel.getCTM()!.inverse().multiply(pfad.getCTM()!);
      const laenge = pfad.getTotalLength();
      return Array.from({ length: 200 }, (_, i) => pfad.getPointAtLength((laenge * i) / 200).matrixTransform(m));
    }
    // Halbe Strichstärken von Hand (2.6 bei Maßstab 1.6) und Stern, dazu Luft.
    const mindestens = (2.6 * 1.6) / 2 + 0.6 + 1;

    for (const guete of [null, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) {
      // Je Güte ein frisches Siegel: ohne Wechsel läuft keine Drehung, die Hand steht im Zielwinkel.
      const f = TestBed.createComponent(SiegelComponent);
      f.componentRef.setInput('guete', guete);
      f.componentRef.setInput('glanz', true);
      f.detectChanges();
      const el = f.nativeElement as HTMLElement;
      document.body.appendChild(el);
      const wurzel = el.querySelector<SVGSVGElement>('svg')!;
      const hand = umriss(el.querySelector<SVGPathElement>('.siegel-hand path')!, wurzel);
      for (const pfad of Array.from(el.querySelectorAll<SVGPathElement>('.siegel-sterne path'))) {
        const stern = umriss(pfad, wurzel);
        const abstand = Math.min(...hand.flatMap((h) => stern.map((s) => Math.hypot(h.x - s.x, h.y - s.y))));
        expect(abstand).withContext(`Güte ${guete}, ${pfad.getAttribute('class')}`).toBeGreaterThan(mindestens);
      }
      el.remove();
    }
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
    // Das Logo ist die Güte 10, also im Tannengrün der Seite.
    expect(logo).toContain(`fill="${tannengruen()}"`);
    expect(logo).not.toContain('#008a3c');
  });

  it('gibt dem Logo eine weiße Kontur, damit es auch auf tannengrünem Grund lesbar ist', async () => {
    const logo = await (await fetch('/marke/logo.svg')).text();
    const dokument = new DOMParser().parseFromString(logo, 'image/svg+xml');
    expect(dokument.querySelector('parsererror')).withContext('logo.svg ist wohlgeformtes XML').toBeNull();
    const kontur = dokument.querySelector('g.kontur');

    expect(kontur).withContext('Gruppe .kontur im Logo').not.toBeNull();
    expect(kontur!.getAttribute('stroke')).toBe('#fff');
    expect(Number(kontur!.getAttribute('stroke-width'))).toBeGreaterThanOrEqual(4);
    // Die Kontur liegt unter der Blase, nicht darüber.
    const gruppen = Array.from(dokument.documentElement.children);
    const blase = gruppen.find((g) => g.getAttribute('fill') === tannengruen());
    expect(gruppen.indexOf(kontur!)).toBeLessThan(gruppen.indexOf(blase!));
  });
});
