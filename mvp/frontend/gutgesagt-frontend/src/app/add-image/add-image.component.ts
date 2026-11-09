import { AfterViewInit, Component, ElementRef, EventEmitter, OnDestroy, Output, ViewChild } from '@angular/core';
import { typBeschreibung } from '../shared/content-type-registry';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ImageService } from '../services/image.service';
import { LoggingService } from '../services/logging.service';
import { ImageSearchResult } from '../services/dtos/searchDtos';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { ContentStatus } from '../services/dtos/content-status-enum';
import { ContentOrigin } from '../services/dtos/content-origin-enum';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { Cc0HinweisComponent } from '../shared/cc0-hinweis/cc0-hinweis.component';
import { SprachhinweisComponent } from '../shared/components/sprachhinweis/sprachhinweis.component';

@Component({
  selector: 'app-add-image',
  standalone: true,
  imports: [
    ...SHARED_IMPORTS,
    CommonModule,
    FormsModule,
    BeitragskarteComponent,
    Cc0HinweisComponent,
    SprachhinweisComponent,
  ],
  templateUrl: './add-image.component.html',
  styleUrls: ['./add-image.component.scss'],
})
export class AddImageComponent implements AfterViewInit, OnDestroy {
  /** Der Satz zum Typ aus der Registry, wie auf /contribute. */
  readonly typBeschreibung = typBeschreibung('image');

  @Output() success = new EventEmitter<string>();
  @Output() cancel = new EventEmitter<void>();

  private destroy$ = new Subject<void>();

  /** Die Vorschau; dort laedt das Bild, und dort merkt man, ob es sich laden laesst (#619). */
  @ViewChild('vorschau', { static: true }) private vorschau?: ElementRef<HTMLElement>;

  /**
   * Die Vorschau konnte das Bild unter der eingegebenen URL nicht laden. Dann steht unter
   * dem Feld ein Hinweis, und die Vorschau zeigt kein kaputtes Bild. Speichern bleibt
   * moeglich: lenken, nicht sperren.
   */
  bildLadefehler = false;
  private bildUrl = '';

  imageForm: FormGroup;
  previewResult: ImageSearchResult | null = null;
  private vorschauCache?: { quelle: ImageSearchResult; karte: KartenDaten };

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

  imageLoading = false;
  imageSaved = false;
  imageError: string | null = null;
  responseId: string = '';

  constructor(
    private fb: FormBuilder,
    private imageService: ImageService,
    private logger: LoggingService,
    private router: Router,
  ) {
    this.imageForm = this.fb.group({
      title: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(200)]],
      image_url: ['', [Validators.required, Validators.pattern(/https?:\/\/.+/)]],
      caption: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(2000)]],
    });

    this.imageForm.valueChanges.pipe(takeUntil(this.destroy$)).subscribe((values) => {
      // Neue URL, neuer Versuch: der alte Ladefehler gilt nicht mehr.
      if ((values.image_url || '') !== this.bildUrl) {
        this.bildUrl = values.image_url || '';
        this.bildLadefehler = false;
      }
      this.updatePreview(values);
    });

    this.updatePreview(this.imageForm.value);
  }

  ngAfterViewInit(): void {
    // Das error-Ereignis eines Bildes steigt nicht auf; in der Capture-Phase kommt es hier an.
    // Ein fremdes Bild laedt erst auf Klick in der Vorschau (#447), der Hinweis also auch.
    this.vorschau?.nativeElement.addEventListener('error', this.beimLadefehler, true);
  }

  private readonly beimLadefehler = (ereignis: Event): void => {
    const bild = ereignis.target;
    if (!(bild instanceof HTMLImageElement) || !this.bildUrl || this.bildLadefehler) {
      return;
    }
    // Nur der Fehler zur aktuellen URL zaehlt, nicht ein verspaeteter zur vorigen.
    if (bild.src !== new URL(this.bildUrl, location.href).href) {
      return;
    }
    this.bildLadefehler = true;
    this.updatePreview(this.imageForm.value);
  };

  updatePreview(values: any): void {
    this.previewResult = {
      score: 1.0,
      statement_text: '',
      statement_similarity_score: 0,
      reply_relevance: 0,
      image_result: {
        id: 'preview',
        title: values.title || 'Titel eingeben...',
        text: values.caption || 'Bildunterschrift eingeben...',
        image_url: this.bildLadefehler ? '' : values.image_url || '',
        references: [],
        created: new Date().toISOString(),
        last_modified: new Date().toISOString(),
        original_author: 'Du',
        last_modified_by: 'Du',
        authors: [{ name: 'Du', role: 'author' }],
        edit_history: [],
        content_type: 'image',
        status: ContentStatus.VISIBLE,
        origin: ContentOrigin.MANUALLY_CREATED,
        score: 1.0,
        most_similar_similarity_score: 0,
        most_similar_content_id: '',
        report_count: 0,
        usage_count: 0,
        references_count: 0,
      },
    } as ImageSearchResult;
  }

  reset(): void {
    this.responseId = '';
    this.imageSaved = false;
    this.imageError = null;
    this.imageForm.reset();
    this.updatePreview(this.imageForm.value);
  }

  /** Nach gescheitertem Speichern: dieselben Eingaben noch einmal senden, nichts leeren. */
  erneutVersuchen(): void {
    this.imageError = null;
    this.saveImageForm();
  }

  navigateBack(): void {
    this.cancel.emit();
  }

  saveImageForm(): void {
    if (!this.imageForm.valid) {
      Object.keys(this.imageForm.controls).forEach((key) => {
        this.imageForm.get(key)?.markAsTouched();
      });
      return;
    }

    const values = this.imageForm.value;
    this.imageLoading = true;
    this.imageError = null;

    this.imageService
      .addImage({
        image: {
          title: values.title,
          image_url: values.image_url,
          text: values.caption,
        },
      })
      .subscribe({
        next: (response) => {
          this.imageLoading = false;
          this.imageSaved = true;
          this.responseId = response.id;
          setTimeout(() => {
            this.success.emit(response.id);
          }, 2000);
        },
        error: (error) => {
          this.logger.error('Error saving image', error);
          this.imageLoading = false;
          this.imageError =
            'Fehler beim Speichern des Bildes. Bitte überprüfe deine Internetverbindung und versuche es erneut.';
        },
      });
  }

  ngOnDestroy(): void {
    this.vorschau?.nativeElement.removeEventListener('error', this.beimLadefehler, true);
    this.destroy$.next();
    this.destroy$.complete();
  }
}
