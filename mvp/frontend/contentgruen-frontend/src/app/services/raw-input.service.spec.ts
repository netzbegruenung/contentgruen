import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { RawInputService, GetRawInputsResponse } from './raw-input.service';
import { LoggingService } from './logging.service';
import { environment } from '../../environments/environment';

describe('RawInputService', () => {
  let service: RawInputService;
  let httpMock: HttpTestingController;

  const basis = `${environment.baseUrl}/api/v1/rawinput`;

  beforeEach(() => {
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['debug', 'error']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [RawInputService, { provide: LoggingService, useValue: loggingSpy }],
    });

    service = TestBed.inject(RawInputService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('schickt einen Einwurf an addRawInput', () => {
    service.addRawInput({ url: 'https://example.org/post' }).subscribe((antwort) => {
      expect(antwort.id).toBe('abc');
    });

    const anfrage = httpMock.expectOne(`${basis}/addRawInput`);
    expect(anfrage.request.method).toBe('POST');
    expect(anfrage.request.body).toEqual({ url: 'https://example.org/post' });
    anfrage.flush({ id: 'abc' });
  });

  it('holt den Fangkorb mit Seitenangaben', () => {
    const antwort: GetRawInputsResponse = {
      results_count: 0,
      results: [],
      total_records_count: 0,
    };

    service.getRawInputs(2, 50).subscribe((daten) => {
      expect(daten).toEqual(antwort);
    });

    const anfrage = httpMock.expectOne(
      (req) => req.url === `${basis}/getRawInputs`,
    );
    expect(anfrage.request.method).toBe('GET');
    expect(anfrage.request.params.get('page')).toBe('2');
    expect(anfrage.request.params.get('page_size')).toBe('50');
    anfrage.flush(antwort);
  });
});
