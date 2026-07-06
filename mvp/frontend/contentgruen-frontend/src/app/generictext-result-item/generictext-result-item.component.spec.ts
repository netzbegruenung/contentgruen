import { ComponentFixture, TestBed } from '@angular/core/testing';
import { GenerictextResultItemComponent } from './generictext-result-item.component';
import { GenerictextSearchResult } from '../services/dtos/searchDtos';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ContentStatus } from '../services/dtos/content-status-enum';
import { ContentOrigin } from '../services/dtos/content-origin-enum';
import { ContentVisibility } from '../services/dtos/content-visibility-enum';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { LoggingService } from '../services/logging.service';

describe('GenerictextResultItemComponent', () => {
  let component: GenerictextResultItemComponent;
  let fixture: ComponentFixture<GenerictextResultItemComponent>;

  const mockResult: GenerictextSearchResult = {
    score: 0.95,
    statement_text: 'Test statement',
    statement_similarity_score: 0.9,
    reply_relevance: 0.85,
    generictext_result: {
      id: 'test-id',
      text: 'Test text',
      content_type: 'generictext',
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
      references: [],
      references_count: 0,
      score: 0.95
    }
  };

  beforeEach(async () => {
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['logInteraction', 'logError', 'error', 'debug', 'info', 'warn']);

    await TestBed.configureTestingModule({
      imports: [
        GenerictextResultItemComponent,
        MatSnackBarModule,
        BrowserAnimationsModule,
        HttpClientTestingModule
      ],
      providers: [
        { provide: 'RESULT', useValue: mockResult },
        { provide: LoggingService, useValue: loggingSpy }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(GenerictextResultItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
