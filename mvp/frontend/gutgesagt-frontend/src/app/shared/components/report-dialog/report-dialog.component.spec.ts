import { MatDialogRef } from '@angular/material/dialog';

import { ReportDialogComponent } from './report-dialog.component';
import { ModerationService } from '../../../services/moderation.service';
import { ERFUNDENES_MELDEN } from '../../schreibregeln';

describe('ReportDialogComponent', () => {
  it('bietet den Grund an, auf den der Hinweis zu Erfundenem verweist', () => {
    const dialog = new ReportDialogComponent(
      {} as MatDialogRef<ReportDialogComponent>,
      { contentId: 'id', contentType: 'commentary' },
      {} as ModerationService,
    );

    const andere = dialog.reasons.find((grund) => grund.value === 'other')!;
    expect(ERFUNDENES_MELDEN).toContain(`„${andere.label}“`);
  });
});
