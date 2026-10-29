import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { BreakpointObserver } from '@angular/cdk/layout';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { ResultCarouselComponent } from '../result-carousel/result-carousel.component';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { CONTENT_TYPE_REGISTRY, resolveContentType } from '../shared/content-type-registry';

/**
 * "Diese Woche oft genutzt" auf der Startseite (#364, docs/VISION.md "Trends").
 *
 * Welche Beitraege oft genug genutzt wurden, entscheidet das Backend
 * (services/oft_genutzt_service.py). Kommt nichts, gibt es keinen Bereich: keine
 * Ueberschrift, kein Leer-Hinweis, kein Lade-Spinner - die Startseite sieht dann
 * aus wie vorher.
 */
@Component({
  selector: 'app-oft-genutzt',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, ResultCarouselComponent, KartenlisteComponent],
  templateUrl: './oft-genutzt.component.html',
  styleUrls: ['./oft-genutzt.component.css'],
})
export class OftGenutztComponent implements OnInit {
  karten: KartenDaten[] = [];
  /** Bis 599 px eine Liste, darueber das Karussell (wie "Neueste Inhalte"). */
  istMobil = false;

  constructor(
    private usage: UsageTrackingService,
    private breakpointObserver: BreakpointObserver,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
  ) {}

  ngOnInit(): void {
    this.breakpointObserver
      .observe('(max-width: 599px)')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((zustand) => {
        this.istMobil = zustand.matches;
        this.cdr.markForCheck();
      });

    this.usage
      .getOftGenutzt()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((antwort) => {
        this.karten = antwort.results.flatMap((beitrag) => {
          const typ = resolveContentType(beitrag.result_type);
          const feld = typ && CONTENT_TYPE_REGISTRY[typ].resultField;
          if (!feld) {
            return [];
          }
          // Kein Suchtreffer: ohne Aussage, Aehnlichkeit und Relevanz.
          return [ausSuchergebnis({
            score: 1.0,
            statement_text: null,
            statement_similarity_score: null,
            reply_relevance: null,
            content_type: typ,
            [feld]: beitrag,
          })];
        });
        this.cdr.markForCheck();
      });
  }
}
