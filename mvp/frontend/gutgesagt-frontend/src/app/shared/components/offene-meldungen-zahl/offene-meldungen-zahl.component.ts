import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';

import { combineLatest } from 'rxjs';
import { map, startWith } from 'rxjs/operators';

import { OffeneMeldungen, Stand, WartendeSuchanfragen, ZuTunService, suchanfragenText } from '../../../services/zu-tun.service';

/** Was am Admin-Link steht: Meldungen und wartende Suchanfragen zusammen. */
export interface KopfZahl {
  /** Offene Meldungen plus wartende Suchanfragen. */
  anzahl: number;
  /** Die Meldungen haben die Grenze erreicht: Es können mehr sein. */
  mehr: boolean;
  /** Für Screenreader, etwa „2 offene Meldungen, 1 Suchanfrage wartet auf Freigabe“. */
  ansage: string;
}

/** Die Zahl am Admin-Link aus beiden Ständen; null, solange nichts zu tun oder nichts geladen ist. */
export function kopfZahl(meldungen: Stand<OffeneMeldungen>, suchanfragen: Stand<WartendeSuchanfragen>): KopfZahl | null {
  const m = meldungen.daten;
  const s = suchanfragen.daten?.anzahl ?? 0;
  const teile: string[] = [];
  if (m && m.anzahl > 0) {
    teile.push(m.anzahl === 1 ? '1 offene Meldung' : m.anzahl + (m.mehr ? ' oder mehr' : '') + ' offene Meldungen');
  }
  if (s > 0) {
    teile.push(suchanfragenText(s));
  }
  const anzahl = (m?.anzahl ?? 0) + s;
  return anzahl > 0 ? { anzahl, mehr: !!m?.mehr, ansage: teile.join(', ') } : null;
}

/**
 * Die Zahl am Admin-Link im Kopf und im Menue: offene Meldungen plus Suchanfragen, die
 * auf Freigabe warten (#664). Sie laedt selbst nach (ZuTunService); ist nichts zu tun,
 * steht nichts da.
 *
 * Steht nur im Link fuer Admins, deshalb fragen andere nie. Die Ziffer ist fuer
 * Screenreader stumm, sie lesen „2 offene Meldungen, 1 Suchanfrage wartet auf Freigabe“
 * als Teil des Links.
 */
@Component({
  selector: 'app-offene-meldungen-zahl',
  standalone: true,
  imports: [AsyncPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (zahl$ | async; as offen) {
      <span class="zahl" aria-hidden="true">{{ offen.mehr ? offen.anzahl + '+' : offen.anzahl }}</span>
      <span class="visually-hidden">, {{ offen.ansage }}</span>
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
  private readonly zuTun = inject(ZuTunService);
  private readonly leer = { daten: null, fehler: false };

  readonly zahl$ = combineLatest([
    this.zuTun.meldungen$.pipe(startWith<Stand<OffeneMeldungen>>(this.leer)),
    this.zuTun.suchanfragen$.pipe(startWith<Stand<WartendeSuchanfragen>>(this.leer)),
  ]).pipe(map(([meldungen, suchanfragen]) => kopfZahl(meldungen, suchanfragen)));
}
