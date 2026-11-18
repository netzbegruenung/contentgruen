import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

import { KartenDaten, KartenKennzahlen } from '../beitragskarte/karten-daten';
import { FASSUNGEN, FASSUNG_LABEL } from '../shared/fassung';
import { PLATTFORM_GRENZE } from '../shared/beitrag-grenzen';
import { STIL_ERKLAERUNG, STIL_LABEL } from '../shared/zweck-stil';
import { SiegelErklaerung, siegelErklaerung } from '../shared/components/siegel/siegel-erklaerung';
import { GLANZ_TEXT, hatGlanz } from '../shared/components/siegel/siegel-auszeichnung';
import { RelativeTimePipe } from '../shared/pipes/relative-time.pipe';

/** Eine Zeile "Länge": je Fassung (Kurz, Mittel, Lang) oder ohne Fassungen der Text. */
export interface LaengenZeile {
  /** Name der Fassung; null, wenn es nur einen Text gibt. */
  fassung: string | null;
  zeichen: number;
  /** Bis 280 Zeichen: passt auf Mastodon/Bluesky/X (wie die Marke der vollen Karte). */
  passt: boolean;
}

/**
 * Die Laengen des Beitrags: am Kommentar mit Kurz- oder Langfassung je vorhandener Fassung,
 * sonst die des einen Texts; ohne Text keine.
 */
export function laengenZeilen(karte: KartenDaten): LaengenZeile[] {
  const zeile = (fassung: string | null, text: string): LaengenZeile => ({
    fassung,
    zeichen: text.length,
    passt: text.length <= PLATTFORM_GRENZE,
  });
  const kurz = karte.extra?.kurz ?? '';
  const lang = karte.extra?.lang ?? '';
  const mittel = karte.text ?? '';
  if (kurz || lang) {
    const texte = { kurz, mittel, lang };
    return FASSUNGEN.filter((f) => texte[f]).map((f) => zeile(FASSUNG_LABEL[f], texte[f]));
  }
  return mittel ? [zeile(null, mittel)] : [];
}

/**
 * Zu dieser Antwort (Maintainer 18.11.): am Desktop rechts neben der besten Antwort, was ihre
 * schlichte Karte nicht oder nur hinter einem Antippen zeigt: Laenge und Plattform je Fassung,
 * die Erklaerung des Stils und der Guete, das Alter. Nichts davon betrifft eine Person; Autor,
 * Abzeichen, Nutzung und Herkunft stehen schon auf der Karte und fehlen hier, ebenso die
 * Aussage (die Zeile "Erkannt als" nennt sie). Am Handy und unter 1024 px blendet die
 * Ergebnisseite den Kasten aus.
 */
