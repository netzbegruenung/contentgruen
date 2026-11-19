import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { Observable, combineLatest, of } from 'rxjs';
import { distinctUntilChanged, map, switchMap } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { PAGE_TITLES, ROUTES } from '../shared/constants/app.constants';
import { NeuesArt, SeitLetztemBesuchService } from './seit-letztem-besuch.service';
import { LUECKE } from '../shared/luecke-texte';
import { MENUE_ICONS } from '../shared/fangkorb-texte';

/** Eine Kachel im Block: was neu ist und wohin es fuehrt. */
export interface NeuesEintrag {
  /** Grosse Zahl auf der Kachel, an der Grenze der Lueckenliste etwa „50+“. */
  zahl: string;
  /** Kurzer sichtbarer Text unter der Zahl. */
  wort: string;
  /**
   * Der ganze Satz fuer Screenreader (aria-label). Er enthaelt Zahl und Wort so, wie sie
   * sichtbar sind, damit auch Sprachsteuerung die Kachel unter ihrem Text findet.
   */
  satz: string;
  /** Material-Icon links neben der Zahl. */
  icon: string;
  ziel: string;
  /** Fuer Tests und Styles, und welche Kachel nach dem Klick verschwindet. */
  art: NeuesArt;
}

/** Hoechstens drei Kacheln, je nur, wenn die Zahl groesser 0 ist. */
export function neuesListe(nutzung: number | null, einwuerfe: number, aussagen: number, aussagenMehr = false): NeuesEintrag[] {
  const liste: NeuesEintrag[] = [];
  if (nutzung && nutzung > 0) {
    const nutzungWort = nutzung === 1 ? 'Nutzung deiner Beiträge' : 'Nutzungen deiner Beiträge';
    liste.push({
      art: 'nutzung',
      ziel: ROUTES.MEINE_BEITRAEGE,
      icon: 'trending_up',
      zahl: `${nutzung}`,
      wort: nutzungWort,
      satz: `${nutzung} ${nutzungWort}`,
    });
  }
  if (einwuerfe > 0) {
    const wort = einwuerfe === 1 ? 'neuer Einwurf im Fangkorb' : 'neue Einwürfe im Fangkorb';
    liste.push({
      art: 'einwuerfe',
      ziel: '/fangkorb',
      icon: MENUE_ICONS.einwerfen,
      zahl: `${einwuerfe}`,
      wort,
      satz: `${einwuerfe} ${wort}`,
    });
  }
  if (aussagen > 0) {
    const zahl = aussagenMehr ? `${aussagen}+` : `${aussagen}`;
    const eine = aussagen === 1 && !aussagenMehr;
    const wort = eine ? 'Aussage ohne Antwort' : 'Aussagen ohne Antwort';
    liste.push({
      art: 'aussagen',
      ziel: ROUTES.HIER_FEHLT_EINE_ANTWORT,
      icon: 'question_answer',
      zahl,
      wort,
      // Beginnt mit dem sichtbaren Text, damit Sprachsteuerung ihn trifft (WCAG 2.5.3)
      satz: `${zahl} ${wort}: ${eine ? LUECKE.einzahl : LUECKE.mehrzahl} in „${PAGE_TITLES.HIER_FEHLT_EINE_ANTWORT}“`,
    });
  }
  return liste;
}

/**
 * „Seit deinem letzten Besuch“ auf der Startseite, nur fuer Angemeldete (Nutzerfuehrung
 * 13.11.): hoechstens drei kleine Kacheln mit Zahl im Stil der Mitmachen-Kacheln
 * (Entscheidung 18.11.); die ganze Kachel ist der Link. Ohne Neues steht nichts da. Kein
 * roter Zaehler, nichts, das verfaellt. Alle Zahlen stammen aus der Antwort des Besuchs
 * beim App-Start (RueckmeldungService), ohne eigenen Abruf.
 */
@Component({
  selector: 'app-seit-letztem-besuch',
  standalone: true,
  imports: [AsyncPipe, RouterLink, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (eintraege$ | async; as eintraege) {
      @if (eintraege.length) {
        <nav class="seit-besuch" aria-labelledby="seit-besuch-titel">
          <h2 id="seit-besuch-titel">Seit deinem letzten Besuch</h2>
          <ul class="seit-besuch-kacheln">
            @for (eintrag of eintraege; track eintrag.art) {
              <li>
                <a [routerLink]="eintrag.ziel" [class]="'seit-besuch-kachel ' + eintrag.art"
                   [attr.aria-label]="eintrag.satz" (click)="neues.erledigen(eintrag.art)">
                  <span class="seit-besuch-kopf">
                    <mat-icon class="seit-besuch-icon" aria-hidden="true">{{ eintrag.icon }}</mat-icon>
                    <span class="seit-besuch-zahl">{{ eintrag.zahl }}</span>
                  </span>
                  <span class="seit-besuch-wort">{{ eintrag.wort }}</span>
                </a>
              </li>
            }
          </ul>
        </nav>
      }
    }
  `,
  styleUrls: ['./seit-letztem-besuch.component.css'],
})
export class SeitLetztemBesuchComponent {
  private readonly usage = inject(UsageTrackingService);
  protected readonly neues = inject(SeitLetztemBesuchService);

  /** Je Konto: Wechselt die Kennung, kommt ein neuer Besuch und die Klicks gelten nicht mehr. */
  readonly eintraege$: Observable<NeuesEintrag[]> = inject(AuthService).userInfo$.pipe(
    map((info) => (info?.isAuthenticated && info.userId ? info.userId : null)),
    distinctUntilChanged(),
    switchMap((kennung) => {
      if (!kennung) {
        return of([]);
      }
      this.neues.fuer(kennung);
      return combineLatest([this.usage.besuchStand$, this.neues.erledigt$]).pipe(
        map(([stand, erledigt]) =>
          stand
            ? neuesListe(
                stand.nutzung_seit_letztem_besuch,
                stand.neue_einwuerfe ?? 0,
                stand.unbeantwortete_aussagen ?? 0,
                stand.unbeantwortete_aussagen_mehr ?? false,
              ).filter((e) => !erledigt.has(e.art))
            : [],
        ),
      );
    }),
  );
}
