import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RundgangBandComponent } from './rundgang-band.component';
import { RundgangService } from './rundgang.service';
import { Angebot, MITMACHEN_ANGEBOT, WILLKOMMEN } from './rundgang-daten';

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
    band.set(WILLKOMMEN);
    fixture.detectChanges();
    knopf('Rundgang starten').click();
    expect(rundgang.bandBeantworten).toHaveBeenCalledWith(true);
    knopf('Ausblenden').click();
    expect(rundgang.bandBeantworten).toHaveBeenCalledWith(false);
  });
});
