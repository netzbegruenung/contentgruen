import { Component, Input, Output, EventEmitter, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { trigger, transition, style, animate } from '@angular/animations';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { GenericTextService } from '../services/generic-text.service';
import { StatementService } from '../services/statement.service';
import { LoggingService } from '../services/logging.service';
import { AddGenericTextRequest, AddGenericTextResponse } from '../services/dtos/generictextDtos';
import { AddReplysuggestionToStatementRequest, AddReplysuggestionToStatementResponse } from '../services/dtos/statementDtos';
import { GenerictextSearchResult } from '../services/dtos/searchDtos';
import { GenerictextResultItemComponent } from '../generictext-result-item/generictext-result-item.component';
import { ReferenceInputComponent, ReferenceEntry } from '../reference-input/reference-input.component';
import { ContentStatus } from '../services/dtos/content-status-enum';
import { ContentOrigin } from '../services/dtos/content-origin-enum';
import { ContentVisibility } from '../services/dtos/content-visibility-enum';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil, debounceTime } from 'rxjs/operators';


interface GenericTextFormValues {
    title: string;
    text: string;
    references: string[];
}

@Component({
    selector: 'app-add-generictext',
    standalone: true,
    imports: [
        ...SHARED_IMPORTS,
        CommonModule,
        FormsModule,
        MatSlideToggleModule,
        GenerictextResultItemComponent,
        ReferenceInputComponent
    ],
    templateUrl: './add-generictext.component.html',
    styleUrls: ['./add-generictext.component.scss'],
    providers: [
        { provide: 'RESULT', useValue: null }
    ],
    animations: [
        trigger('expandCollapse', [
            transition(':enter', [
                style({ height: '0', opacity: 0, overflow: 'hidden' }),
                animate('300ms cubic-bezier(0.4, 0, 0.2, 1)', style({ height: '*', opacity: 1 })),
            ]),
            transition(':leave', [
                style({ overflow: 'hidden' }),
                animate('200ms cubic-bezier(0.4, 0, 0.2, 1)', style({ height: '0', opacity: 0 })),
            ]),
        ]),
    ]
})
export class AddGenerictextComponent implements OnDestroy {
    @Input() statementText: string = '';
    @Input() statementId: string = '';
    @Output() success = new EventEmitter<string>();
    @Output() cancel = new EventEmitter<void>();
    @ViewChild('successContainer', { read: ElementRef }) successContainer?: ElementRef;
    @ViewChild('loadingContainer', { read: ElementRef }) loadingContainer?: ElementRef;
    @ViewChild(ReferenceInputComponent) referenceInput?: ReferenceInputComponent;

    private destroy$ = new Subject<void>();

    generictextForm: FormGroup;
    previewResult: GenerictextSearchResult | null = null;

    generictextLoading = false;
    generictextSaved = false;

    generictextError: string | null = null;
    responseId: string = '';

    // New properties for inline statement handling
    isReplyToStatement: boolean = false;
    statementInput: string = '';
    private statementUpdateSubject = new Subject<string>();

    // Sources start hidden to keep the initial form minimal.
    // NOTE: if an edit mode is added later, initialise this from the loaded values
    // (e.g. showReferences = references.length > 0) so filled fields stay visible.
    showReferences = false;

    constructor(
        private fb: FormBuilder,
        private genericTextService: GenericTextService,
        private statementService: StatementService,
        private logger: LoggingService,
        private router: Router
    ) {
        this.generictextForm = this.fb.group({
            title: ['', [Validators.required, Validators.minLength(3)]],
            text: ['', [Validators.required, Validators.minLength(10)]],
            references: [[]]  // Changed from FormArray to simple array control
        });

        // Listen to form changes to update the preview dynamically
        this.generictextForm.valueChanges
            .pipe(takeUntil(this.destroy$))
            .subscribe((formValues) => {
                this.updatePreview(formValues);
            });

        // Initialize preview with form values
        this.updatePreview(this.generictextForm.value);

        // Set initial state based on whether we have a statement
        if (this.statementText) {
            this.isReplyToStatement = true;
            this.statementInput = this.statementText;
        }

        // Debounce statement input changes
        this.statementUpdateSubject
            .pipe(
                takeUntil(this.destroy$),
                debounceTime(500)
            )
            .subscribe(text => {
                if (text && text.trim()) {
                    this.findOrCreateStatement(text.trim());
                }
            });
    }

    // Handle reference changes from autocomplete component
    onReferenceAdded(reference: ReferenceEntry): void {
        // Reference added event - handled by form control
    }

    onReferenceRemoved(reference: ReferenceEntry): void {
        // Reference removed event - handled by form control
    }

    // One-way reveal: re-creating app-reference-input would drop the server ids of
    // already added references, so the section stays open once it has been opened.
    revealReferences(): void {
        this.showReferences = true;
    }

