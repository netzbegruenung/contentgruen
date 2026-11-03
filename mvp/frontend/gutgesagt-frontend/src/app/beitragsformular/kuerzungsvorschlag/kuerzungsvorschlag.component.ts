import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  inject,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

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
export class KuerzungsvorschlagComponent implements OnChanges {
  /** Der Haupttext des Kommentars (Mittelfassung). */
  @Input() text: string | null = '';
  /** Die Aussage, auf die der Kommentar antwortet; leer, wenn er auf keine antwortet. */
  @Input() aussage: string | null = '';
  /** Höchstlänge der Kurzfassung: Erst ein längerer Kommentar bekommt den Knopf. */
  @Input() grenze = 0;
  @Output() uebernehmen = new EventEmitter<string>();

  stand: Stand = 'leer';
  vorschlag = '';

  private readonly service = inject(KuerzungsvorschlagService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly destroyRef = inject(DestroyRef);
  private anfrage?: Subscription;

  get lohntSich(): boolean {
    return (this.text?.trim().length ?? 0) > this.grenze;
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Ein Vorschlag gilt nur für den Text und die Aussage, aus denen er entstand.
    const geaendert = ['text', 'aussage'].some((name) => changes[name] && !changes[name].firstChange);
    if (geaendert) this.verwerfen();
  }

  vorschlagen(): void {
    this.stand = 'laedt';
    this.anfrage = this.service
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
    this.anfrage?.unsubscribe();
    this.vorschlag = '';
    this.stand = 'leer';
    this.cdr.markForCheck();
  }
}
