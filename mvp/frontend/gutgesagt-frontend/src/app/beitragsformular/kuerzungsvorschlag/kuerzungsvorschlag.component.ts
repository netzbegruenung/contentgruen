import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, EventEmitter, Input, Output, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';

import { KuerzungsvorschlagService } from './kuerzungsvorschlag.service';

type Stand = 'leer' | 'laedt' | 'vorschlag' | 'passt-nicht' | 'fehler';

/**
 * Kürzungsvorschlag (#403) unter der Kurzfassung: Auf Klick schlägt der Dienst eine
 * Kurzfassung aus den eigenen Sätzen des Kommentars vor, ohne KI und ohne Umformulieren.
 * Die Person übernimmt oder verwirft ihn; nichts wird automatisch ersetzt (ADR 0003).
 */
@Component({
  selector: 'app-kuerzungsvorschlag',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './kuerzungsvorschlag.component.html',
  styleUrls: ['./kuerzungsvorschlag.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KuerzungsvorschlagComponent {
  /** Der Haupttext des Kommentars (Mittelfassung). */
  @Input() text: string | null = '';
  /** Die Aussage, auf die der Kommentar antwortet; leer, wenn er auf keine antwortet. */
  @Input() aussage: string | null = '';
  @Output() uebernehmen = new EventEmitter<string>();

  stand: Stand = 'leer';
  vorschlag = '';

  private readonly service = inject(KuerzungsvorschlagService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly destroyRef = inject(DestroyRef);

  get hatText(): boolean {
    return !!this.text?.trim();
  }

  vorschlagen(): void {
    this.stand = 'laedt';
    this.service
      .vorschlagen((this.text ?? '').trim(), (this.aussage ?? '').trim())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ vorschlag }) => {
          this.vorschlag = vorschlag ?? '';
          this.stand = vorschlag ? 'vorschlag' : 'passt-nicht';
          this.cdr.markForCheck();
        },
        error: () => {
          this.stand = 'fehler';
          this.cdr.markForCheck();
        },
      });
  }

  annehmen(): void {
    this.uebernehmen.emit(this.vorschlag);
    this.verwerfen();
  }

  verwerfen(): void {
    this.vorschlag = '';
    this.stand = 'leer';
  }
}
