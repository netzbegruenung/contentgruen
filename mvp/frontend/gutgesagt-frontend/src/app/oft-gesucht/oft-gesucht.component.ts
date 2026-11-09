import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  Input,
  OnInit,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, forkJoin, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { AussageKurz, ContentService } from '../services/content.service';
import { ROUTES } from '../shared/constants/app.constants';
import { SUCHTEXT_PARAM } from '../shared/formular-adresse';

/** Wie viele Aussagen der Abschnitt zeigt. */
export const OFT_GESUCHT_ANZAHL = 3;

/** Wie viele Beitraege hoechstens nachgeladen werden, um ihre Aussagen zu finden. */
const HOECHSTENS_BEITRAEGE = 6;

/** Woher die Aussagen kommen: oft genutzte Beitraege dieser Woche, sonst die neuesten. */
export type OftGesuchtQuelle = 'oft-genutzt' | 'neueste';

export const OFT_GESUCHT_TITEL: Record<OftGesuchtQuelle, string> = {
  'oft-genutzt': 'Oft gesucht',
  neueste: 'Zuletzt beantwortet',
};

/**
 * Bis zu drei Aussagen, jede einmal, ohne die der eigenen Suche. Gross- und
 * Kleinschreibung und Leerraum am Rand zaehlen nicht.
 */
export function aussagenAuswaehlen(aussagen: (AussageKurz | null | undefined)[], suchtext: string): AussageKurz[] {
  const gleich = (text: string) => text.trim().toLocaleLowerCase('de');
  const gesehen = new Set<string>([gleich(suchtext)]);
  const gewaehlt: AussageKurz[] = [];
  for (const aussage of aussagen) {
    const text = aussage?.text?.trim();
    if (!aussage || !text || gesehen.has(gleich(text))) {
      continue;
    }
    gesehen.add(gleich(text));
    gewaehlt.push({ id: aussage.id, text });
    if (gewaehlt.length === OFT_GESUCHT_ANZAHL) {
      break;
    }
  }
  return gewaehlt;
}

/**
 * "Oft gesucht" auf der Ergebnisseite ohne Treffer (#642, R51): Auch wer nichts
 * gefunden hat und kein Konto hat, bekommt einen Weg weiter - drei beliebte
 * Aussagen als Suche und den Link "Hier fehlt eine Antwort".
 *
 * Beliebt heisst: die Aussagen, auf die die oft genutzten Beitraege dieser Woche
 * antworten (dieselbe Auswahl wie "Diese Woche oft genutzt" auf dem Start). Gibt es
 * die nicht, die Aussagen der neuesten Beitraege, dann mit dem Titel "Zuletzt
 * beantwortet". Beide Endpunkte und die Beitragsadresse sind auch fuer Besucher
 * offen. Kommt nichts, bleibt nur der Link.
 */
@Component({
  selector: 'app-oft-gesucht',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterLink],
  templateUrl: './oft-gesucht.component.html',
  styleUrls: ['./oft-gesucht.component.css'],
})
export class OftGesuchtComponent implements OnInit {
  /** Der Suchtext ohne Treffer; diese Aussage wird nicht noch einmal vorgeschlagen. */
  @Input() suchtext = '';

  aussagen: AussageKurz[] = [];
  quelle: OftGesuchtQuelle = 'oft-genutzt';

  readonly ergebnisse = ROUTES.RESULT;
  readonly hierFehltEineAntwort = ROUTES.HIER_FEHLT_EINE_ANTWORT;

  constructor(
    private usage: UsageTrackingService,
    private content: ContentService,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
  ) {}

  get titel(): string {
    return OFT_GESUCHT_TITEL[this.quelle];
  }

  ngOnInit(): void {
    this.ausBeitraegen(this.usage.getOftGenutzt().pipe(map((a) => a.results ?? [])))
      .pipe(
        switchMap((oft) =>
          oft.length
            ? of({ quelle: 'oft-genutzt' as const, aussagen: oft })
            : this.ausBeitraegen(
                this.content.getRecentContent(HOECHSTENS_BEITRAEGE).pipe(map((a) => a.results ?? [])),
              ).pipe(map((aussagen) => ({ quelle: 'neueste' as const, aussagen }))),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ quelle, aussagen }) => {
        this.quelle = quelle;
        this.aussagen = aussagen;
        this.cdr.markForCheck();
      });
  }

  /** Query-Parameter, um nach einer Aussage zu suchen. */
  sucheNach(aussage: AussageKurz): Record<string, string> {
    return { [SUCHTEXT_PARAM]: aussage.text };
  }

  /** Die Aussagen der Beitraege aus einer Liste; Fehler ergeben eine leere Liste. */
  private ausBeitraegen(beitraege$: Observable<{ id?: string }[]>): Observable<AussageKurz[]> {
    return beitraege$.pipe(
      catchError(() => of([] as { id?: string }[])),
      switchMap((beitraege) => {
        const ids = [...new Set(beitraege.map((b) => b?.id).filter((id): id is string => !!id))].slice(
          0,
          HOECHSTENS_BEITRAEGE,
        );
        if (!ids.length) {
          return of([] as AussageKurz[]);
        }
        return forkJoin(
          ids.map((id) =>
            this.content.beitragLaden(id).pipe(
              map((beitrag) => beitrag.aussage ?? null),
              catchError(() => of(null)),
            ),
          ),
        ).pipe(map((aussagen) => aussagenAuswaehlen(aussagen, this.suchtext)));
      }),
    );
  }
}
