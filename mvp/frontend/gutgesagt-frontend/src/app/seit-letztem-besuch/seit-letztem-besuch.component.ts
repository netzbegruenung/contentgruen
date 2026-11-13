import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Observable, combineLatest, of } from 'rxjs';
import { distinctUntilChanged, map, switchMap } from 'rxjs/operators';

import { AuthService } from '../auth/auth.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { ROUTES } from '../shared/constants/app.constants';
import { SeitLetztemBesuchService } from './seit-letztem-besuch.service';

/** Ein Link im Block: was neu ist und wohin es fuehrt. */
export interface NeuesEintrag {
  text: string;
  ziel: string;
  /** Fuer Tests und Styles. */
  art: 'nutzung' | 'einwuerfe' | 'aussagen';
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
      text: aussagen === 1 ? '1 neue Lücke' : `${aussagen} neue Lücken`,
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
              <li><a [routerLink]="eintrag.ziel" [class]="'seit-besuch-link ' + eintrag.art">{{ eintrag.text }}</a></li>
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
  private readonly neues = inject(SeitLetztemBesuchService);

  readonly eintraege$: Observable<NeuesEintrag[]> = inject(AuthService).userInfo$.pipe(
    map((info) => info?.isAuthenticated === true),
    distinctUntilChanged(),
    switchMap((angemeldet) =>
      angemeldet
        ? combineLatest([this.usage.nutzungSeitLetztemBesuch$, this.neues.stand()]).pipe(
            map(([nutzung, stand]) => neuesListe(nutzung, stand.einwuerfe, stand.aussagen)),
          )
        : of([]),
    ),
  );
}
