import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RundgangBandComponent } from './rundgang-band.component';
import { RundgangService } from './rundgang.service';
import { Angebot, HOME_ANGEBOT, MITMACHEN_ANGEBOT, WILLKOMMEN } from './rundgang-daten';

/** Das Angebot eines Rundgangs als Band statt Fenster (#587). */
describe('RundgangBandComponent', () => {
  let fixture: ComponentFixture<RundgangBandComponent>;
  let band: ReturnType<typeof signal<Angebot | null>>;
  let rundgang: { band: typeof band; bandBeantworten: jasmine.Spy };

  beforeEach(() => {
    band = signal<Angebot | null>(null);
    rundgang = { band, bandBeantworten: jasmine.createSpy('bandBeantworten') };
    TestBed.configureTestingModule({
      imports: [RundgangBandComponent],
      providers: [{ provide: RundgangService, useValue: rundgang }],
    });
    fixture = TestBed.createComponent(RundgangBandComponent);
    fixture.detectChanges();
  });

  const el = (): HTMLElement => fixture.nativeElement;
  const knopf = (text: string): HTMLButtonElement =>
    Array.from(el().querySelectorAll('button')).find((b) => b.textContent?.trim() === text) as HTMLButtonElement;

  it('zeigt nichts ohne Angebot', () => {
    expect(el().querySelector('aside')).toBeNull();
  });

  it('zeigt Titel und Satz des Angebots, benannt nach dem Titel', () => {
    fixture.componentRef.setInput('ort', 'start');
    band.set(WILLKOMMEN);
    fixture.detectChanges();
    const aside = el().querySelector('aside')!;
    expect(aside.querySelector('h2')?.textContent).toContain(WILLKOMMEN.titel);
    expect(aside.textContent).toContain(WILLKOMMEN.satz);
    expect(aside.getAttribute('aria-labelledby')).toBe(aside.querySelector('h2')!.id);
  });

  it('ist kein Fenster: kein Dialog, kein Fokusfang', () => {
    band.set(MITMACHEN_ANGEBOT);
    fixture.detectChanges();
    expect(el().querySelector('[role=dialog]')).toBeNull();
    expect(document.activeElement).not.toBe(knopf('Zeig mir’s'));
  });

  it('beschriftet die Knöpfe je Angebot', () => {
    band.set(MITMACHEN_ANGEBOT);
    fixture.detectChanges();
    expect(knopf('Zeig mir’s')).toBeTruthy();
    expect(knopf('Nein danke')).toBeTruthy();
  });

  it('startet den Rundgang oder blendet sich aus', () => {
    fixture.componentRef.setInput('ort', 'start');
    band.set(WILLKOMMEN);
    fixture.detectChanges();
    knopf('Rundgang starten').click();
    expect(rundgang.bandBeantworten).toHaveBeenCalledWith(true);
    knopf('Ausblenden').click();
    expect(rundgang.bandBeantworten).toHaveBeenCalledWith(false);
  });

  describe('Hinweis „Gut gesagt als App“ (14.11.2026)', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('ort', 'start');
      band.set(HOME_ANGEBOT);
      fixture.detectChanges();
    });

    it('sagt in einem Satz, wie es geht, mit dem Teilen-Symbol nur fürs Auge', () => {
      const p = el().querySelector('aside p')!;
      expect(p.textContent!.replace(/\s+/g, ' ').trim()).toBe(
        'Tippe in Safari auf Teilen (oder erst auf ···) und dann auf „Zum Home-Bildschirm“.',
      );
      const svg = p.querySelector('svg')!;
      expect(svg.getAttribute('aria-hidden')).toBe('true');
      expect(el().querySelector('aside h2')?.textContent).toContain('Gut gesagt als App');
    });

    it('zeigt das App-Symbol statt des Daumens', () => {
      expect(el().querySelector('aside img')?.getAttribute('src')).toBe('marke/apple-touch-icon-180.png');
    });

    it('hat nur „Ausblenden“, für Screenreader „Hinweis ausblenden“', () => {
      const knoepfe = el().querySelectorAll('aside button');
      expect(knoepfe.length).toBe(1);
      expect(knopf('Ausblenden').getAttribute('aria-label')).toBe('Hinweis ausblenden');
      knopf('Ausblenden').click();
      expect(rundgang.bandBeantworten).toHaveBeenCalledWith(false);
    });
  });

  describe('Fokus nach dem Ausblenden', () => {
    let haupt: HTMLElement;

    beforeEach(() => {
      haupt = document.createElement('main');
      haupt.id = 'hauptinhalt';
      document.body.appendChild(haupt);
      document.body.appendChild(fixture.nativeElement);
    });

    afterEach(() => {
      haupt.remove();
      (fixture.nativeElement as HTMLElement).remove();
    });

    it('geht an den Hauptinhalt, nicht an den Seitenanfang', () => {
      band.set(MITMACHEN_ANGEBOT);
      fixture.detectChanges();
      knopf('Nein danke').focus();
      knopf('Nein danke').click();
      expect(document.activeElement).toBe(haupt);
      expect(haupt.getAttribute('tabindex')).toBe('-1');
    });

    it('auch beim Home-Hinweis mit eigenem Namen für Screenreader', () => {
      fixture.componentRef.setInput('ort', 'start');
      band.set(HOME_ANGEBOT);
      fixture.detectChanges();
      const aus = el().querySelector<HTMLButtonElement>('button[aria-label="Hinweis ausblenden"]')!;
      aus.focus();
      aus.click();
      expect(rundgang.bandBeantworten).toHaveBeenCalledWith(false);
      expect(document.activeElement).toBe(haupt);
    });

    it('lässt Knöpfe ohne eigenen Namen ohne aria-label', () => {
      band.set(MITMACHEN_ANGEBOT);
      fixture.detectChanges();
      expect(knopf('Nein danke').hasAttribute('aria-label')).toBeFalse();
    });
  });

  describe('Ort (Nutzerfuehrung 13.11.)', () => {
    it('zeigt das Willkommen nur unter dem Suchfeld, nicht ueber dem Inhalt', () => {
      band.set(WILLKOMMEN);
      fixture.detectChanges();
      expect(el().querySelector('aside')).toBeNull();

      fixture.componentRef.setInput('ort', 'start');
      fixture.detectChanges();
      expect(el().querySelector('aside h2')?.textContent).toContain(WILLKOMMEN.titel);
    });

    it('zeigt Mitmachen weiter ueber dem Inhalt und nicht auf der Startseite', () => {
      band.set(MITMACHEN_ANGEBOT);
      fixture.detectChanges();
      expect(el().querySelector('aside')).not.toBeNull();

      fixture.componentRef.setInput('ort', 'start');
      fixture.detectChanges();
      expect(el().querySelector('aside')).toBeNull();
    });
  });
});