@Component({
  selector: 'app-zu-dieser-antwort',
  standalone: true,
  imports: [CommonModule, RouterLink, MatIconModule, RelativeTimePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <aside class="zu-dieser-antwort" aria-labelledby="zu-dieser-antwort-titel">
      <h3 class="zda-titel" id="zu-dieser-antwort-titel">Zu dieser Antwort</h3>
      <dl class="zda-kasten">
        <div class="zda-eintrag zda-laenge" *ngIf="laengen.length">
          <dt>Länge</dt>
          <dd>
            <ul class="zda-zeilen">
              <li *ngFor="let z of laengen">
                <span>{{ z.fassung ? z.fassung + ': ' : '' }}{{ z.zeichen }} Zeichen</span>
                <span class="zda-passt" *ngIf="z.passt"
                  ><mat-icon class="zda-icon" aria-hidden="true">check</mat-icon>passt auf Mastodon/Bluesky/X</span
                >
              </li>
            </ul>
          </dd>
        </div>
        <div class="zda-eintrag zda-stil" *ngIf="stilErklaerung as stil">
          <dt>Stil</dt>
          <dd>{{ stil }}</dd>
        </div>
        <div class="zda-eintrag zda-guete" *ngIf="erklaerung as e">
          <dt>Güte</dt>
          <dd>
            <p class="zda-guete-kopf">{{ e.ueberschrift }}</p>
            <ul *ngIf="e.kriterien.length" class="zda-zeilen zda-kriterien">
              <li *ngFor="let kriterium of e.kriterien">
                <mat-icon class="zda-icon" aria-hidden="true">check</mat-icon>{{ kriterium }}
              </li>
            </ul>
            <p>{{ e.stimmen }} Wie oft sie genutzt wird, zählt nicht hinein.</p>
            <p *ngIf="glanz">{{ GLANZ_TEXT }}</p>
            <a class="zda-mehr" routerLink="/about" fragment="siegel">Mehr zur Güte</a>
          </dd>
        </div>
        <div class="zda-eintrag zda-alter" *ngIf="karte.erstellt">
          <dt>Eingestellt</dt>
          <dd>{{ karte.erstellt | relativeTime }} ({{ karte.erstellt | date: 'dd.MM.yyyy' }})</dd>
        </div>
      </dl>
    </aside>
  `,
  styles: [
    `
      :host {
        display: block;
      }

      /* Titel und Kasten als zwei Zeilen; steht der Kasten im Raster der Ergebnisseite (subgrid),
         teilen sie die Zeilen mit "Beste Antwort" und der Karte daneben */
      .zu-dieser-antwort {
        display: grid;
        grid-row: span 2;
        grid-template-rows: subgrid;
        align-content: start;
        align-items: start;
      }

      /* Wie "Beste Antwort" daneben: kleine Versalien, 24 px hoch, damit beide auf einer Linie stehen */
      .zda-titel {
        margin: 0 0 var(--spacing-xs);
        font-family: PTSans-bold, Roboto, sans-serif;
        font-weight: normal;
        font-size: 13px;
        line-height: 24px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        /* Dieselbe Farbe wie "Beste Antwort" (.beste-ueberschrift), damit beide gleichrangig wirken */
        color: var(--primary-dark);
      }

      .zda-kasten {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-md);
        margin: 0;
        padding: var(--spacing-md);
        border: 1px solid var(--line-light);
        border-radius: var(--border-radius-medium);
        background: var(--primary-tint-faint);
        color: var(--text-primary);
        font-size: 14px;
        line-height: 1.45;
      }

      dt {
        margin-bottom: 2px;
        font-family: PTSans-bold, Roboto, sans-serif;
        color: var(--text-secondary);
        font-size: 13px;
      }

      dd {
        margin: 0;
      }

      dd p {
        margin: 0 0 4px;
      }

      .zda-guete-kopf {
        font-family: PTSans-bold, Roboto, sans-serif;
      }

      .zda-zeilen {
        display: flex;
        flex-direction: column;
        gap: 2px;
        margin: 0 0 4px;
        padding: 0;
        list-style: none;
      }

      .zda-zeilen li {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        column-gap: var(--spacing-sm);
      }

      .zda-passt {
        display: inline-flex;
        align-items: center;
        color: var(--text-secondary);
      }

      .zda-icon {
        width: 16px;
        height: 16px;
        margin-right: 4px;
        font-size: 16px;
        color: var(--primary-dark);
      }

      .zda-mehr {
        display: inline-flex;
        align-items: center;
        min-height: 24px;
        color: var(--primary-dark);
        text-decoration: underline;
        text-underline-offset: 3px;
      }

      .zda-mehr:focus-visible {
        outline: 2px solid var(--akzent-klee);
        outline-offset: 2px;
      }
    `,
  ],
})
export class ZuDieserAntwortComponent {
  private _karte!: KartenDaten;
  /** Einmal je Karte berechnet: neue Zeilen bei jeder Pruefung baueten die Liste neu. */
  laengen: LaengenZeile[] = [];

  @Input({ required: true })
  set karte(karte: KartenDaten) {
    this._karte = karte;
    this.laengen = laengenZeilen(karte);
  }
  get karte(): KartenDaten {
    return this._karte;
  }

  /**
   * Was die Karte daneben nach Stimme oder Kopieren meldet; gilt nur fuer dieselbe Karte,
   * sonst zaehlen die Suchdaten. So stimmen Siegel und "Guete N von 10" ueberein.
   */
  @Input() kennzahlen: KartenKennzahlen | null = null;

  readonly GLANZ_TEXT = GLANZ_TEXT;

  private get aktuell(): KartenKennzahlen | null {
    return this.kennzahlen?.id === this.karte.id ? this.kennzahlen : null;
  }

  /** Wie am Stil-Etikett der Karte, etwa "sachlich: …"; nur am Kommentar mit Stil. */
  get stilErklaerung(): string | null {
    const stil = this.karte.extra?.stil;
    return stil ? `${STIL_LABEL[stil]}: ${STIL_ERKLAERUNG[stil]}` : null;
  }

  /** Dieselbe Erklaerung wie im Siegel-Menue der Karte; ohne Guete (alte Antwort) keine. */
  get erklaerung(): SiegelErklaerung | null {
    const aktuell = this.aktuell;
    const g = aktuell ? aktuell.guete : this.karte.guete;
    return g ? siegelErklaerung(g.wert, g.erfuellt, g.stimmenZaehlen) : null;
  }

  get glanz(): boolean {
    const aktuell = this.aktuell;
    return hatGlanz(aktuell ? aktuell.nutzung : this.karte.nutzung);
  }
}
