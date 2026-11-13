import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, combineLatest, of } from 'rxjs';
import { distinctUntilChanged, map, switchMap } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { ROUTES } from '../shared/constants/app.constants';
import { NeuesArt, SeitLetztemBesuchService } from './seit-letztem-besuch.service';
import { lueckenWarten } from '../shared/luecke-texte';
import { LETZTER_BESUCH_AN } from '../shared/geraetespeicher-schalter';

/** Ein Link im Block: was neu ist und wohin es fuehrt. */
export interface NeuesEintrag {
  text: string;
  ziel: string;
  /** Fuer Tests und Styles, und welcher Link nach dem Klick verschwindet. */
  art: NeuesArt;
}

/** Hoechstens drei Links, je nur, wenn die Zahl groesser 0 ist. */
export function neuesListe(nutzung: number | null, einwuerfe: number, aussagen: number): NeuesEintrag[] {
  const liste: NeuesEintrag[] = [];
  if (nutzung && nutzung > 0) {
    liste.push({
      art: 'nutzung',
      ziel: ROUTES.MEINE_BEITRAEGE,
      text: nutzung === 1 ? '1 neue Nutzung deiner Beiträge' : `${nutzung} neue Nutzungen deiner Beiträge`,
    });
  }
  if (einwuerfe > 0) {
    liste.push({
      art: 'einwuerfe',
      ziel: '/fangkorb',
      text: einwuerfe === 1 ? '1 neuer Einwurf im Fangkorb' : `${einwuerfe} neue Einwürfe im Fangkorb`,
    });
  }
  if (aussagen > 0) {
    liste.push({
      art: 'aussagen',
      ziel: ROUTES.HIER_FEHLT_EINE_ANTWORT,
      text: lueckenWarten(aussagen),
    });
  }
  return liste;
}

/**
 * „Seit deinem letzten Besuch“ auf der Startseite, nur fuer Angemeldete (Nutzerfuehrung
 * 13.11.): eine ruhige Zeile mit hoechstens drei Links. Ohne Neues steht nichts da. Kein
 * roter Zaehler, nichts, das verfaellt. Die Nutzung kommt aus der Rueckmeldung beim
 * App-Start (RueckmeldungService), Fangkorb und Aussagen aus SeitLetztemBesuchService.
 */
@Component({
  selector: 'app-seit-letztem-besuch',
  standalone: true,
  imports: [AsyncPipe, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (eintraege$ | async; as eintraege) {
      @if (eintraege.length) {
        <nav class="seit-besuch" aria-labelledby="seit-besuch-titel">
          <h2 id="seit-besuch-titel" class="seit-besuch-titel">Seit deinem letzten Besuch</h2>
          <ul class="seit-besuch-liste">
            @for (eintrag of eintraege; track eintrag.art) {
              <li><a [routerLink]="eintrag.ziel" [class]="'seit-besuch-link ' + eintrag.art"
                     (click)="neues.erledigen(eintrag.art)">{{ eintrag.text }}</a></li>
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

  /**
   * Je Konto: Wechselt die Kennung, rechnet der Dienst neu und vergisst die Klicks. Bei
   * ausgeschaltetem Merker (LETZTER_BESUCH_AN) gibt es den Abschnitt nicht: kein Abruf,
   * kein Zugriff auf den Browser-Speicher.
   */
  readonly eintraege$: Observable<NeuesEintrag[]> = !inject(LETZTER_BESUCH_AN) ? of([]) : inject(AuthService).userInfo$.pipe(
    map((info) => (info?.isAuthenticated && info.userId ? info.userId : null)),
    distinctUntilChanged(),
    switchMap((kennung) =>
      kennung
        ? combineLatest([this.usage.nutzungSeitLetztemBesuch$, this.neues.stand(kennung), this.neues.erledigt$]).pipe(
            map(([nutzung, stand, erledigt]) =>
              neuesListe(nutzung, stand.einwuerfe, stand.aussagen).filter((e) => !erledigt.has(e.art)),
            ),
          )
        : of([]),
    ),
  );
}
