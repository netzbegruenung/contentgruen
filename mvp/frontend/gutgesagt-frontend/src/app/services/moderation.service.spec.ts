import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ModerationService } from './moderation.service';
import { environment } from '../../environments/environment';

describe('ModerationService', () => {
  let service: ModerationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        ModerationService
      ]
    });

    service = TestBed.inject(ModerationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('reportContent', () => {
    it('sendet die Meldung ohne Sitzungskennung (#446)', () => {
      const contentId = 'content-123';
      const contentType = 'commentary';
      const reason = 'spam';
      const description = 'This is spam content';

      service.reportContent(contentId, contentType, reason, description).subscribe();

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/moderation/report`);
      expect(req.request.method).toBe('POST');
      expect(req.request.headers.has('X-Session-Id')).toBeFalse();
      expect(req.request.body).toEqual({
        content_id: contentId,
        content_type: contentType,
        reason: reason,
        description: description
      });

      req.flush({ success: true, message: 'Report submitted' });
    });

    it('should send report request without description', () => {
      const contentId = 'content-123';
      const contentType = 'generictext';
      const reason = 'inappropriate';

      service.reportContent(contentId, contentType, reason).subscribe();

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/moderation/report`);
      expect(req.request.body.description).toBeUndefined();

      req.flush({ success: true, message: 'Report submitted' });
    });

    it('should handle successful report submission', (done) => {
      const mockResponse = { success: true, message: 'Content reported successfully' };

      service.reportContent('content-123', 'commentary', 'spam').subscribe(response => {
        expect(response).toEqual(mockResponse);
        done();
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/moderation/report`);
      req.flush(mockResponse);
    });

    it('should handle error response', (done) => {
      service.reportContent('content-123', 'commentary', 'spam').subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(429);
          done();
        }
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/moderation/report`);
      req.flush({ detail: 'Too many reports' }, { status: 429, statusText: 'Too Many Requests' });
    });
  });

  describe('getPendingReports', () => {
    it('should fetch pending reports with cache busting', () => {
      service.getPendingReports().subscribe();

      const req = httpMock.expectOne(req => req.url.includes('/api/v1/moderation/reports'));
      expect(req.request.method).toBe('GET');
      expect(req.request.url).toContain('limit=50');
      expect(req.request.url).toContain('offset=0');
      expect(req.request.url).toContain('_t='); // Cache busting timestamp
      expect(req.request.headers.get('Cache-Control')).toBe('no-cache');
      expect(req.request.headers.get('Pragma')).toBe('no-cache');

      req.flush({ total: 0, reports: [] });
    });

    it('should accept custom limit and offset', () => {
      service.getPendingReports(100, 50).subscribe();

      const req = httpMock.expectOne(req => req.url.includes('/api/v1/moderation/reports'));
      expect(req.request.url).toContain('limit=100');
      expect(req.request.url).toContain('offset=50');

      req.flush({ total: 0, reports: [] });
    });
  });

  describe('sperren', () => {
    it('sperrt den Beitrag per PUT mit Sperrgrund und Begründung, ohne Beitragstyp im Pfad', () => {
      const contentId = 'content-123';

      service.sperren(contentId, 'unterstellung', 'Unterstellt Bosheit.').subscribe();

      const req = httpMock.expectOne(
        `${environment.baseUrl}/api/v1/moderation/content/${contentId}/sperren`
      );
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({
        sperrgrund: 'unterstellung',
        begruendung: 'Unterstellt Bosheit.',
      });

      req.flush({ success: true, message: 'gesperrt' });
    });
  });

  describe('sperreBestaetigen', () => {
    it('bestätigt die Sperre per PUT mit Begründung', () => {
      service.sperreBestaetigen('sperre-1', 'Bleibt.').subscribe();

      const req = httpMock.expectOne(
        `${environment.baseUrl}/api/v1/moderation/sperren/sperre-1/bestaetigen`
      );
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ begruendung: 'Bleibt.' });

      req.flush({ success: true, message: 'Sperre bestaetigt' });
    });
  });

  describe('entsperren', () => {
    it('hebt die Sperre per PUT auf', () => {
      const contentId = 'content-123';

      service.entsperren(contentId).subscribe();

      const req = httpMock.expectOne(
        `${environment.baseUrl}/api/v1/moderation/content/${contentId}/entsperren`
      );
      expect(req.request.method).toBe('PUT');

      req.flush({ success: true, message: 'entsperrt' });
    });
  });

  describe('getGesperrte', () => {
    it('lädt die gesperrten Beiträge per GET', () => {
      let anzahl = -1;

      service.getGesperrte().subscribe((antwort) => (anzahl = antwort.total));

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/moderation/gesperrt`);
      expect(req.request.method).toBe('GET');

      req.flush({ total: 1, beitraege: [{ id: 'b-1', content_type: 'commentary', status: 'blocked' }] });
      expect(anzahl).toBe(1);
    });
  });

  describe('dismissReport', () => {
    it('should send dismiss request with optional notes', () => {
      const reportId = 'report-123';
      const notes = 'Not a valid report';

      service.dismissReport(reportId, notes).subscribe();

      const req = httpMock.expectOne(
        `${environment.baseUrl}/api/v1/moderation/reports/${reportId}/dismiss`
      );
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ notes });

      req.flush({ success: true, message: 'Report dismissed' });
    });

    it('should send dismiss request without notes', () => {
      const reportId = 'report-123';

      service.dismissReport(reportId).subscribe();

      const req = httpMock.expectOne(
        `${environment.baseUrl}/api/v1/moderation/reports/${reportId}/dismiss`
      );
      expect(req.request.body).toEqual({ notes: undefined });

      req.flush({ success: true, message: 'Report dismissed' });
    });
  });
});
