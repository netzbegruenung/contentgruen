import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FremdesBildComponent, istFremdeAdresse } from './fremdes-bild.component';

/**
 * Bilder fremder Server laedt der Browser erst auf Klick (#447). Ob eine Anfrage rausgeht,
 * pruefen die Specs an den Anfragen selbst: ein PerformanceObserver faengt jede Ressource ab,
 * die der Browser laedt. Als "fremder Server" dient der Karma-Server unter dem anderen
 * Hostnamen (localhost <-> 127.0.0.1): anderer Origin, aber erreichbar, sodass der Klick
 * nachweislich eine Anfrage ausloest.
 */
describe('FremdesBildComponent', () => {
  let fixture: ComponentFixture<FremdesBildComponent>;
  let element: HTMLElement;
  let beobachter: PerformanceObserver;
  let angefragt: string[];
  let zaehler = 0;

  function fremdeAdresse(): string {
    const host = location.hostname === '127.0.0.1' ? 'localhost' : '127.0.0.1';
    zaehler += 1;
    return `${location.protocol}//${host}:${location.port}/fremd-447.png?n=${Date.now()}-${zaehler}`;
  }

  function zeigen(src: string, alt = 'Solardach auf dem Rathaus'): void {
    fixture = TestBed.createComponent(FremdesBildComponent);
    fixture.componentRef.setInput('src', src);
    fixture.componentRef.setInput('alt', alt);
    fixture.detectChanges();
    element = fixture.nativeElement as HTMLElement;
  }

  /** Wartet, bis das Bild geladen oder gescheitert ist; beides heisst: die Anfrage ist raus. */
  function bildFertig(bild: HTMLImageElement): Promise<void> {
    if (bild.complete && bild.src) return Promise.resolve();
    return new Promise((fertig) => {
      bild.addEventListener('load', () => fertig(), { once: true });
      bild.addEventListener('error', () => fertig(), { once: true });
    });
  }

  /** Gibt dem Browser Zeit fuer Anfragen, die er ausloesen wuerde, und sammelt sie ein. */
  async function anfragenAbwarten(): Promise<string[]> {
    await new Promise((weiter) => setTimeout(weiter, 300));
    angefragt.push(...beobachter.takeRecords().map((e) => e.name));
    return angefragt;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [FremdesBildComponent] }).compileComponents();
    angefragt = [];
    beobachter = new PerformanceObserver((liste) => angefragt.push(...liste.getEntries().map((e) => e.name)));
    beobachter.observe({ type: 'resource' });
  });

  afterEach(() => beobachter.disconnect());

  it('stellt ohne Klick keine Anfrage an den fremden Server und zeigt "Bild laden"', async () => {
    const adresse = fremdeAdresse();
    zeigen(adresse);

    expect(element.querySelector('img')).toBeNull();
    const knopf = element.querySelector<HTMLButtonElement>('button.bild-laden')!;
    expect(knopf.textContent).toContain('Bild laden');
    expect(await anfragenAbwarten()).not.toContain(adresse);
  });

  it('laedt auf Klick genau dieses Bild, mit Alternativtext', async () => {
    const adresse = fremdeAdresse();
    const andere = fremdeAdresse();
    zeigen(adresse);
    const zweite = TestBed.createComponent(FremdesBildComponent);
    zweite.componentRef.setInput('src', andere);
    zweite.componentRef.setInput('alt', 'anderes Bild');
    zweite.detectChanges();

    element.querySelector<HTMLButtonElement>('button.bild-laden')!.click();
    fixture.detectChanges();

    const bild = element.querySelector<HTMLImageElement>('img')!;
    expect(bild.getAttribute('src')).toBe(adresse);
    expect(bild.alt).toBe('Solardach auf dem Rathaus');
    expect(element.querySelector('button.bild-laden')).toBeNull();
    await bildFertig(bild);

    const anfragen = await anfragenAbwarten();
    expect(anfragen).toContain(adresse);
    expect(anfragen).not.toContain(andere);
    expect((zweite.nativeElement as HTMLElement).querySelector('img')).toBeNull();
  });

  it('ist mit der Tastatur bedienbar und nennt den Alternativtext', () => {
    zeigen(fremdeAdresse());
    const knopf = element.querySelector<HTMLButtonElement>('button.bild-laden')!;

    expect(knopf.type).toBe('button');
    expect(knopf.getAttribute('aria-label')).toBe('Bild laden: Solardach auf dem Rathaus');
    knopf.focus();
    expect(document.activeElement).toBe(knopf);
  });

  it('gibt Klick und Enter nicht an die Karte weiter, die sonst die Detailansicht oeffnet', () => {
    zeigen(fremdeAdresse());
    const karte = jasmine.createSpy('karte');
    element.addEventListener('click', karte);
    element.addEventListener('keyup', karte);
    const knopf = element.querySelector<HTMLButtonElement>('button.bild-laden')!;

    knopf.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));
    knopf.click();

    expect(karte).not.toHaveBeenCalled();
  });

  it('setzt den Fokus nach dem Laden auf das Bild, damit Tastaturnutzende nicht ins Leere fallen', () => {
    zeigen(fremdeAdresse());
    const knopf = element.querySelector<HTMLButtonElement>('button.bild-laden')!;
    knopf.focus();
    knopf.click();
    fixture.detectChanges();

    expect(document.activeElement).toBe(element.querySelector('img'));
  });

  it('fragt nach einem Wechsel der Adresse wieder nach', () => {
    zeigen(fremdeAdresse());
    element.querySelector<HTMLButtonElement>('button.bild-laden')!.click();
    fixture.detectChanges();

    fixture.componentRef.setInput('src', fremdeAdresse());
    fixture.detectChanges();

    expect(element.querySelector('img')).toBeNull();
    expect(element.querySelector('button.bild-laden')).not.toBeNull();
  });

  it('zeigt Bilder vom eigenen Server sofort', () => {
    zeigen('/marke/logo.svg', 'Logo');

    expect(element.querySelector('button.bild-laden')).toBeNull();
    expect(element.querySelector('img')!.getAttribute('src')).toBe('/marke/logo.svg');
  });

  it('nutzt Sand als Grund und Tanne als Schrift', () => {
    zeigen(fremdeAdresse());
    document.body.appendChild(element);
    const stil = getComputedStyle(element.querySelector('button.bild-laden')!);
    const wurzel = getComputedStyle(document.documentElement);
    const aufgeloest = (farbe: string): string => {
      const probe = document.createElement('span');
      probe.style.color = farbe;
      document.body.appendChild(probe);
      const rgb = getComputedStyle(probe).color;
      probe.remove();
      return rgb;
    };

    expect(stil.backgroundColor).toBe(aufgeloest(wurzel.getPropertyValue('--einwurf-grund').trim()));
    expect(stil.color).toBe(aufgeloest(wurzel.getPropertyValue('--primary-dark').trim()));
    element.remove();
  });
});

describe('istFremdeAdresse', () => {
  const eigener = 'https://gutgesagt.example';

  it('erkennt fremde Server', () => {
    expect(istFremdeAdresse('https://example.org/dach.jpg', eigener)).toBeTrue();
    expect(istFremdeAdresse('http://gutgesagt.example/bild.png', eigener)).toBeTrue();
    expect(istFremdeAdresse('//example.org/dach.jpg', eigener)).toBeTrue();
  });

  it('laesst eigene, relative und eingebettete Bilder durch', () => {
    expect(istFremdeAdresse('https://gutgesagt.example/bild.png', eigener)).toBeFalse();
    expect(istFremdeAdresse('/marke/logo.svg', eigener)).toBeFalse();
    expect(istFremdeAdresse('data:image/png;base64,AAAA', eigener)).toBeFalse();
  });

  it('behandelt Unlesbares vorsichtshalber als fremd', () => {
    expect(istFremdeAdresse('http://[kaputt', eigener)).toBeTrue();
  });
});
