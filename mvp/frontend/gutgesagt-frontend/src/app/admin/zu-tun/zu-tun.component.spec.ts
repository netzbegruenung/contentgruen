import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { ZuTunComponent } from './zu-tun.component';
import { OffeneLoeschauftraege, OffeneMeldungen, Stand, ZuTunService } from '../../services/zu-tun.service';

describe('ZuTunComponent', () => {
  let fixture: ComponentFixture<ZuTunComponent>;
  let meldungen$: BehaviorSubject<Stand<OffeneMeldungen>>;
  let loeschauftraege$: BehaviorSubject<Stand<OffeneLoeschauftraege>>;

  beforeEach(() => {
    meldungen$ = new BehaviorSubject<Stand<OffeneMeldungen>>({ daten: null, fehler: false });
    loeschauftraege$ = new BehaviorSubject<Stand<OffeneLoeschauftraege>>({ daten: null, fehler: false });
    TestBed.configureTestingModule({
      imports: [ZuTunComponent],
      providers: [provideRouter([]), { provide: ZuTunService, useValue: { meldungen$, loeschauftraege$ } }],
    });
    fixture = TestBed.createComponent(ZuTunComponent);
    fixture.detectChanges();
  });

  function punkt(testid: string): HTMLElement {
    return fixture.nativeElement.querySelector(`[data-testid="${testid}"]`);
  }

  function text(element: HTMLElement): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
  }

  it('zeigt beim ersten Laden Spinner und Text', () => {
    expect(text(punkt('zu-tun-meldungen'))).toBe('Lade Meldungen …');
    expect(punkt('zu-tun-meldungen').querySelector('mat-spinner')).not.toBeNull();
  });

  it('nennt offene Meldungen mit dem Alter der aeltesten und verlinkt die offene Liste', () => {
    const vorDreiTagen = new Date(Date.now() - 3 * 24 * 3_600_000 - 60_000).toISOString();
    meldungen$.next({ daten: { anzahl: 2, mehr: false, aelteste: vorDreiTagen }, fehler: false });
    loeschauftraege$.next({ daten: { anzahl: 0, ueberfaellig: 0 }, fehler: false });
    fixture.detectChanges();

    expect(text(punkt('zu-tun-meldungen'))).toBe('2 offene Meldungen, älteste seit 3 Tagen');
    const link: HTMLAnchorElement = punkt('zu-tun-meldungen').querySelector('a')!;
    expect(link.getAttribute('href')).toBe('/admin/moderation?ansicht=pending');
    expect(text(punkt('zu-tun-loeschauftraege'))).toBe('Keine offenen Löschaufträge');
  });

  it('hebt ueberfaellige Loeschauftraege hervor und verlinkt ihre Liste', () => {
    meldungen$.next({ daten: { anzahl: 0, mehr: false, aelteste: null }, fehler: false });
    loeschauftraege$.next({ daten: { anzahl: 3, ueberfaellig: 1 }, fehler: false });
    fixture.detectChanges();

    expect(text(punkt('zu-tun-loeschauftraege'))).toBe('3 offene Löschaufträgewarning1 überfällig');
    expect(punkt('zu-tun-ueberfaellig')).not.toBeNull();
    expect(punkt('zu-tun-loeschauftraege').querySelector('a')!.getAttribute('href')).toBe(
      '/admin/moderation?ansicht=loeschauftraege',
    );
  });

  it('sagt in einem Satz, wenn nichts zu tun ist', () => {
    meldungen$.next({ daten: { anzahl: 0, mehr: false, aelteste: null }, fehler: false });
    loeschauftraege$.next({ daten: { anzahl: 0, ueberfaellig: 0 }, fehler: false });
    fixture.detectChanges();

    expect(text(punkt('zu-tun-nichts'))).toBe('Nichts zu tun. Keine Meldungen, keine Löschaufträge.');
    expect(punkt('zu-tun-meldungen')).toBeNull();
  });

  it('nennt bei erreichter Grenze kein Alter, das falsch sein kann', () => {
    meldungen$.next({ daten: { anzahl: 100, mehr: true, aelteste: '2026-11-01T00:00:00Z' }, fehler: false });
    fixture.detectChanges();

    expect(text(punkt('zu-tun-meldungen'))).toBe('100 oder mehr offene Meldungen');
  });

  it('sagt bei einem Fehler, dass es von selbst neu versucht, statt „bitte neu laden“', () => {
    meldungen$.next({ daten: null, fehler: true });
    loeschauftraege$.next({ daten: { anzahl: 1, ueberfaellig: 0 }, fehler: true });
    fixture.detectChanges();

    expect(text(punkt('zu-tun-meldungen'))).toBe('Meldungen gerade nicht erreichbar, neuer Versuch in Kürze …');
    expect(text(fixture.nativeElement)).toContain('Aktualisieren gerade nicht möglich, neuer Versuch in Kürze …');
    expect(text(fixture.nativeElement)).not.toContain('neu laden');
  });
});
