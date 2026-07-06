import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, forwardRef } from '@angular/core';
import { FormControl, NG_VALUE_ACCESSOR, ControlValueAccessor } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ReferenceService } from '../services/reference.service';
import { AddReferenceResponse } from '../services/dtos/referenceDtos';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { CommonModule } from '@angular/common';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { ReferenceDuplicateDialog } from '../reference-duplicate-dialog/reference-duplicate-dialog';

export interface ReferenceEntry {
    id?: string;
    reference_string: string;
    description?: string;
    is_new?: boolean;
    isPending?: boolean;
}

@Component({
    selector: 'app-reference-input',
    standalone: true,
    imports: [
        ...SHARED_IMPORTS,
        CommonModule,
        MatChipsModule,
        MatIconModule,
        MatProgressSpinnerModule
    ],
    templateUrl: './reference-input.component.html',
    styleUrls: ['./reference-input.component.css'],
    providers: [
        {
            provide: NG_VALUE_ACCESSOR,
            useExisting: forwardRef(() => ReferenceInputComponent),
            multi: true
        }
    ]
})
export class ReferenceInputComponent implements OnInit, OnDestroy, ControlValueAccessor {
    @Input() maxReferences = 10;
    @Output() referenceAdded = new EventEmitter<ReferenceEntry>();
    @Output() referenceRemoved = new EventEmitter<ReferenceEntry>();

    urlControl = new FormControl('');
    descriptionControl = new FormControl('');
    selectedReferences: ReferenceEntry[] = [];

    private destroy$ = new Subject<void>();
    private onChange: (value: any[]) => void = () => {};
    private onTouched: () => void = () => {};

    constructor(
        private referenceService: ReferenceService,
        private snackBar: MatSnackBar,
        private dialog: MatDialog
    ) {
        // No initialization needed
    }

