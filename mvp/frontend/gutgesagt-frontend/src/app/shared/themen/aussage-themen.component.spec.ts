import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { BehaviorSubject } from 'rxjs';
import { AussageThemenComponent } from './aussage-themen.component';
import { THEMEN_NICHT_GESPEICHERT } from './themen-meldung';
import { AuthService, UserInfo } from '../../auth/auth.service';
import { AussageMitThemenFeld } from '../../services/themen.service';
import { environment } from '../../../environments/environment';
import { STILLE_ABFRAGE } from '../selbst-nachladen';

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
    // Abgemeldete fragen die Liste nicht ab (s. Test „fragt Abgemeldete nicht …“).
    if (angemeldet) listeLiefern();
    return fixture.nativeElement as HTMLElement;
  }

  function listeLiefern(): void {
    const anfrage = http.expectOne(LISTE_URL);
    // Still: Ein 401 darf nie auf /login umleiten (Besucher auf der Ergebnisseite).
    expect(anfrage.request.context.get(STILLE_ABFRAGE)).toBeTrue();
    anfrage.flush({ themen: [KLIMA, VERKEHR, WOHNEN] });
    fixture.detectChanges();
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

  it('nennt die Marken als Liste „Themen“ fuer Screenreader', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [KLIMA, VERKEHR] }, false);

    const liste = e.querySelector('[role="list"]')!;
    expect(liste.getAttribute('aria-label')).toBe('Themen');
    expect(liste.querySelectorAll('[role="listitem"]').length).toBe(2);
  });

  it('speichert zwei schnelle Klicks der Reihe nach; der letzte gilt, der Spinner bleibt bis zum Ende', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [] }, true);
    umschalter(e)!.click();
    fixture.detectChanges();

    chip(e, 'Klima').click();
    fixture.detectChanges();
    chip(e, 'Wohnen').click();
    fixture.detectChanges();
    expect(marken(e)).toEqual(['Klima', 'Wohnen']);

    const erste = http.expectOne(ZUORDNEN_URL);
    expect(erste.request.body.themen).toEqual(['klima']);
    erste.flush({ statement_id: 'a-1', themen: [KLIMA] });
    fixture.detectChanges();
    expect(e.querySelector('.themen-speichert')).withContext('zweiter Auftrag noch offen').not.toBeNull();
    expect(marken(e)).toEqual(['Klima', 'Wohnen']);

    const zweite = http.expectOne(ZUORDNEN_URL);
    expect(zweite.request.body.themen).toEqual(['klima', 'wohnen']);
    zweite.flush({ statement_id: 'a-1', themen: [KLIMA, WOHNEN] });
    fixture.detectChanges();

    expect(e.querySelector('.themen-speichert')).toBeNull();
    expect(marken(e)).toEqual(['Klima', 'Wohnen']);
    expect(e.querySelector('[aria-live="polite"]')?.textContent?.trim()).toBe('Themen gespeichert.');
  });

  it('beginnt bei einer anderen Aussage zugeklappt und ohne Fehler', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [KLIMA] }, true);
    umschalter(e)!.click();
    fixture.detectChanges();
    chip(e, 'Verkehr').click();
    fixture.detectChanges();
    http.expectOne(ZUORDNEN_URL).flush({}, { status: 500, statusText: 'Fehler' });
    fixture.detectChanges();
    expect(e.querySelector('[role="alert"]')).not.toBeNull();

    fixture.componentRef.setInput('aussage', { statement_id: 'a-2', themen: [WOHNEN] });
    fixture.detectChanges();

    expect(marken(e)).toEqual(['Wohnen']);
    expect(e.querySelector('.themen-bearbeiten')).toBeNull();
    expect(e.querySelector('[role="alert"]')).toBeNull();
    expect(umschalter(e)!.getAttribute('aria-expanded')).toBe('false');
    expect(umschalter(e)!.hasAttribute('aria-controls')).toBeFalse();
  });

  it('nimmt nach dem Abmelden den Umschalter weg', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [KLIMA] }, true);
    expect(umschalter(e)).not.toBeNull();

    nutzer.next(null);
    fixture.detectChanges();

    expect(umschalter(e)).toBeNull();
    expect(marken(e)).toEqual(['Klima']);
  });

  // Die Themenliste braucht nur, wer zuordnet. Das BFF antwortet Abgemeldeten auf
  // /api/v1/statement/themen mit 401, und der AuthInterceptor fuehrte die Person dann
  // von der Ergebnisseite auf /login (Befund auf Test, v0.9.9).
  it('fragt Abgemeldete nicht nach der Themenliste', () => {
    zeigen({ statement_id: 'a-1', themen: [KLIMA] }, false);

    http.expectNone(LISTE_URL);
  });

  it('laedt die Themenliste nach dem Anmelden und bietet dann das Zuordnen an', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [KLIMA] }, false);
    http.expectNone(LISTE_URL);

    nutzer.next(ANGEMELDET);
    fixture.detectChanges();
    listeLiefern();

    expect(umschalter(e)!.textContent?.trim()).toBe('Themen ändern');
  });

  it('laedt die Themenliste beim naechsten Anmelden neu, wenn der erste Versuch scheiterte', () => {
    const e = zeigen({ statement_id: 'a-1', themen: [KLIMA] }, false);
    nutzer.next(ANGEMELDET);
    fixture.detectChanges();
    http.expectOne(LISTE_URL).flush({}, { status: 401, statusText: 'Unauthorized' });
    fixture.detectChanges();
    expect(umschalter(e)).toBeNull();

    nutzer.next(null);
    nutzer.next(ANGEMELDET);
    fixture.detectChanges();
    listeLiefern();

    expect(umschalter(e)!.textContent?.trim()).toBe('Themen ändern');
  });
});
