import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { cacheInterceptor, cacheService } from './cache.interceptor';
import { EinwurfService } from '../services/einwurf.service';
import { environment } from '../../environments/environment';

describe('cacheInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  const api = `${environment.baseUrl}/api/v1`;

  /** Eine GET-Anfrage stellen und liefern, was beim Aufrufer ankommt. */
  function holen(url: string): unknown[] {
    const ergebnis: unknown[] = [];
    http.get(url).subscribe((daten) => ergebnis.push(daten));
    return ergebnis;
  }

  beforeEach(() => {
    cacheService.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(withInterceptors([cacheInterceptor])), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    cacheService.clear();
  });

  it('beantwortet eine wiederholte GET-Anfrage aus dem Cache', () => {
    holen(`${api}/content/recent`);
    httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'alt' });

    const zweite = holen(`${api}/content/recent`);

    httpMock.expectNone(`${api}/content/recent`);
    expect(zweite).toEqual([{ stand: 'alt' }]);
  });

  for (const methode of ['POST', 'PUT', 'PATCH', 'DELETE']) {
    it(`leert nach ${methode} auch die Antworten anderer Pfade`, () => {
      holen(`${api}/content/recent`);
      httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'alt' });

      http.request(methode, `${api}/commentary/addCommentary`, { body: {} }).subscribe();
      httpMock.expectOne(`${api}/commentary/addCommentary`).flush({});

      const danach = holen(`${api}/content/recent`);
      httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'neu' });
      expect(danach).toEqual([{ stand: 'neu' }]);
    });
  }

  it('leert den Cache auch, wenn die Aenderung fehlschlaegt', () => {
    holen(`${api}/content/recent`);
    httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'alt' });

    http.patch(`${api}/rawinput/id-1/status`, {}).subscribe({ error: () => undefined });
    httpMock
      .expectOne(`${api}/rawinput/id-1/status`)
      .flush('kaputt', { status: 500, statusText: 'Server Error' });

    holen(`${api}/content/recent`);
    httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'neu' });
  });

  it('speichert keine Antwort, deren Anfrage vor einer Aenderung losging', () => {
    holen(`${api}/content/recent`);
    const alteAnfrage = httpMock.expectOne(`${api}/content/recent`);

    http.put(`${api}/voting/content/c-1/like`, {}).subscribe();
    httpMock.expectOne(`${api}/voting/content/c-1/like`).flush({});
    alteAnfrage.flush({ stand: 'alt' });

    const danach = holen(`${api}/content/recent`);
    httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'neu' });
    expect(danach).toEqual([{ stand: 'neu' }]);
  });

  it('laesst den Cache bei lesenden POST-Anfragen wie der Suche stehen', () => {
    holen(`${api}/content/recent`);
    httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'alt' });

    for (const pfad of [
      'statement/searchStatements',
      'reference/search',
      'image/suggestCaption',
      'voting/votes/batch',
    ]) {
      http.post(`${api}/${pfad}`, {}).subscribe();
      httpMock.expectOne(`${api}/${pfad}`).flush({});
    }

    holen(`${api}/content/recent`);
    httpMock.expectNone(`${api}/content/recent`);
  });

  it('leert den Cache nach einer Suche, weil sie eine Aussage anlegt und Kennzahlen zaehlt', () => {
    holen(`${api}/metrics/suchen-ohne-treffer`);
    httpMock.expectOne(`${api}/metrics/suchen-ohne-treffer`).flush({ stand: 'alt' });

    http.post(`${api}/search/searchByText`, { query_text: 'Waermepumpe' }).subscribe();
    httpMock.expectOne(`${api}/search/searchByText`).flush({});

    const danach = holen(`${api}/metrics/suchen-ohne-treffer`);
    httpMock.expectOne(`${api}/metrics/suchen-ohne-treffer`).flush({ stand: 'neu' });
    expect(danach).toEqual([{ stand: 'neu' }]);
  });

  it('leert den Cache auch, wenn eine laufende Aenderung abgebrochen wird', () => {
    const aenderung = http.delete(`${api}/content/c-1`).subscribe();
    const anfrage = httpMock.expectOne(`${api}/content/c-1`);
    // Was waehrend der Aenderung geholt wird, landet im Cache, bis sie endet
    holen(`${api}/content/recent`);
    httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'waehrenddessen' });

    aenderung.unsubscribe();
    expect(anfrage.cancelled).toBeTrue();

    const danach = holen(`${api}/content/recent`);
    httpMock.expectOne(`${api}/content/recent`).flush({ stand: 'neu' });
    expect(danach).toEqual([{ stand: 'neu' }]);
  });

  it('haelt den Fangkorb nie im Cache', () => {
    holen(`${api}/rawinput/getRawInputs?page=1`);
    httpMock.expectOne(`${api}/rawinput/getRawInputs?page=1`).flush({ stand: 'alt' });

    holen(`${api}/rawinput/getRawInputs?page=1`);
    httpMock.expectOne(`${api}/rawinput/getRawInputs?page=1`).flush({ stand: 'neu' });
  });

  it('laedt Meine Einwuerfe jedes Mal frisch', () => {
    // Ein gerade eingeworfenes Fundstueck soll sofort dastehen.
    const einwuerfe = TestBed.inject(EinwurfService);
    const eigene = `${api}/rawinput/getOwnRawInputs?page=1&page_size=24`;
    const leer = { results_count: 0, results: [], total_records_count: 0 };

    einwuerfe.eigeneLaden(1, 24).subscribe();
    httpMock.expectOne(eigene).flush(leer);

    einwuerfe.eigeneLaden(1, 24).subscribe();
    httpMock.expectOne(eigene).flush(leer);
  });

  describe('nach dem Stufenwechsel eines Einwurfs (#291)', () => {
    // Die Fangkorb-Haelfte belegt die Spec, besteht aber auch ohne Leeren, weil der
    // Fangkorb nie im Cache liegt. Dass PATCH den Cache leert, belegt die Liste.
    it('liefern Fangkorb und gecachte Listen ohne Wartezeit den neuen Stand', () => {
      const einwuerfe = TestBed.inject(EinwurfService);
      const fangkorb = `${api}/rawinput/getRawInputs?page=1&page_size=20`;
      const stufen: string[] = [];
      const laden = () =>
        einwuerfe
          .fangkorbLaden(1, 20)
          .subscribe((antwort) => stufen.push(antwort.results[0].status));

      laden();
      httpMock.expectOne(fangkorb).flush({ results: [{ id: 'id-1', status: 'open' }] });
      // Eine Liste, die im Cache liegt, etwa die eigenen Beitraege
      holen(`${api}/contribution/getContributionsOfUser`);
      httpMock.expectOne(`${api}/contribution/getContributionsOfUser`).flush({ stand: 'alt' });

      einwuerfe.updateStatus('id-1', 'discarded').subscribe();
      httpMock.expectOne(`${api}/rawinput/id-1/status`).flush({ id: 'id-1', status: 'discarded' });

      laden();
      httpMock.expectOne(fangkorb).flush({ results: [{ id: 'id-1', status: 'discarded' }] });

      const liste = holen(`${api}/contribution/getContributionsOfUser`);
      httpMock.expectOne(`${api}/contribution/getContributionsOfUser`).flush({ stand: 'neu' });

      expect(stufen).toEqual(['open', 'discarded']);
      expect(liste).toEqual([{ stand: 'neu' }]);
    });
  });
});
