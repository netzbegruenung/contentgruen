import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface DuplicateDialogData {
  referenceString: string;
  existingDescription?: string;
  newDescription?: string;
}

@Component({
  selector: 'app-reference-duplicate-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    FormsModule
  ],
  templateUrl: './reference-duplicate-dialog.html',
  styleUrl: './reference-duplicate-dialog.css'
})
export class ReferenceDuplicateDialog {
  editableDescription: string;

  constructor(
    public dialogRef: MatDialogRef<ReferenceDuplicateDialog>,
    @Inject(MAT_DIALOG_DATA) public data: DuplicateDialogData
  ) {
    // Initialize with the new description or empty string
    this.editableDescription = data.newDescription || '';
  }

  useExisting(): void {
    this.dialogRef.close({ action: 'use-existing' });
  }

  useNew(): void {
    // Return the edited description
    this.dialogRef.close({
      action: 'use-new',
      description: this.editableDescription
    });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
