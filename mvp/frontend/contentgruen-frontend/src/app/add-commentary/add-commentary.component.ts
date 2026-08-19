import { Component, Input, Output, EventEmitter, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { trigger, transition, style, animate } from '@angular/animations';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CommentaryService } from '../services/commentary.service';
import { StatementService } from '../services/statement.service';
import { LoggingService } from '../services/logging.service';
import { AddCommentaryRequest, AddCommentaryResponse } from '../services/dtos/commentaryDtos';
import { AddReplysuggestionToStatementRequest, AddReplysuggestionToStatementResponse } from '../services/dtos/statementDtos';
import { CommentaryResult } from '../services/dtos/searchDtos';
import { CommentaryResultItemComponent } from '../commentary-result-item/commentary-result-item.component';
import { ReferenceInputComponent, ReferenceEntry } from '../reference-input/reference-input.component';
import { ContentStatus } from '../services/dtos/content-status-enum';
import { ContentOrigin } from '../services/dtos/content-origin-enum';
import { ContentVisibility } from '../services/dtos/content-visibility-enum';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil, debounceTime } from 'rxjs/operators';

interface CommentaryFormValues {
    title: string;
    text: string;
    long_text: string;
    short_text: string;
    references: string[];
}

@Component({
    standalone: true,
    selector: 'app-add-commentary',
    templateUrl: './add-commentary.component.html',
    styleUrls: ['./add-commentary.component.scss'],
    imports: [
        ...SHARED_IMPORTS,
        CommonModule,
        FormsModule,
        MatSlideToggleModule,
        CommentaryResultItemComponent,
        ReferenceInputComponent
    ],
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
export class AddCommentaryComponent implements OnDestroy {
    @Input() statementText: string = '';
    @Input() statementId: string = '';
    @Output() success = new EventEmitter<string>();
    @Output() cancel = new EventEmitter<void>();
    @ViewChild('successContainer', { read: ElementRef }) successContainer?: ElementRef;
    @ViewChild('loadingContainer', { read: ElementRef }) loadingContainer?: ElementRef;
    @ViewChild(ReferenceInputComponent) referenceInput?: ReferenceInputComponent;

    private destroy$ = new Subject<void>();

    commentaryForm: FormGroup;
    previewResult: CommentaryResult | null = null;

    commentaryLoading = false;
    commentarySaved = false;

    commentaryError: string | null = null;
    responseId: string = '';

    // New properties for inline statement handling
    isReplyToStatement: boolean = false;
    statementInput: string = '';
    private statementUpdateSubject = new Subject<string>();

    // Optional form sections start collapsed to keep the initial form minimal.
    // NOTE: if an edit mode is added later, initialise these from the loaded values
    // (e.g. showTextVariants = !!long_text || !!short_text) so filled fields stay visible.
    showTextVariants = false;
    showReferences = false;

    constructor(
        private fb: FormBuilder,
        private commentaryService: CommentaryService,
        private statementService: StatementService,
        private logger: LoggingService,
        private router: Router
    ) {
        this.commentaryForm = this.fb.group({
            title: ['', [Validators.required, Validators.minLength(3)]],
            text: ['', [Validators.required, Validators.minLength(10)]],
            references: [[]],  // Changed from FormArray to simple array control
            long_text: [''],
            short_text: [''],
        });

        // Listen to form changes to update the preview dynamically
        this.commentaryForm.valueChanges
            .pipe(takeUntil(this.destroy$))
            .subscribe((formValues) => {
                this.updatePreview(formValues);
            });

        // Initialize preview with form values
        this.updatePreview(this.commentaryForm.value);

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

    // Collapsing only removes the fields from the DOM - the form controls keep their
    // values, so nothing entered here is lost when the section is closed again.
    toggleTextVariants(): void {
        this.showTextVariants = !this.showTextVariants;
    }

    // One-way reveal: re-creating app-reference-input would drop the server ids of
    // already added references, so the section stays open once it has been opened.
    revealReferences(): void {
        this.showReferences = true;
    }

    updatePreview(formValues: CommentaryFormValues): void {
        // Create or update preview result
        this.previewResult = {
            content_type: 'commentary',
            title: formValues.title || 'Titel eingeben...',
            text: formValues.text || 'Text eingeben...',
            long_text: formValues.long_text || '',
            short_text: formValues.short_text || '',
            id: 'preview',
            created: new Date().toISOString(),
            last_modified: new Date().toISOString(),
            original_author: 'Du',
            last_modified_by: 'user',
            authors: [],
            edit_history: [],
            status: ContentStatus.DRAFT,
            origin: ContentOrigin.MANUALLY_CREATED,
            most_similar_similarity_score: 0,
            most_similar_content_id: '',
            report_count: 0,
            is_archived: false,
            report_flagged: false,
            rejection_reason: '',
            block_reason: '',
            visibility: ContentVisibility.VISIBLE,
            // Create mock references for preview
            references: formValues.references ? formValues.references
                .filter((ref: any) => ref && ref.reference_string && ref.reference_string.trim()) // Filter out empty references
                .map((ref: any, index: number) => ({
                    reference_id: 'preview-' + index,
                    reference_text: ref.reference_string,
                    reference_description: ref.description || undefined, // Use the description if provided
                    created: new Date().toISOString()
                })) : [],
            references_count: 0,
            score: 1.0
        };
        // Update references_count to match
        this.previewResult.references_count = this.previewResult.references.length;
    }

    saveCommentaryForm(): void {
        // Noch nicht bestaetigte Quelleneingabe uebernehmen, bevor der Formularwert
        // gelesen wird - sonst geht sie beim Speichern stumm verloren.
        this.referenceInput?.flushPendingInput();

        if (this.commentaryForm.invalid) {
            return;
        }

        this.commentaryLoading = true;
        this.commentaryError = null;
        this.scrollToLoadingOrSuccess();

        const formValue = this.commentaryForm.value;
        const request: AddCommentaryRequest = {
            commentary: {
                title: formValue.title,
                text: formValue.text,
                long_text: formValue.long_text || '',
                short_text: formValue.short_text || '',
                references: [] // Don't send reference IDs here - they will be created and added by the backend
            },
            references: formValue.references || [] // Send the text strings here for the backend to create
        };

        this.commentaryService.addCommentary(request).subscribe({
            next: (response) => {
                this.responseId = response.id;

                // Fetch the full commentary to get the actual reference IDs
                this.commentaryService.getCommentaryById(response.id).subscribe({
                    next: (fullCommentary) => {
                        // Update the preview with the full commentary data including real reference IDs
                        this.previewResult = fullCommentary;
                    },
                    error: (error) => {
                        this.logger.error('Error fetching full commentary details', error);
                        // Keep the existing preview
                    }
                });

                // If there's a statement, link the commentary to it
                if (this.statementId) {
                    const statementRequest: AddReplysuggestionToStatementRequest = {
                        statement_id: this.statementId,
                        replysuggestion_id: response.id,
                        content_type: 'commentary',  // We know this is a commentary
                        relevance: 1.0
                    };
                    this.statementService.addReplysuggestionToStatement(statementRequest).subscribe({
                        next: () => {
                            this.commentarySaved = true;
                            this.commentaryLoading = false;
                            this.success.emit(response.id);
                        },
                        error: (error) => {
                            this.logger.error('Error linking commentary to statement', error);
                            // Still consider it saved even if linking failed
                            this.commentarySaved = true;
                            this.commentaryLoading = false;
                            this.success.emit(response.id);
                        }
                    });
                } else {
                    this.commentarySaved = true;
                    this.commentaryLoading = false;
                    this.success.emit(response.id);
                }
            },
            error: (error: Error) => {
                this.logger.error('Error saving commentary', error);
                this.commentaryError = error.message || 'Fehler beim Speichern des Kommentars. Bitte überprüfe deine Internetverbindung und versuche es erneut.';
                this.commentaryLoading = false;
            }
        });
    }

    retryCommentarySave(): void {
        this.commentaryError = null;
        this.saveCommentaryForm();
    }

    resetCommentaryForm(): void {
        this.commentaryForm.reset({
            title: '',
            text: '',
            long_text: '',
            short_text: '',
            references: []
        });
        this.responseId = '';
        this.commentaryError = null;
        this.commentarySaved = false;
        this.showTextVariants = false;
        this.showReferences = false;
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

    findOrCreateStatement(statementText: string): void {
        this.statementService.findOrCreateStatement(statementText, 'manually_created').subscribe({
            next: (response) => {
                this.statementId = response.statement_id;
                this.statementText = response.statement_text;

                if (response.statement_was_new) {
                    this.logger.info('Created new statement with ID:', response.statement_id);
                } else {
                    this.logger.info('Using existing statement with ID:', response.statement_id);
                }

                // View will update automatically
            },
            error: (error) => {
                this.logger.error('Error finding or creating statement', error);
                // Don't use a temporary ID - show error to user instead
                this.commentaryError = 'Fehler beim Erstellen des Statements. Bitte versuche es erneut.';
            }
        });
    }

    removeStatement(): void {
        this.clearStatement();
        this.isReplyToStatement = false;
    }

    navigateToCommentary(id: string): void {
        // Navigate to search page with query param to trigger refresh and fragment to scroll
        this.router.navigate(['/search'], {
            queryParams: { refresh: 'true' },
            fragment: 'recent-content'
        });
    }

    onCancel(): void {
        this.cancel.emit();
    }

    private scrollToLoadingOrSuccess(): void {
        // Immediately scroll to loading or success container
        setTimeout(() => {
            // First priority: loading container when form is being submitted
            if (this.commentaryLoading && this.loadingContainer) {
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
