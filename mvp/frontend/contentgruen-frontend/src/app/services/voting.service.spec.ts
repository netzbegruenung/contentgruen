import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { VotingService, VoteResponse, VoteStats } from './voting.service';
import { LoggingService } from './logging.service';
import { environment } from '../../environments/environment';

describe('VotingService', () => {
  let service: VotingService;
  let httpMock: HttpTestingController;
  let loggingService: jasmine.SpyObj<LoggingService>;

  beforeEach(() => {
    const loggingSpy = jasmine.createSpyObj('LoggingService', [
      'logInteraction',
      'logError'
    ]);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        VotingService,
        { provide: LoggingService, useValue: loggingSpy }
      ]
    });

    service = TestBed.inject(VotingService);
    httpMock = TestBed.inject(HttpTestingController);
    loggingService = TestBed.inject(LoggingService) as jasmine.SpyObj<LoggingService>;
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('setLike', () => {
    it('should set a like successfully', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';
      const mockResponse: VoteResponse = {
        content_id: contentId,
        vote_type: 'like',
        message: 'Like set successfully'
      };

      service.setLike(contentId).subscribe(response => {
        expect(response).toEqual(mockResponse);
        expect(loggingService.logInteraction).toHaveBeenCalledWith(
          'vote_like',
          { contentId }
        );
        expect(loggingService.logInteraction).toHaveBeenCalledWith(
          'like_set',
          {
            contentId,
            message: 'Like set successfully'
          }
        );
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/like`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({});
      req.flush(mockResponse);
    });

    it('should handle error when setting like', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';

      service.setLike(contentId).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(500);
          expect(loggingService.logError).toHaveBeenCalledWith(
            'Failed to set like',
            jasmine.any(Object)
          );
        }
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/like`);
      req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });
    });
  });

  describe('removeLike', () => {
    it('should remove a like successfully', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';
      const mockResponse: VoteResponse = {
        content_id: contentId,
        vote_type: null,
        message: 'Like removed successfully'
      };

      service.removeLike(contentId).subscribe(response => {
        expect(response).toEqual(mockResponse);
        expect(loggingService.logInteraction).toHaveBeenCalledWith(
          'remove_like',
          { contentId }
        );
        expect(loggingService.logInteraction).toHaveBeenCalledWith(
          'like_removed',
          {
            contentId,
            message: 'Like removed successfully'
          }
        );
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/like`);
      expect(req.request.method).toBe('DELETE');
      req.flush(mockResponse);
    });

    it('should handle error when removing like', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';

      service.removeLike(contentId).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(500);
          expect(loggingService.logError).toHaveBeenCalledWith(
            'Failed to remove like',
            jasmine.any(Object)
          );
        }
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/like`);
      req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });
    });
  });

  describe('setDislike', () => {
    it('should set a dislike successfully', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';
      const mockResponse: VoteResponse = {
        content_id: contentId,
        vote_type: 'dislike',
        message: 'Dislike set successfully'
      };

      service.setDislike(contentId).subscribe(response => {
        expect(response).toEqual(mockResponse);
        expect(loggingService.logInteraction).toHaveBeenCalledWith(
          'vote_dislike',
          { contentId }
        );
        expect(loggingService.logInteraction).toHaveBeenCalledWith(
          'dislike_set',
          {
            contentId,
            message: 'Dislike set successfully'
          }
        );
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/dislike`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({});
      req.flush(mockResponse);
    });

    it('should handle error when setting dislike', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';

      service.setDislike(contentId).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(500);
          expect(loggingService.logError).toHaveBeenCalledWith(
            'Failed to set dislike',
            jasmine.any(Object)
          );
        }
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/dislike`);
      req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });
    });
  });

  describe('removeDislike', () => {
    it('should remove a dislike successfully', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';
      const mockResponse: VoteResponse = {
        content_id: contentId,
        vote_type: null,
        message: 'Dislike removed successfully'
      };

      service.removeDislike(contentId).subscribe(response => {
        expect(response).toEqual(mockResponse);
        expect(loggingService.logInteraction).toHaveBeenCalledWith(
          'remove_dislike',
          { contentId }
        );
        expect(loggingService.logInteraction).toHaveBeenCalledWith(
          'dislike_removed',
          {
            contentId,
            message: 'Dislike removed successfully'
          }
        );
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/dislike`);
      expect(req.request.method).toBe('DELETE');
      req.flush(mockResponse);
    });

    it('should handle error when removing dislike', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';

      service.removeDislike(contentId).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(500);
          expect(loggingService.logError).toHaveBeenCalledWith(
            'Failed to remove dislike',
            jasmine.any(Object)
          );
        }
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/dislike`);
      req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });
    });
  });

  describe('getUserVote', () => {
    it('should get the user vote for a content item', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';
      const mockResponse = {
        content_id: contentId,
        vote_type: 'like'
      };

      service.getUserVote(contentId).subscribe(response => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should handle null vote', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';
      const mockResponse = {
        content_id: contentId,
        vote_type: null
      };

      service.getUserVote(contentId).subscribe(response => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should handle error when getting user vote', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';

      service.getUserVote(contentId).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(404);
          expect(loggingService.logError).toHaveBeenCalledWith(
            'Failed to get user vote',
            jasmine.any(Object)
          );
        }
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}`);
      req.flush('Not found', { status: 404, statusText: 'Not Found' });
    });
  });

  describe('getUserVotesBatch', () => {
    it('should get user votes for multiple content items', () => {
      const contentIds = [
        '123e4567-e89b-12d3-a456-426614174000',
        '223e4567-e89b-12d3-a456-426614174001'
      ];
      const mockResponse = {
        '123e4567-e89b-12d3-a456-426614174000': 'like',
        '223e4567-e89b-12d3-a456-426614174001': 'dislike'
      };

      service.getUserVotesBatch(contentIds).subscribe(response => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/votes/batch`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(contentIds);
      req.flush(mockResponse);
    });

    it('should handle error when getting batch votes', () => {
      const contentIds = ['123e4567-e89b-12d3-a456-426614174000'];

      service.getUserVotesBatch(contentIds).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(500);
          expect(loggingService.logError).toHaveBeenCalledWith(
            'Failed to get user votes batch',
            jasmine.any(Object)
          );
        }
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/votes/batch`);
      req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });
    });
  });

  describe('getVoteStats', () => {
    it('should get vote statistics for a content item', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';
      const mockStats: VoteStats = {
        content_id: contentId,
        likes: 10,
        dislikes: 2,
        score: 0.833
      };

      service.getVoteStats(contentId).subscribe(stats => {
        expect(stats).toEqual(mockStats);
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/stats`);
      expect(req.request.method).toBe('GET');
      req.flush(mockStats);
    });

    it('should handle error when getting vote stats', () => {
      const contentId = '123e4567-e89b-12d3-a456-426614174000';

      service.getVoteStats(contentId).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(500);
          expect(loggingService.logError).toHaveBeenCalledWith(
            'Failed to get vote stats',
            jasmine.any(Object)
          );
        }
      });

      const req = httpMock.expectOne(`${environment.baseUrl}/api/v1/voting/content/${contentId}/stats`);
      req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });
    });
  });
});