    ngOnInit(): void {
        // No initialization needed
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    // ControlValueAccessor implementation
    writeValue(value: any[]): void {
        if (value && Array.isArray(value)) {
            // Handle both string array (legacy) and object array
            this.selectedReferences = value.map(ref => {
                if (typeof ref === 'string') {
                    // Legacy format - just strings
                    return {
                        reference_string: ref,
                        description: undefined,
                        is_new: true
                    };
                } else {
                    // New format - objects with reference_string and description
                    return {
                        reference_string: ref.reference_string,
                        description: ref.description,
                        is_new: true
                    };
                }
            });
            this._syncInputDisabledState();
        }
    }

    registerOnChange(fn: (value: any[]) => void): void {
        this.onChange = fn;
    }

    registerOnTouched(fn: () => void): void {
        this.onTouched = fn;
    }

    setDisabledState(isDisabled: boolean): void {
        if (isDisabled) {
            this.urlControl.disable();
            this.descriptionControl.disable();
        } else {
            this.urlControl.enable();
            this.descriptionControl.enable();
        }
    }

    private _syncInputDisabledState(): void {
        if (this.selectedReferences.length >= this.maxReferences) {
            this.urlControl.disable();
            this.descriptionControl.disable();
        } else {
            this.urlControl.enable();
            this.descriptionControl.enable();
        }
    }

    // Component methods

    addCustomReference(): void {
        const url = this.urlControl.value?.trim();
        const description = this.descriptionControl.value?.trim();

        // Validate input
        if (!this.isValidInput(url)) {
            return;
        }

        // TypeScript guard: url is now guaranteed to be string
        if (!url) {
            return;
        }

        // Check for local duplicates
        if (this.hasLocalDuplicate(url)) {
            this.showDuplicateWarning();
            return;
        }

        // Show immediate feedback
        this.snackBar.open('Referenz wird hinzugefügt...', '', {
            duration: 0,  // Keep open until replaced
            panelClass: ['info-snackbar']
        });

        // Add reference immediately with temporary ID and pending state
        const tempRef: ReferenceEntry = {
            id: 'temp-' + Date.now(),
            reference_string: url,
            description: description,
            is_new: true,
            isPending: true
        };
        this.addReference(tempRef);
        this.clearInputs();

        // Check server for global duplicates and add reference
        this.checkAndAddReference(url, description, tempRef);
    }

    private isValidInput(url: string | undefined): boolean {
        if (!url || url.length === 0) {
            return false;
        }

        // Check if it's a valid URL or has minimum length
        return this.referenceService.isValidUrl(url) || url.length >= 5;
    }

    private hasLocalDuplicate(url: string): boolean {
        return this.selectedReferences.some(
            ref => ref.reference_string.toLowerCase() === url.toLowerCase()
        );
    }

    private showDuplicateWarning(): void {
        this.snackBar.open('Diese Referenz wurde bereits hinzugefügt', 'OK', {
            duration: 3000,
            panelClass: ['warning-snackbar']
        });
    }

    private checkAndAddReference(url: string, description: string | undefined, tempRef?: ReferenceEntry): void {
        // Use simplified add endpoint that checks for duplicates
        this.referenceService.addReference({
            reference_string: url,
            text: description || url  // Use text field instead of description
        })
            .pipe(takeUntil(this.destroy$))
            .subscribe(
                (response: AddReferenceResponse) => {
                    if (tempRef) {
                        // Update the temp reference with real data
                        const index = this.selectedReferences.findIndex(r => r.id === tempRef.id);
                        if (index !== -1) {
                            this.selectedReferences[index] = {
                                ...tempRef,
                                id: response.id,
                                isPending: false,
                                is_new: response.was_new
                            };
                            this.updateFormValue();
                        }
                        // Dismiss the loading snackbar and show success message
                        this.snackBar.dismiss();
                        this.showReferenceAddedFeedback(!response.was_new);
                    } else {
                        // Fallback to old behavior if no tempRef provided
                        this.showReferenceAddedFeedback(!response.was_new);
                        this.addReference({
                            id: response.id,
                            reference_string: url,
                            description: description,
                            is_new: response.was_new
                        });
                    }
                },
                (error) => {
                    if (tempRef) {
                        // Remove the temp reference on error
                        const index = this.selectedReferences.findIndex(r => r.id === tempRef.id);
                        if (index !== -1) {
                            this.selectedReferences.splice(index, 1);
                            this.updateFormValue();
                        }
                        // Dismiss loading snackbar and show error
                        this.snackBar.dismiss();
                    }
                    this.snackBar.open('Fehler beim Hinzufügen der Referenz', 'OK', {
                        duration: 3000,
                        panelClass: ['error-snackbar']
                    });
                    console.error('Error adding reference:', error);
                }
            );
    }

    private showDuplicateDialog(response: AddReferenceResponse, url: string, newDescription?: string): void {
        const dialogRef = this.dialog.open(ReferenceDuplicateDialog, {
            width: '600px',
            data: {
                referenceString: url,
                existingDescription: undefined,  // No longer available
                newDescription: newDescription
            },
            hasBackdrop: true,
            backdropClass: 'cdk-overlay-dark-backdrop',
            panelClass: 'custom-dialog-container',
            autoFocus: false,
            restoreFocus: false
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result && result.action === 'use-existing') {
                // User wants to keep existing description
                this.addReference({
                    id: response.id,
                    reference_string: url,
                    description: newDescription,  // Use the new description locally
                    is_new: false
                });
                this.clearInputs();
                this.snackBar.open('✓ Referenz hinzugefügt', 'OK', {
                    duration: 3000,
                    panelClass: ['success-snackbar']
                });
            } else if (result && result.action === 'use-new') {
                // User wants to use the new description
                const finalDescription = result.description;

                // Add the reference to the list
                this.addReference({
                    id: response.id,
                    reference_string: url,
                    description: finalDescription,
                    is_new: false
                });
                this.clearInputs();
            }
            // If result is null, user cancelled - do nothing
        });
    }

    private showReferenceAddedFeedback(isDuplicate: boolean): void {
        if (isDuplicate) {
            this.snackBar.open(
                '✓ Existierende Referenz wird wiederverwendet',
                'OK',
                {
                    duration: 3000,
                    panelClass: ['success-snackbar']
                }
            );
        } else {
            this.snackBar.open(
                '+ Neue Referenz wird erstellt',
                'OK',
                {
                    duration: 2000,
                    panelClass: ['info-snackbar']
                }
            );
        }
    }

    private clearInputs(): void {
        this.urlControl.setValue('');
        this.descriptionControl.setValue('');
    }

    private addReference(reference: ReferenceEntry): void {
        if (this.selectedReferences.length >= this.maxReferences) {
            return;
        }

        // Check for duplicates
        const isDuplicate = this.selectedReferences.some(
            ref => ref.reference_string.toLowerCase() === reference.reference_string.toLowerCase()
        );

        if (!isDuplicate) {
            this.selectedReferences.push(reference);
            this.updateFormValue();
            this._syncInputDisabledState();
            this.referenceAdded.emit(reference);
        }
    }

    removeReference(index: number): void {
        const removed = this.selectedReferences.splice(index, 1)[0];
        this.updateFormValue();
        this._syncInputDisabledState();
        this.referenceRemoved.emit(removed);
    }

    private updateFormValue(): void {
        // Send full reference objects with both string and description
        const values = this.selectedReferences.map(ref => ({
            reference_string: ref.reference_string,
            description: ref.description
        }));

        this.onChange(values);
        this.onTouched();
    }


    onInputKeydown(event: KeyboardEvent): void {
        if (event.key === 'Enter') {
            event.preventDefault();
            this.addCustomReference();
        }
    }
}
