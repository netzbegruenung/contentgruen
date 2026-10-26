import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { ContentModerationComponent } from './content-moderation.component';
import { ContentReport, ModerationService } from '../../services/moderation.service';

function meldung(overrides: Partial<ContentReport> = {}): ContentReport {
  return {
    id: 'report-1',
    content_id: 'beitrag-1',
    content_type: 'commentary',
    reason: 'inappropriate',
    description: null,
    reported_by_user_id: null,
    reported_by_session_id: 'sess-123456789',
    created: '2026-10-26T10:00:00',
    status: 'pending',
    content: { status: 'released_internal', title: 'Titel', text: 'Text' },
    ...overrides
  };
}

describe('ContentModerationComponent', () => {
  let fixture: ComponentFixture<ContentModerationComponent>;
  let moderation: jasmine.SpyObj<ModerationService>;

  function mitMeldungen(meldungen: ContentReport[]) {
    moderation.getReports.and.returnValue(of({ total: meldungen.length, reports: meldungen }));
    fixture = TestBed.createComponent(ContentModerationComponent);
    fixture.detectChanges();
  }

  function knopf(text: string): HTMLButtonElement | undefined {
    const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((b) => b.textContent?.includes(text));
  }

  beforeEach(() => {
    moderation = jasmine.createSpyObj('ModerationService', ['getReports', 'sperren', 'entsperren', 'dismissReport']);
    moderation.sperren.and.returnValue(of({ success: true, message: '' }));
    moderation.entsperren.and.returnValue(of({ success: true, message: '' }));

    TestBed.configureTestingModule({
      imports: [ContentModerationComponent, NoopAnimationsModule],
      providers: [{ provide: ModerationService, useValue: moderation }]
    });
  });

  it('bietet zu einer offenen Meldung Sperren statt Löschen an', () => {
    mitMeldungen([meldung()]);

    expect(knopf('Sperren')).toBeTruthy();
    expect(knopf('Löschen')).toBeUndefined();
    expect(knopf('Entsperren')).toBeUndefined();
  });

  it('sperrt nach Rückfrage und lädt die Meldungen neu', () => {
    spyOn(window, 'confirm').and.returnValue(true);
    mitMeldungen([meldung()]);

    knopf('Sperren')!.click();

    expect(moderation.sperren).toHaveBeenCalledWith('beitrag-1');
    expect(moderation.getReports).toHaveBeenCalledTimes(2);
  });

  it('sperrt nicht, wenn die Rückfrage abgebrochen wird', () => {
    spyOn(window, 'confirm').and.returnValue(false);
    mitMeldungen([meldung()]);

    knopf('Sperren')!.click();

    expect(moderation.sperren).not.toHaveBeenCalled();
  });

  it('bietet zu einem gesperrten Beitrag Entsperren an', () => {
    mitMeldungen([meldung({ status: 'reviewed', content: { status: 'blocked', title: 'T', text: 'T' } })]);
    fixture.componentInstance.onStatusFilterChange('reviewed');
    fixture.detectChanges();

    expect(knopf('Sperren')).toBeUndefined();
    knopf('Entsperren')!.click();

    expect(moderation.entsperren).toHaveBeenCalledWith('beitrag-1');
  });

  it('nennt die Meldungsstufen wie das Glossar', () => {
    mitMeldungen([]);
    const c = fixture.componentInstance;

    expect([c.getStatusLabel('pending'), c.getStatusLabel('reviewed'), c.getStatusLabel('dismissed')])
      .toEqual(['Offen', 'Bearbeitet', 'Abgewiesen']);
  });
});
