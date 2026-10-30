import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FremdesBildComponent, istFremdeAdresse } from './fremdes-bild.component';
import { aufgeloest, themaFarbe } from '../../testing/farben';
import { Anfragen, bildFertig, fremdeAdresse } from '../../testing/anfragen';

/** Bilder von fremden Servern laedt der Browser erst auf Klick (#447); belegt an den Anfragen selbst. */
describe('FremdesBildComponent', () => {
  let fixture: ComponentFixture<FremdesBildComponent>;
  let element: HTMLElement;
  let anfragen: Anfragen;

  function zeigen(src: string, alt = 'Solardach auf dem Rathaus'): void {
    fixture = TestBed.createComponent(FremdesBildComponent);
    fixture.componentRef.setInput('src', src);
    fixture.componentRef.setInput('alt', alt);
    fixture.detectChanges();
    element = fixture.nativeElement as HTMLElement;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [FremdesBildComponent] }).compileComponents();
    anfragen = new Anfragen();
    anfragen.starten();
  });

  afterEach(() => anfragen.beenden());

  it('stellt ohne Klick keine Anfrage an den fremden Server und zeigt "Bild laden"', async () => {
    const adresse = fremdeAdresse();
    zeigen(adresse);

    expect(element.querySelector('img')).toBeNull();
    const knopf = element.querySelector<HTMLButtonElement>('button.bild-laden')!;
    expect(knopf.textContent).toContain('Bild laden');
    expect(await anfragen.abwarten()).not.toContain(adresse);
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

    const angefragt = await anfragen.abwarten();
    expect(angefragt).toContain(adresse);
    expect(angefragt).not.toContain(andere);
    expect((zweite.nativeElement as HTMLElement).querySelector('img')).toBeNull();
  });

  it('ist ein fokussierbarer Knopf, der den Alternativtext nennt', () => {
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
    const darum = element.parentElement!;
    darum.addEventListener('click', karte);
    darum.addEventListener('keyup', karte);
    const knopf = element.querySelector<HTMLButtonElement>('button.bild-laden')!;

    knopf.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));
    knopf.click();

    expect(karte).not.toHaveBeenCalled();
  });

  it('gibt das keyup von Enter nicht weiter, das nach dem Laden schon auf dem Bild landet', () => {
    zeigen(fremdeAdresse());
    const karte = jasmine.createSpy('karte');
    element.parentElement!.addEventListener('keyup', karte);
    const knopf = element.querySelector<HTMLButtonElement>('button.bild-laden')!;
    knopf.focus();

    // Enter: keydown loest am Knopf den Klick aus, das keyup trifft danach das Bild
    knopf.click();
    fixture.detectChanges();
    document.activeElement!.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));

    expect(document.activeElement!.tagName).toBe('IMG');
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

  it('nennt ohne Alternativtext nach dem Laden wenigstens den Server, auf dem der Fokus landet', () => {
    const adresse = fremdeAdresse();
    zeigen(adresse, '');
    const knopf = element.querySelector<HTMLButtonElement>('button.bild-laden')!;
    expect(knopf.getAttribute('aria-label')).toBe('Bild laden');

    knopf.focus();
    knopf.click();
    fixture.detectChanges();

    const bild = element.querySelector<HTMLImageElement>('img')!;
    expect(document.activeElement).toBe(bild);
    expect(bild.alt).toBe(`Bild von ${new URL(adresse).hostname}`);
  });

  it('behaelt das geladene Bild, wenn sich nur der Alternativtext aendert', () => {
    zeigen(fremdeAdresse());
    element.querySelector<HTMLButtonElement>('button.bild-laden')!.click();
    fixture.detectChanges();

    fixture.componentRef.setInput('alt', 'anderer Text');
    fixture.detectChanges();

    expect(element.querySelector<HTMLImageElement>('img')!.alt).toBe('anderer Text');
  });

  it('zeigt Bilder vom eigenen Server sofort', () => {
    zeigen('/marke/logo.svg', 'Logo');

    expect(element.querySelector('button.bild-laden')).toBeNull();
    expect(element.querySelector('img')!.getAttribute('src')).toBe('/marke/logo.svg');
  });

  it('nutzt Sand als Grund und Tanne als Schrift', () => {
    zeigen(fremdeAdresse());
    const stil = getComputedStyle(element.querySelector('button.bild-laden')!);

    expect(stil.backgroundColor).toBe(aufgeloest(themaFarbe('--einwurf-grund')));
    expect(stil.color).toBe(aufgeloest(themaFarbe('--primary-dark')));
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
