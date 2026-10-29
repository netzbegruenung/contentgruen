import { MatDialogRef } from '@angular/material/dialog';
import { of } from 'rxjs';

import { ReportDialogComponent } from './report-dialog.component';
import { ModerationService } from '../../../services/moderation.service';
import { ERFUNDENES_MELDEN } from '../../schreibregeln';

describe('ReportDialogComponent', () => {
  function dialog(moderation = {} as ModerationService): ReportDialogComponent {
    return new ReportDialogComponent(
      { close: () => {} } as MatDialogRef<ReportDialogComponent>,
      { contentId: 'id', contentType: 'commentary' },
      moderation,
    );
  }

  it('bietet „Erfunden oder sachlich falsch“ als Meldegrund an', () => {
    const grund = dialog().reasons.find((g) => g.value === 'fabricated_or_false');

    expect(grund?.label).toBe('Erfunden oder sachlich falsch');
  });

  it('nennt die Dublette nach dem Glossar', () => {
    const grund = dialog().reasons.find((g) => g.value === 'duplicate');

    expect(grund?.label).toBe('Dublette');
  });

  it('bietet den Grund an, auf den der Hinweis zu Erfundenem verweist', () => {
    const grund = dialog().reasons.find((g) => g.value === 'fabricated_or_false')!;

    expect(ERFUNDENES_MELDEN).toContain(`„${grund.label}“`);
    expect(ERFUNDENES_MELDEN).not.toContain('„Andere“');
  });

  it('sendet den gewählten Grund', () => {
    const moderation = jasmine.createSpyObj<ModerationService>('ModerationService', ['reportContent']);
    moderation.reportContent.and.returnValue(of({ success: true, message: '' }));
    const komponente = dialog(moderation);

    komponente.selectedReason = 'fabricated_or_false';
    komponente.description = 'Die Zahl stimmt nicht';
    komponente.submitReport();

    expect(moderation.reportContent).toHaveBeenCalledWith(
      'id',
      'commentary',
      'fabricated_or_false',
      'Die Zahl stimmt nicht',
    );
  });
});
