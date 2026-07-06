import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CommentaryResultItemComponent } from './commentary-result-item.component';
import { CommentarySearchResult } from '../services/dtos/searchDtos';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ContentStatus } from '../services/dtos/content-status-enum';
import { ContentOrigin } from '../services/dtos/content-origin-enum';
import { ContentVisibility } from '../services/dtos/content-visibility-enum';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('CommentaryResultItemComponent', () => {
  let component: CommentaryResultItemComponent;
  let fixture: ComponentFixture<CommentaryResultItemComponent>;

  const mockResult: CommentarySearchResult = {
    score: 0.95,
    statement_text: 'Test statement',
    statement_similarity_score: 0.9,
    reply_relevance: 0.85,
    commentary_result: {
      id: 'test-id',
      text: 'Test text',
      content_type: 'commentary',
      created: new Date().toISOString(),
      last_modified: new Date().toISOString(),
      original_author: 'Test Author',
      last_modified_by: 'Test Author',
      authors: [],
      edit_history: [],
      status: ContentStatus.APPROVED,
      origin: ContentOrigin.MANUALLY_CREATED,
      most_similar_similarity_score: 0,
      most_similar_content_id: '',
      report_count: 0,
      is_archived: false,
      report_flagged: false,
      rejection_reason: '',
      block_reason: '',
      visibility: ContentVisibility.VISIBLE,
      title: 'Test Title',
      long_text: 'Long text',
      short_text: 'Short text',
      references: [],
      references_count: 0,
      score: 0.95,
      usage_count: 0
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        CommentaryResultItemComponent,
        MatSnackBarModule,
        BrowserAnimationsModule,
        HttpClientTestingModule
      ],
      providers: [
        { provide: 'RESULT', useValue: mockResult }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CommentaryResultItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Mobile Badge Display', () => {
    it('should show new badge for content created within 24 hours', () => {
      const recentDate = new Date();
      recentDate.setHours(recentDate.getHours() - 12); // 12 hours ago

      const recentResult = { ...mockResult };
      recentResult.commentary_result.created = recentDate.toISOString();

      component.result_input = recentResult;
      component.ngOnInit();

      expect(component.showNewBadge).toBeTruthy();
    });

    it('should not show new badge for content older than 24 hours', () => {
      const oldDate = new Date();
      oldDate.setHours(oldDate.getHours() - 48); // 48 hours ago

      const oldResult = { ...mockResult };
      oldResult.commentary_result.created = oldDate.toISOString();

      component.result_input = oldResult;
      component.ngOnInit();

      expect(component.showNewBadge).toBeFalsy();
    });

    it('should show trending badge for content with 5 or more uses', () => {
      const trendingResult = { ...mockResult };
      trendingResult.commentary_result.usage_count = 5;

      component.result_input = trendingResult;
      component.ngOnInit();

      expect(component.showTrendingBadge).toBeTruthy();
    });

    it('should not show trending badge for content with less than 5 uses', () => {
      const notTrendingResult = { ...mockResult };
      notTrendingResult.commentary_result.usage_count = 3;

      component.result_input = notTrendingResult;
      component.ngOnInit();

      expect(component.showTrendingBadge).toBeFalsy();
    });

    it('should toggle new badge expansion state on click', () => {
      const event = new Event('click');
      expect(component.expandedNewBadge).toBeFalsy();

      component.toggleNewBadge(event);
      expect(component.expandedNewBadge).toBeTruthy();

      component.toggleNewBadge(event);
      expect(component.expandedNewBadge).toBeFalsy();
    });

    it('should auto-collapse expanded badge after 3 seconds', (done) => {
      const event = new Event('click');
      component.toggleNewBadge(event);
      expect(component.expandedNewBadge).toBeTruthy();

      setTimeout(() => {
        expect(component.expandedNewBadge).toBeFalsy();
        done();
      }, 3100);
    });
  });
});
