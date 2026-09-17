import {
  ChangeDetectorRef,
  Component,
  DestroyRef,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
  inject,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { TextFieldModule } from '@angular/cdk/text-field';
import { of } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, map, switchMap } from 'rxjs/operators';

import { SHARED_IMPORTS } from '../../shared/shared-imports';
import { BeitragskarteComponent } from '../../beitragskarte/beitragskarte.component';
import { KartenDaten, ausAussage } from '../../beitragskarte/karten-daten';
import { AUSSAGE_MAX_ZEICHEN, StatementService } from '../../services/statement.service';
import { StatementSearchResult } from '../../services/dtos/statementDtos';
import { LoggingService } from '../../services/logging.service';

/** Worauf ein Beitrag antwortet: eine vorhandene Aussage (mit ID) oder nur ihr Text. */
export interface AntwortAuf {
  id: string;
  text: string;
}

export const OHNE_AUSSAGE: AntwortAuf = { id: '', text: '' };

/** Laenge, ab der das Feld vorhandene Aussagen vorschlaegt. */
export const VORSCHLAG_AB_ZEICHEN = 8;

/** Wartezeit nach dem letzten Tastendruck, bevor gesucht wird. */
export const VORSCHLAG_VERZOEGERUNG_MS = 300;

/** Mindestlaenge einer Aussage ohne Auswahl, wie im Backend (statement_text). Leer bleibt erlaubt. */
export const AUSSAGE_MIN_ZEICHEN = 10;

export { AUSSAGE_MAX_ZEICHEN } from '../../services/statement.service';

/**
 * Der Block "Antwort auf" eines Beitragsformulars, fuer alle Beitragstypen.
 *
 * Ist eine Aussage gewaehlt - aus der Adresse oder aus den Vorschlaegen -, steht
 * sie als Kopf-Karte da und laesst sich entfernen. Sonst ist es ein freies,
 * optionales Feld: Beim Tippen schlaegt es passende vorhandene Aussagen vor, und
 * darunter steht immer die Wahl, den getippten Text als neue Aussage zu nehmen.
 * Angelegt wird hier nichts; was gilt, meldet `aussageChange`, und aufgeloest
 * wird erst beim Speichern im Backend.
 */
@Component({
  standalone: true,
  selector: 'app-antwort-auf',
  templateUrl: './antwort-auf.component.html',
  styleUrls: ['./antwort-auf.component.css'],
  imports: [...SHARED_IMPORTS, CommonModule, ReactiveFormsModule, TextFieldModule, BeitragskarteComponent],
})
export class AntwortAufComponent implements OnInit, OnChanges {
  private destroyRef = inject(DestroyRef);

  /** Die Aussage aus der Adresse; mit ID gilt sie als gewaehlt, ohne ID steht ihr Text im Feld. */
  @Input() aussage: AntwortAuf = OHNE_AUSSAGE;
  /** Die Aussage aus der Adresse war nicht ladbar. */
  @Input() hinweis: string | null = null;
  /** Beispiel im leeren Feld. */
  @Input() platzhalter = 'z. B. „Wärmepumpen sind zu teuer“';
  @Output() aussageChange = new EventEmitter<AntwortAuf>();

  readonly maxZeichen = AUSSAGE_MAX_ZEICHEN;
  readonly minZeichen = AUSSAGE_MIN_ZEICHEN;
  readonly feld = new FormControl('', { nonNullable: true });
  gewaehlt: AntwortAuf | null = null;
  /** Die gewaehlte Aussage gibt es noch nicht; sie entsteht beim Speichern. */
  gewaehltNeu = false;
  kopf: KartenDaten | null = null;
  vorschlaege: StatementSearchResult[] = [];
  /** Der Text, fuer den die Vorschlaege gesucht wurden - erst dann gibt es "neu anlegen". */
  gesuchtFuer: string | null = null;

