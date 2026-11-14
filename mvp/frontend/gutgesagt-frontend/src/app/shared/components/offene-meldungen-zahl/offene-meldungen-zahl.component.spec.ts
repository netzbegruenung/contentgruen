import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject } from 'rxjs';

import { OffeneMeldungenZahlComponent } from './offene-meldungen-zahl.component';
import { OffeneMeldungen, Stand, WartendeSuchanfragen, ZuTunService } from '../../../services/zu-tun.service';

describe('OffeneMeldungenZahlComponent', () => {
  let fixture: ComponentFixture<OffeneMeldungenZahlComponent>;
  let meldungen$: BehaviorSubject<Stand<OffeneMeldungen>>;
  let suchanfragen$: BehaviorSubject<Stand<WartendeSuchanfragen>>;

  beforeEach(() => {
    meldungen$ = new BehaviorSubject<Stand<OffeneMeldungen>>({ daten: null, fehler: false });
    suchanfragen$ = new BehaviorSubject<Stand<WartendeSuchanfragen>>({ daten: null, fehler: false });
    TestBed.configureTestingModule({
      imports: [OffeneMeldungenZahlComponent],
      providers: [{ provide: ZuTunService, useValue: { meldungen$, suchanfragen$ } }],
    });
    fixture = TestBed.createComponent(OffeneMeldungenZahlComponent);
    fixture.detectChanges();
  });

  function text(): string {
    return (fixture.nativeElement.textContent ?? '').replace(/\s+/g, ' ').trim();
  }

  it('zeigt nichts, solange nichts geladen ist oder nichts offen ist', () => {
    expect(text()).toBe('');
    meldungen$.next({ daten: { anzahl: 0, mehr: false, aelteste: null }, fehler: false });
    fixture.detectChanges();
    expect(text()).toBe('');
  });

  it('zeigt die Zahl, fuer Screenreader als Satz, und zieht von selbst nach', () => {
    meldungen$.next({ daten: { anzahl: 2, mehr: false, aelteste: null }, fehler: false });
    fixture.detectChanges();

    const zahl: HTMLElement = fixture.nativeElement.querySelector('.zahl');
    expect(zahl.textContent!.trim()).toBe('2');
    expect(zahl.getAttribute('aria-hidden')).toBe('true');
    expect(fixture.nativeElement.querySelector('.visually-hidden').textContent.trim()).toBe(', 2 offene Meldungen');

    meldungen$.next({ daten: { anzahl: 1, mehr: false, aelteste: null }, fehler: false });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.visually-hidden').textContent.trim()).toBe(', 1 offene Meldung');
  });

  it('zeigt bei erreichter Grenze ein Plus', () => {
    meldungen$.next({ daten: { anzahl: 100, mehr: true, aelteste: null }, fehler: false });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.zahl').textContent.trim()).toBe('100+');
  });

  it('zählt wartende Suchanfragen mit und sagt sie an (#664)', () => {
    meldungen$.next({ daten: { anzahl: 2, mehr: false, aelteste: null }, fehler: false });
    suchanfragen$.next({ daten: { anzahl: 1 }, fehler: false });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.zahl').textContent.trim()).toBe('3');
    expect(fixture.nativeElement.querySelector('.visually-hidden').textContent.trim())
      .toBe(', 2 offene Meldungen, 1 Suchanfrage wartet auf Freigabe');

    meldungen$.next({ daten: { anzahl: 0, mehr: false, aelteste: null }, fehler: false });
    suchanfragen$.next({ daten: { anzahl: 3 }, fehler: false });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.zahl').textContent.trim()).toBe('3');
    expect(fixture.nativeElement.querySelector('.visually-hidden').textContent.trim())
      .toBe(', 3 Suchanfragen warten auf Freigabe');
  });

  it('zeigt Suchanfragen auch, solange die Meldungen noch laden', () => {
    suchanfragen$.next({ daten: { anzahl: 2 }, fehler: false });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.zahl').textContent.trim()).toBe('2');
  });
});
