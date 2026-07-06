import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AddImageComponent } from '../add-image/add-image.component';
import { ContentRefreshService } from '../services/content-refresh.service';
import { LoggingService } from '../services/logging.service';

@Component({
  standalone: true,
  selector: 'app-add-image-workflow',
  templateUrl: './add-image-workflow.component.html',
  styleUrls: ['./add-image-workflow.component.css'],
  imports: [
    CommonModule,
    AddImageComponent,
  ],
})
export class AddImageWorkflowComponent {
  constructor(
    private router: Router,
    private logger: LoggingService,
    private contentRefreshService: ContentRefreshService,
    private snackBar: MatSnackBar,
  ) {}

  onSuccess(responseId: string): void {
    this.contentRefreshService.triggerRefresh();

    const snackBarRef = this.snackBar.open(
      'Vielen Dank! Dein Bild hilft der gesamten Community. Du kannst deine Beiträge und deren Nutzung auf der "Meine Beiträge" Seite verfolgen.',
      'Meine Beiträge ansehen',
      {
        duration: 8000,
        horizontalPosition: 'center',
        verticalPosition: 'bottom',
        panelClass: ['success-snackbar'],
      },
    );

    snackBarRef.onAction().subscribe(() => {
      this.router.navigate(['/contributions']);
    });

    this.router.navigate(['/contribute']);
  }

  onCancel(): void {
    this.router.navigate(['/contribute']);
  }
}
