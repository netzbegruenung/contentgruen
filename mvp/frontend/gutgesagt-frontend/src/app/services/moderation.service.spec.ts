import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ModerationService } from './moderation.service';
import { SessionService } from './session.service';
import { environment } from '../../environments/environment';

describe('ModerationService', () => {
  let service: ModerationService;
  let httpMock: HttpTestingController;
  let sessionService: jasmine.SpyObj<SessionService>;

  const mockSessionId = '12345678-1234-4234-8234-123456789012';

  beforeEach(() => {
    const sessionServiceSpy = jasmine.createSpyObj('SessionService', ['getSessionId']);
    sessionServiceSpy.getSessionId.and.returnValue(mockSessionId);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        ModerationService,
        { provide: SessionService, useValue: sessionServiceSpy }
      ]
    });

    service = TestBed.inject(ModerationService);
    httpMock = TestBed.inject(HttpTestingController);
    sessionService = TestBed.inject(SessionService) as jasmine.SpyObj<SessionService>;
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('reportContent', () => {
    it('should send report request with X-Session-Id header', () => {
      const contentId = 'content-123';
      const contentType = 'commentary';
      const reason = 'spam';
      const description = 'This is spam content';

      service.reportContent(contentId, contentType, reason, description).subscribe();

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/moderation/report`);
      expect(req.request.method).toBe('POST');
      expect(req.request.headers.get('X-Session-Id')).toBe(mockSessionId);
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
      expect(req.request.headers.get('X-Session-Id')).toBe(mockSessionId);

      req.flush({ success: true, message: 'Report submitted' });
    });

    it('should call sessionService.getSessionId()', () => {
      service.reportContent('content-123', 'commentary', 'spam').subscribe();

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/moderation/report`);
      req.flush({ success: true, message: 'Report submitted' });

      expect(sessionService.getSessionId).toHaveBeenCalled();
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

  describe('deleteContent', () => {
    it('should send delete request with correct parameters', () => {
      const contentType = 'commentary';
      const contentId = 'content-123';

      service.deleteContent(contentType, contentId).subscribe();

      const req = httpMock.expectOne(
        `${environment.baseUrl}/api/v1/moderation/content/${contentType}/${contentId}`
      );
      expect(req.request.method).toBe('DELETE');

      req.flush({ success: true, message: 'Content deleted' });
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
