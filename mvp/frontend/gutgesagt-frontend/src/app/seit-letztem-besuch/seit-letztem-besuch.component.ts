import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Observable, combineLatest, of } from 'rxjs';
import { distinctUntilChanged, map, switchMap } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { BesuchResponse, UsageTrackingService } from '../services/usage-tracking.service';
import { MEINE_TAB_PARAM } from '../services/navigation.service';
import { PAGE_TITLES, ROUTES } from '../shared/constants/app.constants';
import { NeuesArt, SeitLetztemBesuchService } from './seit-letztem-besuch.service';
import { LUECKE } from '../shared/luecke-texte';
import { MENUE_ICONS } from '../shared/fangkorb-texte';

/** Hoechstens so viele Kacheln nebeneinander (Entscheidung 20.11.). */
export const MAX_KACHELN = 4;

/**
 * Zeitraum der Kacheln ohne Zaehlerstand, wie BESUCH_ZEITRAUM_TAGE im Backend
 * (api/v1/usage.py): Dafuer wird nichts gespeichert, deshalb nennt die Kachel ihn.
 */
export const ZEITRAUM = 'letzte 7 Tage';

/** Eine Kachel im Block: was neu ist und wohin es fuehrt. */
export interface NeuesEintrag {
  /** Grosse Zahl auf der Kachel, an der Grenze der Lueckenliste etwa „50+“. */
  zahl: string;
  /** Kurzer sichtbarer Text unter der Zahl. */
  wort: string;
  /** Nur bei Zahlen ueber einen Zeitraum statt seit dem letzten Besuch: welcher. */
  zeitraum?: string;
  /**
   * Der ganze Satz fuer Screenreader (aria-label). Er enthaelt Zahl, Wort und Zeitraum so,
   * wie sie sichtbar sind, damit auch Sprachsteuerung die Kachel unter ihrem Text findet.
   */
  satz: string;
  /** Ist sie allein, eine breite Zeile: der Satz nach der Zahl … */
  zeile: string;
  /** … und der Knopf zum Ziel. */
  knopf: string;
  /** Material-Icon links neben der Zahl. */
  icon: string;
  ziel: string;
  queryParams?: Record<string, string>;
  fragment?: string;
  /** Fuer Tests und Styles, und welche Kachel nach dem Klick verschwindet. */
  art: NeuesArt;
}

/** Die Zahlen aus der Antwort des Besuchs, die der Block braucht. */
export type NeuesStand = Partial<BesuchResponse>;

/** Nur echte positive Zahlen; alles andere (null, fehlend, negativ) zaehlt als 0. */
const positiv = (wert: number | null | undefined): number => (wert && wert > 0 ? wert : 0);

/**
 * Alle Kacheln mit Neuem (Zahl groesser 0), in der Reihenfolge, in der sie stehen und
 * in der sie bei mehr als MAX_KACHELN wegfallen: zuerst, was die eigenen Beitraege und
 * Einwuerfe betrifft, zuletzt die neuen Beitraege, die „Frisch aus der Community“ direkt
 * darunter ohnehin zeigt.
 */
export function neuesListe(stand: NeuesStand): NeuesEintrag[] {
  const liste: NeuesEintrag[] = [];

  const nutzung = positiv(stand.nutzung_seit_letztem_besuch);
  if (nutzung) {
    const wort = nutzung === 1 ? 'Nutzung deiner Beiträge' : 'Nutzungen deiner Beiträge';
    liste.push({
      art: 'nutzung',
      ziel: ROUTES.MEINE_BEITRAEGE,
      icon: 'trending_up',
      zahl: `${nutzung}`,
      wort,
      satz: `${nutzung} ${wort}`,
      zeile: `${wort}. Sieh nach, welche genutzt werden.`,
      knopf: PAGE_TITLES.MEINE_BEITRAEGE,
    });
  }

  const ausformuliert = positiv(stand.ausformulierte_einwuerfe);
  if (ausformuliert) {
    const eins = ausformuliert === 1;
    const wort = eins ? 'Einwurf von dir ausformuliert' : 'Einwürfe von dir ausformuliert';
    liste.push({
      art: 'ausformuliert',
      ziel: ROUTES.MEINE_BEITRAEGE,
      queryParams: { [MEINE_TAB_PARAM]: 'einwuerfe' },
      icon: 'task_alt',
      zahl: `${ausformuliert}`,
      wort,
      zeitraum: ZEITRAUM,
      satz: `${ausformuliert} ${wort}, ${ZEITRAUM}`,
      zeile: eins
        ? 'Einwurf von dir hat jemand in den letzten 7 Tagen ausformuliert.'
        : 'Einwürfe von dir haben andere in den letzten 7 Tagen ausformuliert.',
      knopf: 'Meine Einwürfe',
    });
  }

  const einwuerfe = positiv(stand.neue_einwuerfe);
  if (einwuerfe) {
    const eins = einwuerfe === 1;
    const wort = eins ? 'neuer Einwurf im Fangkorb' : 'neue Einwürfe im Fangkorb';
    liste.push({
      art: 'einwuerfe',
      ziel: ROUTES.RAW_INPUT_LIST,
      icon: MENUE_ICONS.einwerfen,
      zahl: `${einwuerfe}`,
      wort,
      satz: `${einwuerfe} ${wort}`,
      zeile: eins ? 'neuer Einwurf wartet im Fangkorb.' : 'neue Einwürfe warten im Fangkorb.',
      knopf: `Zum ${PAGE_TITLES.RAW_INPUT_LIST}`,
    });
  }

  const aussagen = positiv(stand.unbeantwortete_aussagen);
  if (aussagen) {
    const mehr = stand.unbeantwortete_aussagen_mehr ?? false;
    const zahl = mehr ? `${aussagen}+` : `${aussagen}`;
    const eine = aussagen === 1 && !mehr;
    const wort = eine ? 'Aussage ohne Antwort' : 'Aussagen ohne Antwort';
    liste.push({
      art: 'aussagen',
      ziel: ROUTES.HIER_FEHLT_EINE_ANTWORT,
      icon: 'question_answer',
      zahl,
      wort,
      // Beginnt mit dem sichtbaren Text, damit Sprachsteuerung ihn trifft (WCAG 2.5.3)
      satz: `${zahl} ${wort}: ${eine ? LUECKE.einzahl : LUECKE.mehrzahl} in „${PAGE_TITLES.HIER_FEHLT_EINE_ANTWORT}“`,
      zeile: eine ? 'Aussage wartet auf eine Antwort.' : 'Aussagen warten auf eine Antwort.',
      knopf: PAGE_TITLES.HIER_FEHLT_EINE_ANTWORT,
    });
  }

  const beitraege = positiv(stand.neue_beitraege);
  if (beitraege) {
    const wort = beitraege === 1 ? 'neuer Beitrag' : 'neue Beiträge';
    liste.push({
      art: 'beitraege',
      // Die Startseite ist /search; '/' leitet um und verliert dabei den Anker
      ziel: ROUTES.SEARCH,
      fragment: 'recent-content',
      icon: 'feed',
      zahl: `${beitraege}`,
      wort,
      zeitraum: ZEITRAUM,
      satz: `${beitraege} ${wort}, ${ZEITRAUM}`,
      zeile: `${wort} aus der Community in den letzten 7 Tagen.`,
      knopf: 'Frisch aus der Community',
    });
  }

  return liste;
}

