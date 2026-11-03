import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { KuerzungsvorschlagComponent } from './kuerzungsvorschlag.component';
import { environment } from '../../../environments/environment';

const PFAD = `${environment.baseUrl}/api/v1/kuerzungsvorschlag`;
const LANG = 'Die Wärmepumpe, die im Keller steht, spart viel Geld. Meine Tante war im Urlaub.';

/**
 * Kürzungsvorschlag (#403): Nur auf Klick schlägt der Dienst eine Kurzfassung aus den
 * eigenen Sätzen des Kommentars vor. Die Person übernimmt oder verwirft ihn; nichts wird
 * automatisch ersetzt.
 */
describe('KuerzungsvorschlagComponent', () => {
  let fixture: ComponentFixture<KuerzungsvorschlagComponent>;
  let http: HttpTestingController;
  let uebernommen: string[];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KuerzungsvorschlagComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    fixture = TestBed.createComponent(KuerzungsvorschlagComponent);
    http = TestBed.inject(HttpTestingController);
    uebernommen = [];
    fixture.componentInstance.uebernehmen.subscribe((v: string) => uebernommen.push(v));
    fixture.componentRef.setInput('text', LANG);
    fixture.componentRef.setInput('aussage', 'Wärmepumpen sind zu teuer');
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  const element = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const knopf = (text: string): HTMLButtonElement =>
    Array.from(element().querySelectorAll('button')).find((b) => b.textContent?.trim() === text) as HTMLButtonElement;

  function vorschlagHolen(antwort: string | null): void {
    knopf('Kürzungsvorschlag').click();
    fixture.detectChanges();
    const anfrage = http.expectOne(PFAD);
    expect(anfrage.request.method).toBe('POST');
    expect(anfrage.request.body).toEqual({ text: LANG, aussage: 'Wärmepumpen sind zu teuer' });
    anfrage.flush({ vorschlag: antwort });
    fixture.detectChanges();
  }

  it('fragt nur auf Klick, nicht beim Schreiben', () => {
    fixture.componentRef.setInput('text', LANG + ' Noch ein Satz.');
    fixture.detectChanges();

    http.expectNone(PFAD);
  });

  it('zeigt den Vorschlag und ersetzt nichts, bis die Person übernimmt', () => {
    vorschlagHolen('Die Wärmepumpe spart viel Geld.');

    expect(element().querySelector('.kuerzungsvorschlag-text')?.textContent).toContain('Die Wärmepumpe spart viel Geld.');
    expect(uebernommen).toEqual([]);

    knopf('Übernehmen').click();
    fixture.detectChanges();

    expect(uebernommen).toEqual(['Die Wärmepumpe spart viel Geld.']);
    expect(element().querySelector('.kuerzungsvorschlag-text')).toBeNull();
  });

  it('Verwerfen schließt den Vorschlag, ohne etwas zu übernehmen', () => {
    vorschlagHolen('Die Wärmepumpe spart viel Geld.');

    knopf('Verwerfen').click();
    fixture.detectChanges();

    expect(uebernommen).toEqual([]);
    expect(element().querySelector('.kuerzungsvorschlag-text')).toBeNull();
  });

  it('sagt, wenn kein Satz in die Kurzfassung passt', () => {
    vorschlagHolen(null);

    expect(element().textContent).toContain('Kein Satz passt');
    expect(knopf('Übernehmen')).toBeUndefined();
  });

  it('sagt, wenn der Dienst nicht antwortet', () => {
    knopf('Kürzungsvorschlag').click();
    fixture.detectChanges();
    http.expectOne(PFAD).flush('weg', { status: 503, statusText: 'Service Unavailable' });
    fixture.detectChanges();

    expect(element().querySelector('[role="alert"]')?.textContent).toContain('gerade nicht');
  });

  it('ohne Text gibt es keinen Knopf', () => {
    fixture.componentRef.setInput('text', '   ');
    fixture.detectChanges();

    expect(knopf('Kürzungsvorschlag')).toBeUndefined();
  });
});
