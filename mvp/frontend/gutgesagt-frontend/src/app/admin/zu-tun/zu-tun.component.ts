import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { combineLatest } from 'rxjs';
import { map } from 'rxjs/operators';

import {
  KEINE_SUCHANFRAGEN,
  OffeneLoeschauftraege,
  OffeneMeldungen,
  Stand,
  WartendeSuchanfragen,
  ZuTunService,
  suchanfragenText,
  wartetSeit,
} from '../../services/zu-tun.service';
import { SITZUNG_ABGELAUFEN } from '../../shared/selbst-nachladen';

/** Adresse der Moderation mit gewaehlter Ansicht (ContentModerationComponent liest ``ansicht``). */
export const MODERATION_PFAD = '/admin/moderation';

interface Ansicht {
  meldungen: Stand<OffeneMeldungen>;
  loeschauftraege: Stand<OffeneLoeschauftraege>;
  suchanfragen: Stand<WartendeSuchanfragen>;
}

/**
 * Die Zeile „Zu tun“ oben im Admin-Bereich: offene Meldungen mit dem Alter der
 * aeltesten, offene Loeschauftraege mit den ueberfaelligen, Suchanfragen, die auf
 * Freigabe warten (#664). Je Punkt ein Link auf die passende Liste der Moderation.
 * Laedt selbst nach (ZuTunService).
 */