  constructor(
    private statementService: StatementService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.feld.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((text) => this.aussageChange.emit({ id: '', text: text.trim() }));

    this.feld.valueChanges
      .pipe(
        map((text) => text.trim()),
        debounceTime(VORSCHLAG_VERZOEGERUNG_MS),
        distinctUntilChanged(),
        switchMap((text) =>
          text.length < VORSCHLAG_AB_ZEICHEN
            ? of({ text: null, vorschlaege: [] })
            : this.statementService.aussageVorschlaege(text).pipe(
                catchError((error) => {
                  // Ohne Vorschlaege bleibt das Feld nutzbar; gespeichert wird dann der Text.
                  this.logger.warn('Aussage-Vorschlaege nicht ladbar', error);
                  return of([]);
                }),
                map((vorschlaege) => ({ text: text as string | null, vorschlaege })),
              ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ text, vorschlaege }) => {
        this.vorschlaege = this.gewaehlt ? [] : vorschlaege;
        this.gesuchtFuer = this.gewaehlt ? null : text;
        this.cdr.markForCheck();
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['aussage']) {
      const { id, text } = this.aussage ?? OHNE_AUSSAGE;
      if (id && text) {
        this.waehlen({ id, text });
      } else {
        this.gewaehltSetzen(null);
        this.feld.setValue(text ?? '', { emitEvent: false });
        this.vorschlaege = [];
      }
    }
  }

  /** Was beim Speichern gilt. */
  get wert(): AntwortAuf {
    return this.gewaehlt ?? { id: '', text: this.feld.value.trim() };
  }

  /** Der getippte Text, solange er sich als neue Aussage anbietet. */
  get neuAnlegbar(): string | null {
    const text = this.feld.value.trim();
    return this.gesuchtFuer && text === this.gesuchtFuer && !zuKurz(text) ? text : null;
  }

  /**
   * Was mit dem Feld beim Speichern passiert: nichts (leer), zu kurz (1-9 Zeichen,
   * Speichern gesperrt) oder als neue Aussage angelegt (Text ohne Auswahl).
   */
  get feldZustand(): 'leer' | 'zu-kurz' | 'neu' {
    const text = this.feld.value.trim();
    if (!text) {
      return 'leer';
    }
    return zuKurz(text) ? 'zu-kurz' : 'neu';
  }

  /** Den getippten Text als neue Aussage nehmen - angelegt wird sie beim Speichern. */
  alsNeueAussage(): void {
    const text = this.neuAnlegbar;
    if (!text) {
      return;
    }
    this.gewaehltSetzen({ id: '', text }, true);
    this.vorschlaege = [];
    this.gesuchtFuer = null;
    this.feld.setValue('', { emitEvent: false });
    this.aussageChange.emit({ id: '', text });
  }

  waehlen(aussage: { id: string; text: string }): void {
    this.gewaehltSetzen({ id: aussage.id, text: aussage.text });
    this.vorschlaege = [];
    this.gesuchtFuer = null;
    this.feld.setValue('', { emitEvent: false });
    this.aussageChange.emit(this.wert);
  }

  entfernen(): void {
    this.gewaehltSetzen(null);
    this.feld.setValue('', { emitEvent: false });
    this.vorschlaege = [];
    this.gesuchtFuer = null;
    this.aussageChange.emit(OHNE_AUSSAGE);
  }

  /** Alles leeren, ohne Ereignis - fuer das Zuruecksetzen des Formulars. */
  leeren(): void {
    this.gewaehltSetzen(null);
    this.feld.setValue('', { emitEvent: false });
    this.vorschlaege = [];
    this.gesuchtFuer = null;
  }

  private gewaehltSetzen(aussage: AntwortAuf | null, neu = false): void {
    this.gewaehlt = aussage;
    this.gewaehltNeu = !!aussage && neu;
    // Einmal je Wahl bauen: ein neues Objekt je Change Detection setzte die Karte zurueck.
    this.kopf = aussage ? ausAussage(aussage.id, aussage.text) : null;
  }
}

/** Eine Aussage ohne Auswahl mit 1 bis AUSSAGE_MIN_ZEICHEN - 1 Zeichen. */
export function zuKurz(text: string): boolean {
  const laenge = text.trim().length;
  return laenge > 0 && laenge < AUSSAGE_MIN_ZEICHEN;
}
