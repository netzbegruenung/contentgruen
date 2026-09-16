import { Component, Input, Output, EventEmitter, OnChanges, OnDestroy, SimpleChanges, ViewChild, ElementRef } from '@angular/core';
import { trigger, transition, style, animate } from '@angular/animations';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { GenericTextService } from '../services/generic-text.service';
import { StatementService, VERKNUEPFUNG_FEHLGESCHLAGEN } from '../services/statement.service';
import { LoggingService } from '../services/logging.service';
import { AddGenericTextRequest, AddGenericTextResponse } from '../services/dtos/generictextDtos';
import { GenerictextSearchResult } from '../services/dtos/searchDtos';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { ReferenceInputComponent, ReferenceEntry } from '../reference-input/reference-input.component';
import { ContentStatus } from '../services/dtos/content-status-enum';
import { ContentOrigin } from '../services/dtos/content-origin-enum';
import { ContentVisibility } from '../services/dtos/content-visibility-enum';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import type { Vorbefuellung } from '../destillieren/destillier-uebergabe.service';
import { typLabel } from '../shared/content-type-registry';
import { CONSENT_HINWEIS } from '../shared/consent-hinweis';


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
        BeitragskarteComponent,
        ReferenceInputComponent,
        RouterLink
    ],
    templateUrl: './add-generictext.component.html',
    styleUrls: ['./add-generictext.component.scss'],
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
export class AddGenerictextComponent implements OnChanges, OnDestroy {
    readonly typName = typLabel('generictext');
    readonly consentHinweis = CONSENT_HINWEIS;
    @Input() statementText: string = '';
    @Input() statementId: string = '';
    /** Die Aussage aus der Adresse war nicht ladbar: Hinweis zeigen, Feld leer und offen. */
    @Input() aussageHinweis: string | null = null;
    /** Aus dem Destillier-Ablauf: Satz als Titel, Link als Herkunft. */
    @Input() vorbefuellung: Vorbefuellung | null = null;
    @Output() success = new EventEmitter<string>();
    @Output() cancel = new EventEmitter<void>();
    @ViewChild('successContainer', { read: ElementRef }) successContainer?: ElementRef;
    @ViewChild('loadingContainer', { read: ElementRef }) loadingContainer?: ElementRef;
    @ViewChild(ReferenceInputComponent) referenceInput?: ReferenceInputComponent;

    private destroy$ = new Subject<void>();

    generictextForm: FormGroup;
    previewResult: GenerictextSearchResult | null = null;
    private vorschauCache?: { quelle: GenerictextSearchResult; karte: KartenDaten };

    /** Die Vorschau als KartenDaten, zwischengespeichert bis sich die Vorschau aendert. */
    get vorschauKarte(): KartenDaten | null {
        if (!this.previewResult) {
            return null;
        }
        if (this.vorschauCache?.quelle !== this.previewResult) {
            this.vorschauCache = { quelle: this.previewResult, karte: ausSuchergebnis(this.previewResult) };
        }
        return this.vorschauCache.karte;
    }

    generictextLoading = false;
    generictextSaved = false;

    generictextError: string | null = null;
    responseId: string = '';

    // New properties for inline statement handling
    isReplyToStatement: boolean = false;
    statementInput: string = '';
    /** Gesetzt, wenn der Beitrag gespeichert ist, die Verknuepfung mit der Aussage aber scheiterte. */
    verknuepfungsFehler: string | null = null;

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
            title: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(120)]],
            text: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(2000)]],
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
    }

    ngOnChanges(changes: SimpleChanges): void {
        // Die Aussage kommt als Input - im Konstruktor ist sie noch leer. Vorher
        // stand diese Pruefung dort und griff deshalb nie: Aus der Suche zeigte
        // der Schalter "eigenstaendig", obwohl verknuepft wurde.
        if (changes['statementText']) {
            if (this.statementText) {
                this.isReplyToStatement = true;
                this.statementInput = this.statementText;
            } else {
                // Die Aussage aus der Adresse ist weg (etwa ein neuer Aufruf ohne
                // ?aussage=): Feld und ID leeren, sonst stuende der alte Text noch da.
                this.statementInput = '';
                this.statementId = '';
            }
        }
        if (changes['aussageHinweis'] && this.aussageHinweis) {
            this.isReplyToStatement = true;
            this.statementInput = '';
        }
        if (changes['vorbefuellung'] && this.vorbefuellung) {
            this.vorbefuellungAnwenden(this.vorbefuellung);
        }
    }

    // Titel = Satz aus dem Destillier-Ablauf, Herkunft = Link des Einwurfs. Beides
    // bleibt im Formular aenderbar; die Quellen werden aufgeklappt, damit die
    // uebernommene Herkunft sichtbar ist.
    vorbefuellungAnwenden(vorbefuellung: Vorbefuellung): void {
        this.generictextForm.patchValue({
            title: vorbefuellung.titel,
            references: vorbefuellung.url ? [{ reference_string: vorbefuellung.url }] : [],
        });
        if (vorbefuellung.url) {
            this.showReferences = true;
        }
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

    clearStatement(): void {
        this.statementText = '';
        this.statementId = '';
        this.statementInput = '';
    }

    reset() {
        this.responseId = '';
        this.generictextSaved = false;
        this.generictextError = null;
        this.verknuepfungsFehler = null;
        this.showReferences = false;
        this.generictextForm.reset();
        this.updatePreview(this.generictextForm.value);
    }

    /** Nach gescheiterter Verknuepfung: der Beitrag steht, weiter wie nach dem Speichern. */
    weiterNachVerknuepfungsFehler(): void {
        this.success.emit(this.responseId);
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

                    // Antwort auf eine Aussage: erst jetzt aufloesen und verknuepfen, und
                    // das abwarten. Scheitert es, ist der Beitrag trotzdem gespeichert -
                    // dann bleibt der Hinweis stehen, weiter geht es mit "Weiter".
                    this.statementService
                        .alsAntwortVerknuepfen(response.id, 'generic_text', 0.9, this.aussageZumSpeichern())
                        .subscribe((ergebnis) => {
                            this.generictextLoading = false;
                            this.generictextSaved = true;
                            this.responseId = response.id;

                            if (ergebnis === 'fehlgeschlagen') {
                                this.verknuepfungsFehler = VERKNUEPFUNG_FEHLGESCHLAGEN;
                                return;
                            }
                            setTimeout(() => {
                                this.success.emit(response.id);
                            }, 2000);
                        });
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

    /** Der Text im Aussage-Feld, so wie er gespeichert wuerde. */
    get aussageText(): string {
        return this.isReplyToStatement ? this.statementInput.trim() : '';
    }

    /**
     * Die Aussage fuer alsAntwortVerknuepfen - leer, wenn der Schalter aus ist.
     *
     * Die mitgegebene ID gilt nur, solange der Text der geladenen Aussage
     * unveraendert im Feld steht. Wurde er bearbeitet, zaehlt der Text: Dann wird
     * beim Speichern gesucht oder angelegt, statt an die alte Aussage zu haengen.
     */
    aussageZumSpeichern(): { id: string; text: string } {
        const text = this.aussageText;
        if (!text) {
            return { id: '', text: '' };
        }
        const unveraendert = !!this.statementId && text === this.statementText.trim();
        return { id: unveraendert ? this.statementId : '', text };
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
        this.destroy$.next();
        this.destroy$.complete();
    }
}
