import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ALLE_SEITENGROESSE, AlleMeineBeitraege, MeineBeitraegeService } from './meine-beitraege.service';

describe('MeineBeitraegeService', () => {
  let service: MeineBeitraegeService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(MeineBeitraegeService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const seite = (ids: string[], gesamt: number) => ({
    results_count: ids.length,
    total_records_count: gesamt,
    results: ids.map((id) => ({ id })),
  });

  function antworten(nr: number, ids: string[], gesamt: number): void {
    http
      .expectOne((r) => r.url.endsWith(`getContributionsOfUser?page=${nr}&page_size=${ALLE_SEITENGROESSE}`))
      .flush(seite(ids, gesamt));
  }

  it('laedt fuer das Album alle Seiten: erst die erste, dann die uebrigen zugleich', () => {
    let ergebnis: AlleMeineBeitraege | undefined;
    service.alleMeineBeitraege().subscribe((e) => (ergebnis = e));

    antworten(1, ['a'], 244);
    antworten(2, ['b'], 244);
    antworten(3, ['c'], 244);

    expect(ergebnis?.gesamt).toBe(244);
    expect(ergebnis?.beitraege.map((b) => b.id)).toEqual(['a', 'b', 'c']);
  });

  it('kommt bei wenigen Beitraegen mit einem Abruf aus', () => {
    let ergebnis: AlleMeineBeitraege | undefined;
    service.alleMeineBeitraege().subscribe((e) => (ergebnis = e));

    antworten(1, ['a', 'b', 'c'], 3);

    expect(ergebnis?.beitraege.length).toBe(3);
  });
});
