import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';

import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { CONTENT_TYPE_REGISTRY, resolveContentType } from '../shared/content-type-registry';
import { LoggingService } from '../services/logging.service';
import { VariantenBeitrag, VariantenService } from '../services/varianten.service';

export const ORIGINAL_NICHT_DA = 'Diesen Beitrag gibt es nicht mehr.';
export const NICHT_GELADEN = 'Die Varianten konnten nicht geladen werden.';

/** Ein Beitrag aus /varianten als Karte; kein Suchtreffer, also ohne Aussage. */
export function alsKarte(beitrag: VariantenBeitrag): KartenDaten | null {
  const typ = resolveContentType(beitrag.result_type);
  const feld = typ && CONTENT_TYPE_REGISTRY[typ].resultField;
  if (!feld) {
    return null;
  }
  return ausSuchergebnis({
    score: 1.0,
    statement_text: null,
    statement_similarity_score: null,
    reply_relevance: null,
    content_type: typ,
    [feld]: beitrag,
  });
}

/**
 * Die Varianten eines Beitrags (#356, Glossar "Variante"): oben das Original, darunter
 * die Beitraege, die jemand mit ihm als Vorlage angelegt hat. Ziel von "N Varianten"
 * an der Karte.
 */
@Component({
  selector: 'app-varianten',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, BeitragskarteComponent, KartenlisteComponent],
  templateUrl: './varianten.component.html',
  styleUrls: ['./varianten.component.css'],
})
export class VariantenComponent implements OnInit {
  original: KartenDaten | null = null;
  varianten: KartenDaten[] = [];
  laedt = true;
  fehler: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private service: VariantenService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
  ) {}

  ngOnInit(): void {
    // Fehler je Laden abfangen: Sonst beendete ein gescheitertes Laden den Strom,
    // und eine spaetere Adresse luede nichts mehr.
    this.route.paramMap
      .pipe(
        switchMap((params) => {
          this.laedt = true;
          this.fehler = null;
          return this.service.laden(params.get('id') ?? '').pipe(
            catchError((error) => {
              this.logger.warn('Varianten nicht geladen', error);
              this.fehler = error?.status === 404 ? ORIGINAL_NICHT_DA : NICHT_GELADEN;
              return of(null);
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((antwort) => {
        this.original = antwort ? alsKarte(antwort.original) : null;
        this.varianten = antwort ? antwort.varianten.map(alsKarte).filter((k): k is KartenDaten => !!k) : [];
        this.laedt = false;
        this.cdr.markForCheck();
      });
  }
}