    updatePreview(formValues: GenericTextFormValues): void {
        // Create or update preview result
        this.previewResult = {
            score: 1.0,
            statement_text: '',
            statement_similarity_score: 0,
            reply_relevance: 0,
            generictext_result: {
                id: 'preview',
                title: formValues.title || 'Titel eingeben...',
                text: formValues.text || 'Text eingeben...',
                references: formValues.references?.map((ref: any, index: number) => ({
                    reference_id: 'preview-' + index,
                    created: new Date().toISOString(),
                    reference_text: typeof ref === 'string' ? ref : ref.reference_string,
                    reference_description: typeof ref === 'string' ? '' : (ref.description || '')
                })) || [],
                created: new Date().toISOString(),
                last_modified: new Date().toISOString(),
                original_author: 'Du',
                last_modified_by: 'Du',
                authors: [{
                    name: 'Du',
                    role: 'author'
                }],
                edit_history: [],
                content_type: 'generic_text',
                status: ContentStatus.APPROVED,
                visibility: ContentVisibility.VISIBLE,
                origin: ContentOrigin.MANUALLY_CREATED,
                score: 1.0,
                most_similar_similarity_score: 0,
                most_similar_content_id: '',
                report_count: 0,
                is_archived: false,
                report_flagged: false,
                rejection_reason: '',
                block_reason: '',
                usage_count: 0,
                references_count: formValues.references?.length || 0
            }
        } as GenerictextSearchResult;
    }

    // New inline methods for statement handling
    toggleReplyType(isReply: boolean): void {
        this.isReplyToStatement = isReply;
        if (!isReply) {
            this.clearStatement();
        }
    }

    updateStatement(): void {
        if (this.statementInput && this.statementInput.trim()) {
            this.statementUpdateSubject.next(this.statementInput);
        }
    }

    clearStatement(): void {
        this.statementText = '';
        this.statementId = '';
        this.statementInput = '';
    }

    findOrCreateStatement(text: string): void {
        this.logger.debug('Finding or creating statement:', text);

        this.statementService.findOrCreateStatement(text).subscribe({
            next: (response) => {
                this.statementId = response.statement_id;
                this.statementText = response.statement_text;

                if (response.statement_was_new) {
                    this.logger.info('Created new statement with ID:', response.statement_id);
                } else {
                    this.logger.info('Using existing statement with ID:', response.statement_id);
                }
            },
            error: (error) => {
                this.logger.error('Error finding or creating statement', error);
                this.generictextError = 'Fehler beim Erstellen des Statements.';
            }
        });
    }

    removeStatement(): void {
        this.clearStatement();
        this.isReplyToStatement = false;
        this.logger.debug('Statement removed');
    }

    reset() {
        this.responseId = '';
        this.generictextSaved = false;
        this.generictextError = null;
        this.showReferences = false;
        this.generictextForm.reset();
        this.updatePreview(this.generictextForm.value);
    }

    navigateBack(): void {
        this.cancel.emit();
    }

    navigateToGenerictext(id: string): void {
        // Navigate to search page with query param to trigger refresh and fragment to scroll
        this.router.navigate(['/search'], {
            queryParams: { refresh: 'true' },
            fragment: 'recent-content'
        });
    }


    saveGenericTextForm() {
        // Noch nicht bestaetigte Quelleneingabe uebernehmen, bevor der Formularwert
        // gelesen wird - sonst geht sie beim Speichern stumm verloren.
        this.referenceInput?.flushPendingInput();

        if (this.generictextForm.valid) {
            const formValues = this.generictextForm.value;

            // Manually parse form values into an AddGenericTextRequest object
            const requestPayload: AddGenericTextRequest = {
                generictext: {
                    title: formValues.title,
                    text: formValues.text
                },
                references: formValues.references || []  // Send references separately like commentary
            };

            this.generictextLoading = true;
            this.responseId = '';
            this.scrollToLoadingOrSuccess();
            this.generictextError = null;

            this.logger.debug('Submitting generic text:', requestPayload);


            // Call the service to add generictext
            this.genericTextService.addGenericText(requestPayload).subscribe({
                next: (response: AddGenericTextResponse) => {
                    this.logger.info('Generic text added successfully:', response);

                    if (this.statementText && this.statementId) {
                        const addReplysuggestionToStatementRequest: AddReplysuggestionToStatementRequest = {
                            statement_id: this.statementId,
                            replysuggestion_id: response.id,
                            content_type: 'generic_text',
                            relevance: 0.9
                        };

                        // Call the service to link the replysuggestion to a statement
                        this.statementService.addReplysuggestionToStatement(addReplysuggestionToStatementRequest).subscribe({
                            next: (linkResponse: AddReplysuggestionToStatementResponse) => {
                                this.logger.info('Generic text linked to statement successfully');
                            },
                            error: (error) => {
                                this.logger.warn('Failed to link generic text to statement, but text was saved', error);
                                // Don't show error since the main operation succeeded
                            }
                        });
                    }

                    this.generictextLoading = false;
                    this.generictextSaved = true;
                    this.responseId = response.id;

                    // Emit success event
                    setTimeout(() => {
                        this.success.emit(response.id);
                    }, 2000);
                },
                error: (error) => {
                    this.logger.error('Error saving generic text', error);
                    this.generictextLoading = false;
                    this.generictextError = 'Fehler beim Speichern des Textbeitrags. Bitte überprüfe deine Internetverbindung und versuche es erneut.';
                }
            });
        } else {
            this.logger.warn('Form is invalid', this.generictextForm.errors);
            // Mark all fields as touched to show validation errors
            Object.keys(this.generictextForm.controls).forEach(key => {
                this.generictextForm.get(key)?.markAsTouched();
            });
        }
    }

    private scrollToLoadingOrSuccess(): void {
        // Immediately scroll to loading or success container
        setTimeout(() => {
            // First priority: loading container when form is being submitted
            if (this.generictextLoading && this.loadingContainer) {
                this.loadingContainer.nativeElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
            // Second priority: success container after submission
            else if (this.successContainer) {
                this.successContainer.nativeElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }, 100);
    }

    ngOnDestroy(): void {
        this.statementUpdateSubject.complete();
        this.destroy$.next();
        this.destroy$.complete();
    }
}
