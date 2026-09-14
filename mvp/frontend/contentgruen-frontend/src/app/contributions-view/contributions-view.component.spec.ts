import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { ContributionsViewComponent } from './contributions-view.component';
import { ContributionsService } from '../services/contributions.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';

describe('ContributionsViewComponent', () => {
  let fixture: ComponentFixture<ContributionsViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContributionsViewComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        {
          provide: ContributionsService,
          useValue: {
            getContributions: () =>
              of({
                results_count: 1,
                total_records_count: 1,
                results: [
                  {
                    id: 'b1',
                    created: '2026-09-13T21:05:00',
                    last_modified: '2026-09-13T21:05:00',
                    original_author: 'person-1',
                    last_modified_by: 'person-1',
                    edit_history: {},
                    text: 'Wärmepumpe lohnt sich auch im Altbau',
                    content_type: 'generic_text',
                    score: 0,
                  },
                ],
              }),
          },
        },
        { provide: UsageTrackingService, useValue: { getUserUsageStats: () => of(null) } },
        { provide: AuthService, useValue: { getCurrentUserId: () => null } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContributionsViewComponent);
    fixture.detectChanges();
  });

  function text(selektor: string): string {
    return (fixture.nativeElement.querySelector(selektor) as HTMLElement).textContent!
      .replace(/\s+/g, ' ')
      .trim();
  }

  it('beschriftet den Paginator auf Deutsch', () => {
    expect(text('.mat-mdc-paginator-page-size-label')).toBe('Einträge pro Seite:');
    expect(text('.mat-mdc-paginator-range-label')).toBe('1 – 1 von 1');
  });

  it('zeigt den deutschen Typnamen und die Uhrzeit im 24-Stunden-Format', () => {
    const zeile = text('tr.mat-mdc-row');
    expect(zeile).toContain('Hintergrundinfo');
    expect(zeile).toContain('13.09.2026, 21:05');
  });
});
