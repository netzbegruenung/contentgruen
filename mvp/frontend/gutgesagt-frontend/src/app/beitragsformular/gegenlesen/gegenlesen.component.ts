import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, Input, OnChanges, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Subject, of } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, map, switchMap } from 'rxjs/operators';

import { SiegelComponent } from '../../shared/components/siegel/siegel.component';
import { GEGENLESEN_VERZOEGERUNG_MS, Gegengelesen, GegenlesenService } from './gegenlesen.service';

/** Was gerade im Formular steht. */
interface Eingabe {
  titel: string;
  text: string;
  aussage: string;
}

const NOCH_LEER: Gegengelesen = { guete: null, anmerkungen: [] };

/** Zu viele Anfragen: Das letzte Ergebnis bleibt stehen, statt dass der Block verschwindet. */
const ZU_VIELE = 'zu-viele';

/**
 * Gegenlesen beim Schreiben (#358), unter der Vorschau eines Beitragsformulars: etwa
 * eine Sekunde nach der letzten Eingabe liest der Dienst Titel und Text gegen feste
 * Regeln. Das Siegel zeigt den Kriterienanteil der Güte und dreht sich mit, wenn der
 * Text besser wird; darunter stehen die Anmerkungen. Nur die schreibende Person sieht
 * das, und Speichern geht immer. Antwortet der Dienst nicht, verschwindet der Block,
 * bis das nächste Gegenlesen gelingt; beim Rate-Limit bleibt das letzte Ergebnis stehen.
 */
@Component({
  selector: 'app-gegenlesen',
  standalone: true,
  imports: [CommonModule, SiegelComponent],
  templateUrl: './gegenlesen.component.html',
  styleUrls: ['./gegenlesen.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GegenlesenComponent implements OnChanges {
  @Input() titel: string | null = '';
  @Input() text: string | null = '';
  /** Die Aussage, auf die der Beitrag antwortet; leer, wenn er auf keine antwortet. */
  @Input() aussage: string | null = '';

  ergebnis: Gegengelesen = NOCH_LEER;
  verfuegbar = true;

  private readonly eingabe = new Subject<Eingabe>();

  constructor(service: GegenlesenService, cdr: ChangeDetectorRef) {
    this.eingabe
      .pipe(
        debounceTime(GEGENLESEN_VERZOEGERUNG_MS),
        map((e) => ({ titel: e.titel.trim(), text: e.text.trim(), aussage: e.aussage.trim() })),
        distinctUntilChanged((a, b) => a.titel === b.titel && a.text === b.text && a.aussage === b.aussage),
        switchMap((e) =>
          !e.titel && !e.text
            ? of(NOCH_LEER)
            : service
                .gegenlesen(e.titel, e.text, e.aussage)
                .pipe(
                  catchError((fehler: unknown) =>
                    of<typeof ZU_VIELE | null>(
                      fehler instanceof HttpErrorResponse && fehler.status === 429 ? ZU_VIELE : null,
                    ),
                  ),
                ),
        ),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe((ergebnis) => {
        if (ergebnis === ZU_VIELE) return;
        this.verfuegbar = ergebnis !== null;
        if (ergebnis) this.ergebnis = ergebnis;
        cdr.markForCheck();
      });
  }

  ngOnChanges(): void {
    this.eingabe.next({ titel: this.titel ?? '', text: this.text ?? '', aussage: this.aussage ?? '' });
  }
}
