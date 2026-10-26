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
      'search/searchByText',
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

  it('haelt den Fangkorb nie im Cache', () => {
    holen(`${api}/rawinput/getRawInputs?page=1`);
    httpMock.expectOne(`${api}/rawinput/getRawInputs?page=1`).flush({ stand: 'alt' });

    holen(`${api}/rawinput/getRawInputs?page=1`);
    httpMock.expectOne(`${api}/rawinput/getRawInputs?page=1`).flush({ stand: 'neu' });
  });

  describe('Spec: Stufenwechsel eines Einwurfs', () => {
    it('die Fangkorb-Abfrage liefert danach ohne Wartezeit den neuen Stand', () => {
      const einwuerfe = TestBed.inject(EinwurfService);
      const fangkorb = `${api}/rawinput/getRawInputs?page=1&page_size=20`;
      const stufen: string[] = [];
      const laden = () =>
        einwuerfe
          .fangkorbLaden(1, 20)
          .subscribe((antwort) => stufen.push(antwort.results[0].status));

      laden();
      httpMock.expectOne(fangkorb).flush({ results: [{ id: 'id-1', status: 'open' }] });

      einwuerfe.updateStatus('id-1', 'discarded').subscribe();
      httpMock.expectOne(`${api}/rawinput/id-1/status`).flush({ id: 'id-1', status: 'discarded' });

      laden();
      httpMock.expectOne(fangkorb).flush({ results: [{ id: 'id-1', status: 'discarded' }] });

      expect(stufen).toEqual(['open', 'discarded']);
    });
  });
});
