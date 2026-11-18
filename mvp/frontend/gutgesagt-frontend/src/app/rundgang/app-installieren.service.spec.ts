import { TestBed } from '@angular/core/testing';
import { HOME_HINWEIS_MERKER } from '../shared/geraetespeicher-schalter';
import { installierenEreignis } from '../testing/installieren-ereignis';
import { ALS_APP_GESTARTET, AppInstallierenService } from './app-installieren.service';

/** Angebot des Browsers, Gut gesagt als App zu installieren (18.11.2026). */
describe('AppInstallierenService', () => {
  let alsApp: boolean;

  beforeEach(() => {
    alsApp = false;
    TestBed.configureTestingModule({
      providers: [{ provide: ALS_APP_GESTARTET, useValue: () => alsApp }],
    });
  });

  const service = (): AppInstallierenService => TestBed.inject(AppInstallierenService);

  it('ohne Ereignis: nicht installierbar, „Installieren“ tut nichts', async () => {
    const s = service();
    expect(s.installierbar()).toBeFalse();
    expect(await s.installieren()).toBeNull();
  });

  it('Schalter aus: merkt sich das Ereignis, lässt die Infoleiste des Browsers stehen', async () => {
    const s = service();
    const e = installierenEreignis('accepted');
    window.dispatchEvent(e);
    expect(e.defaultPrevented).toBeFalse();
    expect(s.installierbar()).toBeTrue();
    expect(await s.installieren()).toBe('accepted');
    expect(e.prompt).toHaveBeenCalledTimes(1);
  });

  it('Schalter an: unterdrückt die Infoleiste des Browsers', () => {
    TestBed.overrideProvider(HOME_HINWEIS_MERKER, { useValue: true });
    const s = service();
    const e = installierenEreignis('accepted');
    window.dispatchEvent(e);
    expect(e.defaultPrevented).toBeTrue();
    expect(s.installierbar()).toBeTrue();
  });

  it('„Installieren“ ruft prompt() auf; angenommen gilt als installiert', async () => {
    const s = service();
    const e = installierenEreignis('accepted');
    window.dispatchEvent(e);
    expect(await s.installieren()).toBe('accepted');
    expect(e.prompt).toHaveBeenCalledTimes(1);
    expect(s.installierbar()).toBeFalse();
    expect(s.installiert()).toBeTrue();
  });

  it('abgelehnt: das Ereignis ist verbraucht, nicht installiert, kein zweiter Dialog', async () => {
    const s = service();
    const e = installierenEreignis('dismissed');
    window.dispatchEvent(e);
    expect(await s.installieren()).toBe('dismissed');
    expect(s.installierbar()).toBeFalse();
    expect(s.installiert()).toBeFalse();
    expect(await s.installieren()).toBeNull();
    expect(e.prompt).toHaveBeenCalledTimes(1);
  });

  it('appinstalled: installiert, kein Knopf mehr', () => {
    const s = service();
    window.dispatchEvent(installierenEreignis('accepted'));
    const geaendert = jasmine.createSpy('geaendert');
    s.geaendert$.subscribe(geaendert);
    window.dispatchEvent(new Event('appinstalled'));
    expect(s.installierbar()).toBeFalse();
    expect(s.installiert()).toBeTrue();
    expect(geaendert).toHaveBeenCalled();
  });

  it('als App gestartet: installiert, auch ein spätes Ereignis bringt keinen Knopf', () => {
    alsApp = true;
    const s = service();
    expect(s.installiert()).toBeTrue();
    window.dispatchEvent(installierenEreignis('accepted'));
    expect(s.installierbar()).toBeFalse();
  });

  it('schreibt nichts in den Speicher des Browsers', async () => {
    const schreiben = spyOn(Storage.prototype, 'setItem').and.callThrough();
    const s = service();
    window.dispatchEvent(installierenEreignis('accepted'));
    await s.installieren();
    window.dispatchEvent(new Event('appinstalled'));
    expect(schreiben).not.toHaveBeenCalled();
  });
});