/**
 * „Seit deinem letzten Besuch“ auf der Startseite, nur fuer Angemeldete (Nutzerfuehrung
 * 13.11.): bis zu vier kleine Kacheln mit Zahl im Stil der Mitmachen-Kacheln, die ganze
 * Kachel ist der Link (Entscheidungen 18.11. und 20.11.). Bleibt nur eine, wird sie eine
 * breite Zeile mit Satz und Knopf. Ohne Neues steht nichts da. Kein roter Zaehler,
 * nichts, das verfaellt. Alle Zahlen stammen aus der Antwort des Besuchs beim App-Start
 * (RueckmeldungService), ohne eigenen Abruf.
 */
@Component({
  selector: 'app-seit-letztem-besuch',
  standalone: true,
  imports: [AsyncPipe, RouterLink, MatButtonModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (eintraege$ | async; as eintraege) {
      @if (eintraege.length) {
        <nav class="seit-besuch" aria-labelledby="seit-besuch-titel">
          <h2 id="seit-besuch-titel">Seit deinem letzten Besuch</h2>
          @if (eintraege.length === 1) {
            @let eintrag = eintraege[0];
            <div [class]="'seit-besuch-zeile ' + eintrag.art">
              <mat-icon class="seit-besuch-icon" aria-hidden="true">{{ eintrag.icon }}</mat-icon>
              <p class="seit-besuch-satz" id="seit-besuch-satz">
                <span class="seit-besuch-zahl">{{ eintrag.zahl }}</span> {{ eintrag.zeile }}
              </p>
              <a mat-flat-button class="seit-besuch-knopf" [routerLink]="eintrag.ziel"
                 [queryParams]="eintrag.queryParams" [fragment]="eintrag.fragment"
                 aria-describedby="seit-besuch-satz" (click)="neues.erledigen(eintrag.art)">
                {{ eintrag.knopf }}
                <mat-icon iconPositionEnd aria-hidden="true">arrow_forward</mat-icon>
              </a>
            </div>
          } @else {
            <ul class="seit-besuch-kacheln" [class.vier]="eintraege.length === 4"
                [style.--seit-besuch-spalten]="eintraege.length">
              @for (eintrag of eintraege; track eintrag.art) {
                <li>
                  <a [routerLink]="eintrag.ziel" [queryParams]="eintrag.queryParams" [fragment]="eintrag.fragment"
                     [class]="'seit-besuch-kachel ' + eintrag.art"
                     [attr.aria-label]="eintrag.satz" (click)="neues.erledigen(eintrag.art)">
                    <span class="seit-besuch-kopf">
                      <mat-icon class="seit-besuch-icon" aria-hidden="true">{{ eintrag.icon }}</mat-icon>
                      <span class="seit-besuch-zahl">{{ eintrag.zahl }}</span>
                    </span>
                    <span class="seit-besuch-wort">{{ eintrag.wort }}</span>
                    @if (eintrag.zeitraum) {
                      <span class="seit-besuch-zeitraum">{{ eintrag.zeitraum }}</span>
                    }
                  </a>
                </li>
              }
            </ul>
          }
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
            ? neuesListe(stand)
                .filter((e) => !erledigt.has(e.art))
                .slice(0, MAX_KACHELN)
            : [],
        ),
      );
    }),
  );
}
