import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { BehaviorSubject } from 'rxjs';
import { AussageThemenComponent } from './aussage-themen.component';
import { THEMEN_NICHT_GESPEICHERT } from './themen-meldung';
import { AuthService, UserInfo } from '../../auth/auth.service';
import { AussageMitThemenFeld } from '../../services/themen.service';
import { environment } from '../../../environments/environment';

const LISTE_URL = `${environment.baseUrl}/api/v1/statement/themen`;
const ZUORDNEN_URL = `${environment.baseUrl}/api/v1/statement/themen/zuordnen`;
const KLIMA = { schluessel: 'klima', name: 'Klima' };
const VERKEHR = { schluessel: 'verkehr', name: 'Verkehr' };
const WOHNEN = { schluessel: 'wohnen', name: 'Wohnen' };
const ANGEMELDET: UserInfo = { isAuthenticated: true, userId: 'u-1', userName: 'Testkonto', claims: null };

describe('AussageThemenComponent', () => {
  let fixture: ComponentFixture<AussageThemenComponent>;
  let http: HttpTestingController;
  let nutzer: BehaviorSubject<UserInfo | null>;

  function zeigen(aussage: AussageMitThemenFeld | null, angemeldet: boolean): HTMLElement {
    nutzer = new BehaviorSubject<UserInfo | null>(angemeldet ? ANGEMELDET : null);
    TestBed.configureTestingModule({
      imports: [AussageThemenComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), { provide: AuthService, useValue: { userInfo$: nutzer } }],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AussageThemenComponent);
    fixture.componentRef.setInput('aussage', aussage);
    fixture.detectChanges();
    http.expectOne(LISTE_URL).flush({ themen: [KLIMA, VERKEHR, WOHNEN] });
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  const marken = (e: HTMLElement) => Array.from(e.querySelectorAll('.thema-marke')).map((m) => m.textContent?.trim());
  const umschalter = (e: HTMLElement) => e.querySelector('.themen-umschalter') as HTMLButtonElement | null;
  const chip = (e: HTMLElement, name: string) =>
    (Array.from(e.querySelectorAll('.thema-chip')) as HTMLButtonElement[]).find((k) => k.textContent?.trim() === name)!;

  afterEach(() => http.verify());

  it('zeigt Abgemeldeten nur die Themen, ohne Umschalter', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [KLIMA, VERKEHR] }, false);

    expect(marken(e)).toEqual(['Klima', 'Verkehr']);
    expect(umschalter(e)).toBeNull();
  });

  it('zeigt Abgemeldeten ohne Themen nichts', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [] }, false);

    expect(e.querySelector('.aussage-themen')).toBeNull();
  });

  it('bietet Angemeldeten ohne Themen „Themen zuordnen“ an, mit Themen „Themen ändern“', () => {
    expect(umschalter(zeigen({ statement_id: 'a-1', themen: [] }, true))!.textContent?.trim()).toBe('Themen zuordnen');
    TestBed.resetTestingModule();
    expect(umschalter(zeigen({ statement_id: 'a-1', themen: [KLIMA] }, true))!.textContent?.trim()).toBe('Themen ändern');
  });

  it('klappt die Auswahl auf und speichert jeden Klick gleich, mit Spinner', () => {
    const aussage = { statement_id: 'a-1', themen: [KLIMA] };
    const e = zeigen(aussage, true);
    umschalter(e)!.click();
    fixture.detectChanges();
    expect(umschalter(e)!.getAttribute('aria-expanded')).toBe('true');

    chip(e, 'Wohnen').click();
    fixture.detectChanges();

    const anfrage = http.expectOne(ZUORDNEN_URL);
    expect(anfrage.request.method).toBe('PUT');
    expect(anfrage.request.body).toEqual({ statement_id: 'a-1', themen: ['klima', 'wohnen'] });
    expect(marken(e)).toEqual(['Klima', 'Wohnen']);
    expect(e.querySelector('.themen-speichert')).not.toBeNull();

    anfrage.flush({ statement_id: 'a-1', themen: [KLIMA, WOHNEN] });
    fixture.detectChanges();

    expect(e.querySelector('.themen-speichert')).toBeNull();
    expect(marken(e)).toEqual(['Klima', 'Wohnen']);
    expect(e.querySelector('[role="alert"]')).toBeNull();
  });

  it('zeigt nach einem Fehler den alten Stand und sagt es', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [KLIMA] }, true);
    umschalter(e)!.click();
    fixture.detectChanges();
    chip(e, 'Verkehr').click();
    fixture.detectChanges();

    http.expectOne(ZUORDNEN_URL).flush({}, { status: 500, statusText: 'Fehler' });
    fixture.detectChanges();

    expect(marken(e)).toEqual(['Klima']);
    expect(e.querySelector('[role="alert"]')?.textContent?.trim()).toBe(THEMEN_NICHT_GESPEICHERT);
    expect(e.querySelector('.themen-speichert')).toBeNull();
  });

  it('nimmt nach dem Abmelden den Umschalter weg', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [KLIMA] }, true);
    expect(umschalter(e)).not.toBeNull();

    nutzer.next(null);
    fixture.detectChanges();

    expect(umschalter(e)).toBeNull();
    expect(marken(e)).toEqual(['Klima']);
  });
});