@Component({
  selector: 'app-zu-tun',
  standalone: true,
  imports: [AsyncPipe, RouterLink, MatIconModule, MatProgressSpinnerModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (ansicht$ | async; as a) {
      <section class="zu-tun" aria-labelledby="zu-tun-titel" data-testid="zu-tun">
        <h2 id="zu-tun-titel" class="titel">Zu tun</h2>

        @if (abgelaufen(a)) {
          <!-- Nach 401/403 fragt niemand weiter: kein endloses „neuer Versuch“, sondern der Weg zurück -->
          <p class="punkt" role="status" data-testid="zu-tun-abgelaufen">
            <a routerLink="/login" [queryParams]="{ returnUrl: adresse() }">{{ sitzungAbgelaufen }}</a>
          </p>
        } @else if (nichtsZuTun(a)) {
          <p class="punkt ruhig" data-testid="zu-tun-nichts">Nichts zu tun. Keine Meldungen, keine Löschaufträge.</p>
        } @else {
          <p class="punkt" data-testid="zu-tun-meldungen">
            @if (a.meldungen.daten; as m) {
              @if (m.anzahl > 0) {
                <span><a [routerLink]="moderationPfad" [queryParams]="{ ansicht: 'pending' }">{{ meldungenText(m) }}</a>@if (m.aelteste && !m.mehr) {<span>, älteste {{ alter(m.aelteste) }}</span>}</span>
              } @else {
                <span class="ruhig">Keine offenen Meldungen</span>
              }
            } @else {
              <mat-spinner diameter="16" aria-hidden="true"></mat-spinner>
              <span role="status">{{ a.meldungen.fehler ? 'Meldungen gerade nicht erreichbar, neuer Versuch in Kürze …' : 'Lade Meldungen …' }}</span>
            }
          </p>

          <p class="punkt" data-testid="zu-tun-loeschauftraege">
            @if (a.loeschauftraege.daten; as l) {
              @if (l.anzahl > 0) {
                <a [routerLink]="moderationPfad" [queryParams]="{ ansicht: 'loeschauftraege' }">
                  {{ l.anzahl === 1 ? '1 offener Löschauftrag' : l.anzahl + ' offene Löschaufträge' }}</a>
                @if (l.ueberfaellig > 0) {
                  <span class="ueberfaellig" data-testid="zu-tun-ueberfaellig">
                    <mat-icon aria-hidden="true">warning</mat-icon>{{ l.ueberfaellig }} überfällig
                  </span>
                }
              } @else {
                <span class="ruhig">Keine offenen Löschaufträge</span>
              }
            } @else {
              <mat-spinner diameter="16" aria-hidden="true"></mat-spinner>
              <span role="status">{{ a.loeschauftraege.fehler ? 'Löschaufträge gerade nicht erreichbar, neuer Versuch in Kürze …' : 'Lade Löschaufträge …' }}</span>
            }
          </p>

          <p class="punkt" data-testid="zu-tun-suchanfragen">
            @if (a.suchanfragen.daten; as s) {
              @if (s.anzahl > 0) {
                <a [routerLink]="moderationPfad" [queryParams]="{ ansicht: 'suchanfragen' }">{{ suchanfragenText(s.anzahl) }}</a>
              } @else {
                <span class="ruhig">{{ keineSuchanfragen }}</span>
              }
            } @else {
              <mat-spinner diameter="16" aria-hidden="true"></mat-spinner>
              <span role="status">{{ a.suchanfragen.fehler ? 'Suchanfragen gerade nicht erreichbar, neuer Versuch in Kürze …' : 'Lade Suchanfragen …' }}</span>
            }
          </p>
        }

        @if (veraltet(a) && !abgelaufen(a)) {
          <p class="punkt ruhig klein" role="status">
            <mat-spinner diameter="14" aria-hidden="true"></mat-spinner>
            <span>Aktualisieren gerade nicht möglich, neuer Versuch in Kürze …</span>
          </p>
        }
      </section>
    }
  `,
  styles: [`
    .zu-tun {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--spacing-xs) var(--spacing-lg);
      padding: var(--spacing-sm) var(--spacing-md);
      margin-bottom: var(--spacing-md);
      border-left: 4px solid var(--akzent-tanne);
      border-radius: var(--border-radius-medium);
      background: var(--auswahl-grund);
    }

    /* Kleine Ueberschrift, nicht die globale h2 der Seitentitel */
    .titel {
      margin: 0;
      font-family: inherit;
      font-size: 0.875rem;
      font-weight: 700;
      font-style: normal;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-secondary);
    }

    .punkt {
      display: inline-flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 6px;
      margin: 0;
    }

    .punkt a {
      color: var(--primary-dark);
      font-weight: 700;
    }

    .ruhig {
      color: var(--text-secondary);
    }

    .klein {
      font-size: 0.875rem;
    }

    .ueberfaellig {
      display: inline-flex;
      align-items: center;
      gap: 2px;
      padding: 0 8px;
      border-radius: 12px;
      background: var(--error-bg);
      color: var(--error-color);
      font-weight: 700;
    }

    .ueberfaellig mat-icon {
      width: 18px;
      height: 18px;
      font-size: 18px;
    }
  `],
})
export class ZuTunComponent {
  readonly moderationPfad = MODERATION_PFAD;
  private readonly zuTun = inject(ZuTunService);

  readonly ansicht$ = combineLatest([this.zuTun.meldungen$, this.zuTun.loeschauftraege$, this.zuTun.suchanfragen$]).pipe(
    map(([meldungen, loeschauftraege, suchanfragen]): Ansicht => ({ meldungen, loeschauftraege, suchanfragen })),
  );

  readonly suchanfragenText = suchanfragenText;
  readonly keineSuchanfragen = KEINE_SUCHANFRAGEN;

  readonly sitzungAbgelaufen = SITZUNG_ABGELAUFEN;

  /** 401/403: Die Abfragen haben aufgehört, nur neues Anmelden hilft. */
  abgelaufen(a: Ansicht): boolean {
    return !!a.meldungen.abgelaufen || !!a.loeschauftraege.abgelaufen || !!a.suchanfragen.abgelaufen;
  }

  /** Wohin es nach dem Anmelden zurückgeht. */
  adresse(): string {
    return window.location.pathname + window.location.search;
  }

  nichtsZuTun(a: Ansicht): boolean {
    return a.meldungen.daten?.anzahl === 0 && a.loeschauftraege.daten?.anzahl === 0 && a.suchanfragen.daten?.anzahl === 0;
  }

  /** Ein Nachladen ist gescheitert, angezeigt wird der letzte Stand. */
  veraltet(a: Ansicht): boolean {
    return [a.meldungen, a.loeschauftraege, a.suchanfragen].some((stand) => !!stand.daten && stand.fehler);
  }

  meldungenText(m: OffeneMeldungen): string {
    if (m.anzahl === 1) {
      return '1 offene Meldung';
    }
    return m.mehr ? `${m.anzahl} oder mehr offene Meldungen` : `${m.anzahl} offene Meldungen`;
  }

  alter(zeitpunkt: string): string {
    return wartetSeit(zeitpunkt);
  }
}
