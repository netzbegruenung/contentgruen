import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';

import { ZuTunService } from '../../../services/zu-tun.service';

/**
 * Die Zahl offener Meldungen am Admin-Link im Kopf und im Menue. Sie laedt selbst
 * nach (ZuTunService); ohne offene Meldungen steht nichts da.
 *
 * Steht nur im Link fuer Admins, deshalb fragen andere nie. Die Ziffer ist fuer
 * Screenreader stumm, sie lesen „2 offene Meldungen“ als Teil des Links.
 */
@Component({
  selector: 'app-offene-meldungen-zahl',
  standalone: true,
  imports: [AsyncPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if ((meldungen$ | async)?.daten; as offen) {
      @if (offen.anzahl > 0) {
        <span class="zahl" aria-hidden="true">{{ offen.mehr ? offen.anzahl + '+' : offen.anzahl }}</span>
        <span class="visually-hidden">, {{ offen.anzahl === 1 ? '1 offene Meldung' : offen.anzahl + (offen.mehr ? ' oder mehr' : '') + ' offene Meldungen' }}</span>
      }
    }
  `,
  styles: [`
    :host {
      display: inline-flex;
    }

    .zahl {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 20px;
      height: 20px;
      padding: 0 6px;
      margin-left: 6px;
      box-sizing: border-box;
      border-radius: 10px;
      background: var(--error-color);
      color: var(--bg-card); /* hell auf Rot, im Dunkeln dunkel auf Hellrot */
      font-size: 12px;
      font-weight: 700;
      line-height: 1;
      text-decoration: none;
    }
  `],
})
export class OffeneMeldungenZahlComponent {
  readonly meldungen$ = inject(ZuTunService).meldungen$;
}
