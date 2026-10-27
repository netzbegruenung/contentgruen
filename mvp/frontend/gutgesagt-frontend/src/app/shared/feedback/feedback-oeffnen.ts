import { MatDialog } from '@angular/material/dialog';
import { FeedbackDialogComponent } from './feedback-dialog.component';

/** Oeffnet das Feedback-Formular; derselbe Aufruf im Desktop-Kopf und im mobilen Menue. */
export function oeffneFeedback(dialog: MatDialog) {
  return dialog.open(FeedbackDialogComponent, {
    width: '560px',
    maxWidth: '95vw',
    autoFocus: 'first-tabbable',
  });
}
