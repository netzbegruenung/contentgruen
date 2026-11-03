import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, Input, OnChanges, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Subject, of, timer } from 'rxjs';
import { catchError, distinctUntilChanged, map, switchMap } from 'rxjs/operators';

import {
  SPRACHHINWEIS_AB_WOERTERN,
  SPRACHHINWEIS_VERZOEGERUNG_MS,
  SprachhinweisService,
  woerterZaehlen,
} from './sprachhinweis.service';

const SAETZE = {
  beitrag:
    'Dieser Beitrag ist offenbar nicht auf Deutsch. Gut gesagt ist auf deutsche Texte ausgelegt; speichern kannst du trotzdem.',
  aussage:
    'Diese Aussage ist offenbar nicht auf Deutsch. Gut gesagt ist auf deutsche Texte ausgelegt; anlegen kannst du sie trotzdem.',
} as const;

/** Zu viele Anfragen: Der letzte Stand bleibt stehen, wie beim Gegenlesen. */
const ZU_VIELE = 'zu-viele' as const;

/**
 * Der Sprachhinweis (#405): Ist ein Beitrag oder eine neue Aussage ab fünf Wörtern
 * offenbar nicht deutsch, sagt ein Satz das, etwa eine Sekunde nach der letzten Eingabe.
 * Er sperrt nichts. Antwortet der Dienst nicht, steht einfach nichts da; beim Rate-Limit
 * bleibt der letzte Stand.
 */
@Component({
  selector: 'app-sprachhinweis',
  standalone: true,
  imports: [CommonModule],
  template: `<div aria-live="polite"><p *ngIf="fremd" class="sprachhinweis">{{ satz }}</p></div>`,
  styles: [
    `
      .sprachhinweis {
        margin: 8px 0;
        color: var(--text-secondary);
        font-size: 0.875rem;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SprachhinweisComponent implements OnChanges {
  /** Bei einem Beitrag sein Titel; erkannt werden Titel und Text zusammen. */
  @Input() titel: string | null = '';
  /** Der Text des Beitrags oder der Aussage. */
  @Input() text: string | null = '';
  @Input() gegenstand: keyof typeof SAETZE = 'beitrag';

  fremd = false;

  private readonly eingabe = new Subject<string>();

  constructor(service: SprachhinweisService, cdr: ChangeDetectorRef) {
    this.eingabe
      .pipe(
        map((text) => text.trim()),
        distinctUntilChanged(),
        // Kurze Texte sofort ohne Sprachhinweis und ohne Anfrage; sonst erst nach der Pause.
        switchMap((text) =>
          woerterZaehlen(text) < SPRACHHINWEIS_AB_WOERTERN
            ? of(false)
            : timer(SPRACHHINWEIS_VERZOEGERUNG_MS).pipe(
                switchMap(() => service.fremdsprache(text)),
                map((antwort) => antwort.sprache !== null),
                catchError((fehler: unknown) =>
                  of(fehler instanceof HttpErrorResponse && fehler.status === 429 ? ZU_VIELE : false),
                ),
              ),
        ),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe((fremd) => {
        if (fremd === ZU_VIELE) return;
        this.fremd = fremd;
        cdr.markForCheck();
      });
  }

  get satz(): string {
    return SAETZE[this.gegenstand];
  }

  ngOnChanges(): void {
    this.eingabe.next([this.titel, this.text].filter((teil) => teil?.trim()).join('\n'));
  }
}
