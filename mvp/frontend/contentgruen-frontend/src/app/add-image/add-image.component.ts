import { Component, Input, Output, EventEmitter, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ImageService } from '../services/image.service';
import { LoggingService } from '../services/logging.service';
import { ImageSearchResult } from '../services/dtos/searchDtos';
import { ImageResultItemComponent } from '../image-result-item/image-result-item.component';
import { ContentStatus } from '../services/dtos/content-status-enum';
import { ContentOrigin } from '../services/dtos/content-origin-enum';
import { ContentVisibility } from '../services/dtos/content-visibility-enum';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-add-image',
  standalone: true,
  imports: [
    ...SHARED_IMPORTS,
    CommonModule,
    FormsModule,
    ImageResultItemComponent,
  ],
  templateUrl: './add-image.component.html',
  styleUrls: ['./add-image.component.scss'],
})
export class AddImageComponent implements OnDestroy {
  @Output() success = new EventEmitter<string>();
  @Output() cancel = new EventEmitter<void>();

  private destroy$ = new Subject<void>();

  imageForm: FormGroup;
  previewResult: ImageSearchResult | null = null;

  imageLoading = false;
  imageSaved = false;
  imageError: string | null = null;
  captionLoading = false;
  captionError: string | null = null;
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
      this.updatePreview(values);
    });

    this.updatePreview(this.imageForm.value);
  }

  get imageUrlInvalid(): boolean {
    const ctrl = this.imageForm.get('image_url');
    return !ctrl || ctrl.invalid || !ctrl.value?.trim();
  }

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
        image_url: values.image_url || '',
        description_model: null,
        references: [],
        created: new Date().toISOString(),
        last_modified: new Date().toISOString(),
        original_author: 'Du',
        last_modified_by: 'Du',
        authors: [{ name: 'Du', role: 'author' }],
        edit_history: [],
        content_type: 'image',
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
        references_count: 0,
      },
    } as ImageSearchResult;
  }

  suggestCaption(): void {
    const imageUrl = this.imageForm.get('image_url')?.value?.trim();
    if (!imageUrl) return;

    this.captionLoading = true;
    this.captionError = null;

    this.imageService.suggestCaption({ image_url: imageUrl }).subscribe({
      next: (response) => {
        this.imageForm.get('caption')?.setValue(response.suggested_caption);
        this.captionLoading = false;
      },
      error: (error) => {
        this.logger.error('Caption suggestion failed', error);
        this.captionError =
          'Vorschlag konnte nicht erstellt werden. Bitte gib eine Beschriftung manuell ein.';
        this.captionLoading = false;
      },
    });
  }

  reset(): void {
    this.responseId = '';
    this.imageSaved = false;
    this.imageError = null;
    this.captionError = null;
    this.imageForm.reset();
    this.updatePreview(this.imageForm.value);
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
    this.destroy$.next();
    this.destroy$.complete();
  }
}
