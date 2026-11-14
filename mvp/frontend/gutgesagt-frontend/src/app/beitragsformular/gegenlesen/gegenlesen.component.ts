import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, Input, OnChanges, SimpleChanges, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Subject, of } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, filter, map, switchMap } from 'rxjs/operators';

import { SiegelComponent } from '../../shared/components/siegel/siegel.component';
import { GEGENLESEN_VERZOEGERUNG_MS, Gegengelesen, GegenlesenService } from './gegenlesen.service';

/** Was gerade im Formular steht. */
interface Eingabe {
  titel: string;
  text: string;
  aussage: string;
  titelIstBehauptung: boolean;
}

/**
 * Hintergrundinfo ohne Herkunft (Persona-Test Gerd, 13.11.): eine feste Regel im Formular,
 * ohne Aufruf beim Dienst. Sie zählt nicht in die Güte, die rechnet der Dienst.
 */
export const HERKUNFT_FEHLT = 'Ohne Herkunft glaubt dir das kaum jemand. Nenn, woher es stammt: ein Link oder eine Fundstelle.';

const NOCH_LEER: Gegengelesen = { guete: null, anmerkungen: [] };

/**
 * So lange nach dem letzten Ergebnis und der letzten Eingabe wartet die Ansage fuer
 * Screenreader: Sonst meldete sie sich bei jeder Tipp-Pause von einer Sekunde.
 */
export const ANSAGE_PAUSE_MS = 1500;

/**
 * Die Zahl der Anmerkungen in Worten; leer, solange nichts gegengelesen ist. ``zusaetzlich``
 * zaehlt Anmerkungen des Formulars mit, etwa die fehlende Herkunft (HERKUNFT_FEHLT).
 */
export function zusammenfassung(ergebnis: Gegengelesen, zusaetzlich = 0): string {
  if (ergebnis.guete === null) {
    return '';
  }
  const anzahl = ergebnis.anmerkungen.length + zusaetzlich;
  if (!anzahl) {
    return 'Nichts aufgefallen';
  }
  return anzahl === 1 ? '1 Anmerkung' : `${anzahl} Anmerkungen`;
}

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
  /** Kommentar und Hintergrundinfo behaupten im Titel; ein Post-Titel beschreibt, ohne Verneinungsregel. */
  @Input() titelIstBehauptung = true;
  /** Das Formular hat ein Herkunftsfeld, und es ist leer; nur die Hintergrundinfo setzt das. */
  @Input() herkunftFehlt = false;

  readonly herkunftHinweis = HERKUNFT_FEHLT;
  /**
   * Kompakt direkt unter dem Textfeld, wenn das Formular einspaltig ist: eine Zeile mit
   * Siegel und Zahl der Anmerkungen, aufklappbar. Sonst neben der Vorschau, ganz offen.
   */
  @Input() kompakt = false;

  ergebnis: Gegengelesen = NOCH_LEER;
  verfuegbar = true;
  /**
   * Kompakt: ob die Anmerkungen aufgeklappt sind. Mit der ersten Anmerkung klappt die
   * Zeile von selbst auf, zugeklappt wurde "1 Anmerkung" uebersehen (Persona-Runde 2,
   * P33); hat die Person selbst umgeschaltet, bleibt es bei ihrer Wahl.
   */
  offen = false;
  private vonHandGeschaltet = false;
  /** Was die Live-Region ansagt: nur die Zahl, entprellt (ANSAGE_PAUSE_MS). */
  ansage = '';

  private readonly eingabe = new Subject<Eingabe>();
  /** Jede Eingabe (null) und jedes Ergebnis (die Zahl) schiebt die Ansage auf. */
  private readonly ansageTakt = new Subject<string | null>();

  /** Erst, wenn schon etwas geschrieben ist: Ein leeres Formular soll nicht mahnen. */
  get zeigtHerkunftHinweis(): boolean {
    return this.herkunftFehlt && this.ergebnis.guete !== null;
  }

  get istGut(): boolean {
    return this.ergebnis.guete !== null && !this.ergebnis.anmerkungen.length && !this.zeigtHerkunftHinweis;
  }

  /** Die kompakte Zeile: die Zahl, oder vor dem ersten Gegenlesen eine Einladung. */
  get zeile(): string {
    return zusammenfassung(this.ergebnis, this.herkunftZusatz) || 'liest mit, sobald du schreibst';
  }

  /** Der Herkunftshinweis zaehlt in Zeile und Ansage als eine Anmerkung mit. */
  private get herkunftZusatz(): number {
    return this.zeigtHerkunftHinweis ? 1 : 0;
  }

  constructor(service: GegenlesenService, cdr: ChangeDetectorRef) {
    this.ansageTakt
      .pipe(
        debounceTime(ANSAGE_PAUSE_MS),
        filter((text): text is string => text !== null),
        distinctUntilChanged(),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe((text) => {
        this.ansage = text;
        cdr.markForCheck();
      });

    this.eingabe
      .pipe(
        debounceTime(GEGENLESEN_VERZOEGERUNG_MS),
        map((e) => ({ ...e, titel: e.titel.trim(), text: e.text.trim(), aussage: e.aussage.trim() })),
        distinctUntilChanged(
          (a, b) =>
            a.titel === b.titel &&
            a.text === b.text &&
            a.aussage === b.aussage &&
            a.titelIstBehauptung === b.titelIstBehauptung,
        ),
        switchMap((e) =>
          !e.titel && !e.text
            ? of(NOCH_LEER)
            : service
                .gegenlesen(e.titel, e.text, e.aussage, e.titelIstBehauptung)
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
        if (ergebnis) {
          this.ergebnis = ergebnis;
          if (this.kompakt && !this.vonHandGeschaltet && (ergebnis.anmerkungen.length || this.zeigtHerkunftHinweis)) {
            this.offen = true;
          }
          this.ansageTakt.next(zusammenfassung(ergebnis, this.herkunftZusatz));
        }
        cdr.markForCheck();
      });
  }

  umschalten(): void {
    this.offen = !this.offen;
    this.vonHandGeschaltet = true;
  }

  ngOnChanges(changes: SimpleChanges): void {
    const nurHerkunft = !!changes['herkunftFehlt'] && Object.keys(changes).length === 1;
    if (nurHerkunft) {
      // Kein neues Gegenlesen (die Eingabe ist dieselbe), aber die Zahl aendert sich:
      // die Ansage aus dem jetzigen Stand nachziehen, statt sie mit null zu verwerfen.
      if (this.ergebnis.guete !== null) {
        this.ansageTakt.next(zusammenfassung(this.ergebnis, this.herkunftZusatz));
      }
      return;
    }
    this.ansageTakt.next(null);
    this.eingabe.next({
      titel: this.titel ?? '',
      text: this.text ?? '',
      aussage: this.aussage ?? '',
      titelIstBehauptung: this.titelIstBehauptung,
    });
  }
}
