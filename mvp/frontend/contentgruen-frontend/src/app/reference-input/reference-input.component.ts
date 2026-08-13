import {
    Component,
    Input,
    Output,
    EventEmitter,
    OnInit,
    OnDestroy,
    forwardRef,
    ViewChild,
    ElementRef
} from '@angular/core';
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
    // Ein einziges Beschreibungsfeld, das jeweils an der gerade bearbeiteten
    // Quelle eingeblendet wird - die Beschreibung gehoert an den Chip, nicht
    // ans Eingabefeld (dort wuerde sie sich auf die naechste Quelle beziehen).
    descriptionControl = new FormControl('');
    selectedReferences: ReferenceEntry[] = [];

    // Index der Quelle, deren Beschreibung gerade bearbeitet wird; null = keine.
    editingDescriptionIndex: number | null = null;

    // Der Setter feuert, sobald das eingeblendete Feld im DOM steht. Der Fokus
    // selbst muss aus der laufenden Change Detection heraus verschoben werden -
    // er aendert den Zustand des Material-Feldes.
    private focusDescriptionOnRender = false;

    @ViewChild('chipDescriptionInput')
    set chipDescriptionInput(field: ElementRef<HTMLInputElement> | undefined) {
        if (field && this.focusDescriptionOnRender) {
            this.focusDescriptionOnRender = false;
            setTimeout(() => field.nativeElement.focus());
        }
    }

    private destroy$ = new Subject<void>();
    // Verhindert, dass ein waehrend des Uebernehmens ausgeloester Blur ein
    // zweites Mal denselben Text uebernimmt.
    private isCommitting = false;
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
            this.cancelDescriptionEdit();
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

    /**
     * Nur das URL-Feld haengt an der Obergrenze. Das Beschreibungsfeld gehoert
     * zu den bereits gesetzten Quellen und muss auch bei 10/10 noch bedienbar
     * sein - sonst laesst sich die letzte Quelle nie mehr beschreiben.
     */
    private _syncInputDisabledState(): void {
        if (this.selectedReferences.length >= this.maxReferences) {
            this.urlControl.disable();
        } else {
            this.urlControl.enable();
        }
    }

    // Component methods

    addCustomReference(): void {
        if (this.isCommitting) {
            return;
        }

        const url = this.urlControl.value?.trim();

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

        this.isCommitting = true;
        try {
            // Show immediate feedback
            this.snackBar.open('Referenz wird hinzugefügt...', '', {
                duration: 0,  // Keep open until replaced
                panelClass: ['info-snackbar']
            });

            // Add reference immediately with temporary ID and pending state.
            // Neue Quellen entstehen ohne Beschreibung; die wird bei Bedarf
            // nachtraeglich am Chip ergaenzt.
            const tempRef: ReferenceEntry = {
                id: 'temp-' + Date.now(),
                reference_string: url,
                is_new: true,
                isPending: true
            };
            this.addReference(tempRef);
            this.clearInputs();

            // Check server for global duplicates and add reference
            this.checkAndAddReference(url, undefined, tempRef);
        } finally {
            this.isCommitting = false;
        }
    }

    /**
     * Uebernimmt den noch im Eingabefeld stehenden Text als Quelle.
     *
     * Laeuft synchron: Chip und Formularwert stehen sofort, der Server-Roundtrip
     * laeuft im Hintergrund weiter. Die Eltern-Formulare rufen das vor dem
     * Speichern auf, damit eine getippte, aber nicht bestaetigte Quelle nicht
     * stumm verloren geht.
     *
     * Uebernimmt ausserdem eine offen stehende Beschreibung am Chip - sonst
     * ginge die dritte Variante desselben stillen Verlusts durch: Text getippt,
     * Feld noch offen, gespeichert.
     *
     * @returns true, wenn dadurch noch etwas uebernommen wurde
     */
    flushPendingInput(): boolean {
        const descriptionAdopted = this.commitDescriptionEdit();
        const countBefore = this.selectedReferences.length;
        this.addCustomReference();
        return this.selectedReferences.length > countBefore || descriptionAdopted;
    }

    /**
     * Blur uebernimmt die Eingabe - ausser der Fokus wandert innerhalb der
     * Komponente an eine Stelle, die nichts uebernehmen soll: in die Liste der
     * bereits gesetzten Quellen mit ihren Entfernen-Buttons, Beschreibung-
     * Buttons und Beschreibungsfeldern.
     */
    onInputBlur(event: FocusEvent): void {
        const nextFocus = event.relatedTarget as HTMLElement | null;
        if (nextFocus && nextFocus.closest('.no-commit-zone')) {
            return;
        }
        this.addCustomReference();
    }

    /**
     * Blendet das Beschreibungsfeld an der angegebenen Quelle ein - vorhandener
     * Text steht darin und ist editierbar.
     */
    startDescriptionEdit(index: number): void {
        // Ein eventuell woanders offenes Feld zuerst uebernehmen.
        this.commitDescriptionEdit();

        const reference = this.selectedReferences[index];
        if (!reference) {
            return;
        }

        this.editingDescriptionIndex = index;
        this.descriptionControl.setValue(reference.description ?? '');
        this.focusDescriptionOnRender = true;
    }

    /**
     * Schreibt die offene Beschreibung an ihre Quelle zurueck und schliesst das
     * Feld.
     *
     * @returns true, wenn dadurch eine Beschreibung geaendert wurde
     */
    commitDescriptionEdit(): boolean {
        const index = this.editingDescriptionIndex;
        if (index === null) {
            return false;
        }

        const reference = this.selectedReferences[index];
        this.editingDescriptionIndex = null;
        // Leere Beschreibung nicht als leeren String weiterreichen
        const description = this.descriptionControl.value?.trim() || undefined;
        this.descriptionControl.setValue('');

        if (!reference || reference.description === description) {
            return false;
        }

        reference.description = description;
        this.updateFormValue();
        return true;
    }

    /** Schliesst das Beschreibungsfeld, ohne die Aenderung zu uebernehmen. */
    cancelDescriptionEdit(): void {
        this.editingDescriptionIndex = null;
        this.descriptionControl.setValue('');
    }

    onDescriptionKeydown(event: KeyboardEvent): void {
        if (event.key === 'Enter') {
            event.preventDefault();
            this.commitDescriptionEdit();
        } else if (event.key === 'Escape') {
            event.preventDefault();
            this.cancelDescriptionEdit();
        }
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
        // Das offene Beschreibungsfeld haengt an einem Index - beim Entfernen
        // darf es nicht auf die falsche Quelle rutschen.
        if (this.editingDescriptionIndex === index) {
            this.cancelDescriptionEdit();
        } else if (this.editingDescriptionIndex !== null && this.editingDescriptionIndex > index) {
            this.editingDescriptionIndex--;
        }

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
