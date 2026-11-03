import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { SprachhinweisComponent } from './sprachhinweis.component';
import { SPRACHHINWEIS_VERZOEGERUNG_MS } from './sprachhinweis.service';
import { environment } from '../../../../environments/environment';

const PFAD = `${environment.baseUrl}/api/v1/spracherkennung`;
const ENGLISCH = 'Heat pumps are far too expensive for ordinary families.';

/**
 * Sprachhinweis beim Schreiben (#405): etwa eine Sekunde nach der letzten Eingabe fragt
 * das Formular, ob ein Text ab fünf Wörtern offenbar nicht deutsch ist, und sagt es dann
 * in einem Satz. Er sperrt nichts; kürzere Texte fragt es gar nicht erst.
 */
describe('SprachhinweisComponent', () => {
  let fixture: ComponentFixture<SprachhinweisComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SprachhinweisComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    fixture = TestBed.createComponent(SprachhinweisComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function schreibe(text: string): void {
    fixture.componentRef.setInput('text', text);
    fixture.detectChanges();
  }

  const hinweis = (): string | null =>
    (fixture.nativeElement as HTMLElement).querySelector('.sprachhinweis')?.textContent?.trim() ?? null;

  it('fragt erst eine Sekunde nach der letzten Eingabe, einmal', fakeAsync(() => {
    schreibe('Heat pumps are far');
    tick(SPRACHHINWEIS_VERZOEGERUNG_MS - 100);
    schreibe(ENGLISCH);
    tick(SPRACHHINWEIS_VERZOEGERUNG_MS - 1);
    http.expectNone(PFAD);

    tick(1);
    const anfrage = http.expectOne(PFAD);
    expect(anfrage.request.method).toBe('POST');
    expect(anfrage.request.body).toEqual({ text: ENGLISCH });
    anfrage.flush({ sprache: 'en' });
  }));

  it('zeigt den Sprachhinweis zum Beitrag, wenn der Text nicht deutsch ist', fakeAsync(() => {
    schreibe(ENGLISCH);
    tick(SPRACHHINWEIS_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush({ sprache: 'en' });
    fixture.detectChanges();

    expect(hinweis()).toContain('Dieser Beitrag ist offenbar nicht auf Deutsch');
    expect(hinweis()).toContain('speichern kannst du trotzdem');
  }));

  it('spricht bei einer Aussage von der Aussage', fakeAsync(() => {
    fixture.componentRef.setInput('gegenstand', 'aussage');
    schreibe(ENGLISCH);
    tick(SPRACHHINWEIS_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush({ sprache: 'en' });
    fixture.detectChanges();

    expect(hinweis()).toContain('Diese Aussage ist offenbar nicht auf Deutsch');
    expect(hinweis()).toContain('anlegen kannst du sie trotzdem');
  }));

  it('zeigt nichts bei deutschem Text', fakeAsync(() => {
    schreibe('Wärmepumpen sind für normale Familien viel zu teuer.');
    tick(SPRACHHINWEIS_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush({ sprache: null });
    fixture.detectChanges();

    expect(hinweis()).toBeNull();
  }));

  it('fragt bei weniger als fünf Wörtern nicht und nimmt einen alten Hinweis weg', fakeAsync(() => {
    schreibe(ENGLISCH);
    tick(SPRACHHINWEIS_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush({ sprache: 'en' });
    fixture.detectChanges();
    expect(hinweis()).not.toBeNull();

    schreibe('Heat pumps 2030 are 80 %');
    tick(SPRACHHINWEIS_VERZOEGERUNG_MS);
    http.expectNone(PFAD);
    fixture.detectChanges();

    expect(hinweis()).toBeNull();
  }));

  it('zeigt nichts, wenn der Dienst nicht antwortet', fakeAsync(() => {
    schreibe(ENGLISCH);
    tick(SPRACHHINWEIS_VERZOEGERUNG_MS);
    http.expectOne(PFAD).flush('weg', { status: 503, statusText: 'Service Unavailable' });
    fixture.detectChanges();

    expect(hinweis()).toBeNull();
  }));
});
