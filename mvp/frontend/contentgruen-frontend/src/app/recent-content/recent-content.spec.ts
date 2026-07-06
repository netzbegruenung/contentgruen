import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { RecentContentComponent } from './recent-content.component';
import { ContentService } from '../services/content.service';
import { LoggingService } from '../services/logging.service';

describe('RecentContentComponent', () => {
  let component: RecentContentComponent;
  let fixture: ComponentFixture<RecentContentComponent>;
  let contentService: jasmine.SpyObj<ContentService>;
  let loggingService: jasmine.SpyObj<LoggingService>;

  beforeEach(async () => {
    const contentServiceSpy = jasmine.createSpyObj('ContentService', ['getRecentContent']);
    const loggingServiceSpy = jasmine.createSpyObj('LoggingService', ['info', 'error', 'debug']);

    await TestBed.configureTestingModule({
      imports: [RecentContentComponent, HttpClientTestingModule],
      providers: [
        { provide: ContentService, useValue: contentServiceSpy },
        { provide: LoggingService, useValue: loggingServiceSpy }
      ]
    })
    .compileComponents();

    contentService = TestBed.inject(ContentService) as jasmine.SpyObj<ContentService>;
    loggingService = TestBed.inject(LoggingService) as jasmine.SpyObj<LoggingService>;

    // Mock the getRecentContent to return empty results
    contentService.getRecentContent.and.returnValue(of({ results: [], results_count: 0 }));

    fixture = TestBed.createComponent(RecentContentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
