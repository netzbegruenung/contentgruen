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
import { HOECHSTE_GUETE, normierteGuete } from '../shared/components/siegel/siegel-zeichnung';
import { SiegelComponent } from '../shared/components/siegel/siegel.component';
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
  imports: [CommonModule, RouterLink, MatIconModule, SiegelComponent, RelativeTimePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <aside class="zu-dieser-antwort" aria-labelledby="zu-dieser-antwort-titel">
      <h3 class="zda-titel" id="zu-dieser-antwort-titel">Zu dieser Antwort</h3>
      <!-- Je Angabe eine Kachel mit Material-Icon vorn wie die Angaben der Karte daneben
           (Maintainer 18.11.: weniger Text); die Icons liest der Screenreader nicht vor -->
      <dl class="zda-kasten">
        <div class="zda-eintrag zda-laenge" *ngIf="laengen.length">
          <dt><mat-icon class="zda-symbol" aria-hidden="true">straighten</mat-icon>Länge</dt>
          <dd>
            <div class="zda-fassung" *ngFor="let z of laengen">
              <p class="zda-zeichen">{{ z.fassung ? z.fassung + ' · ' : '' }}{{ z.zeichen }} Zeichen</p>
              <ul class="zda-chips" [attr.aria-label]="z.passt ? 'passt auf' : 'zu lang für'">
                <li *ngFor="let p of PLATTFORMEN" class="zda-chip" [class.zda-chip--aus]="!z.passt">
                  {{ p
                  }}<mat-icon class="zda-chip-icon" aria-hidden="true">{{ z.passt ? 'check' : 'block' }}</mat-icon>
                </li>
              </ul>
            </div>
          </dd>
        </div>
        <div class="zda-eintrag zda-stil" *ngIf="stil as s">
          <dt><mat-icon class="zda-symbol" aria-hidden="true">track_changes</mat-icon>Stil</dt>
          <dd>
            <span class="zda-stil-chip">{{ s.label }}</span>
            <p class="zda-klein">{{ s.erklaerung }}</p>
          </dd>
        </div>
        <div class="zda-eintrag zda-guete" *ngIf="erklaerung as e">
          <dt><app-siegel class="zda-siegel" aria-hidden="true" [guete]="note" [glanz]="glanz"></app-siegel>Güte</dt>
          <dd>
            <p class="zda-guete-kopf">
              <ng-container *ngIf="note !== null; else ohneNote">
                <span class="zda-gross" aria-hidden="true">{{ note }}<span class="zda-von">/{{ HOECHSTE_GUETE }}</span></span>
                <span class="cdk-visually-hidden">{{ e.ueberschrift }}</span>
              </ng-container>
              <ng-template #ohneNote>{{ e.ueberschrift }}</ng-template>
            </p>
            <ul *ngIf="e.kriterien.length" class="zda-kriterien">
              <li *ngFor="let kriterium of e.kriterien">
                <mat-icon class="zda-haken" aria-hidden="true">check</mat-icon>{{ kriterium }}
              </li>
            </ul>
            <p class="zda-klein">{{ e.stimmen }}</p>
            <p class="zda-klein" *ngIf="glanz">{{ GLANZ_TEXT }}</p>
            <a class="zda-mehr zda-klein" routerLink="/about" fragment="siegel">Mehr zur Güte</a>
          </dd>
        </div>
        <div class="zda-eintrag zda-alter" *ngIf="karte.erstellt">
          <dt><mat-icon class="zda-symbol" aria-hidden="true">schedule</mat-icon>Eingestellt</dt>
          <!-- Nach fuenf Tagen nennt relativeTime selbst das Datum: dann nicht doppelt -->
          <dd *ngIf="{ relativ: karte.erstellt | relativeTime, datum: karte.erstellt | date: 'dd.MM.yyyy' } as alter">
            <p class="zda-gross-text">{{ alter.relativ }}</p>
            <p class="zda-klein" *ngIf="alter.relativ !== alter.datum">{{ alter.datum }}</p>
          </dd>
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
        color: var(--akzent-schrift);
      }

      /* Kacheln untereinander, durch feine Linien getrennt */
      .zda-kasten {
        display: flex;
        flex-direction: column;
        margin: 0;
        padding: 0 var(--spacing-md);
        border: 1px solid var(--linie);
        border-radius: var(--border-radius-medium);
        background: var(--primary-tint-faint);
        color: var(--text);
        font-size: 14px;
        line-height: 1.45;
      }

      .zda-eintrag {
        padding: var(--spacing-sm) 0;
      }

      .zda-eintrag + .zda-eintrag {
        border-top: 1px solid var(--linie);
      }

      dt {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 4px;
        font-family: PTSans-bold, Roboto, sans-serif;
        color: var(--text-leise);
        font-size: 12px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }

      .zda-symbol {
        width: 20px;
        height: 20px;
        font-size: 20px;
        color: var(--akzent-schrift);
      }

      .zda-siegel {
        display: block;
        width: 20px;
      }

      /* Inhalt eingerückt unter die Bezeichnung, bündig nach dem Symbol */
      dd {
        margin: 0 0 0 26px;
      }

      dd p {
        margin: 0;
      }

      .zda-klein {
        color: var(--text-leise);
        font-size: 13px;
      }

      .zda-fassung + .zda-fassung {
        margin-top: 6px;
      }

      .zda-zeichen {
        color: var(--text-leise);
        font-size: 13px;
      }

      .zda-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin: 2px 0 0;
        padding: 0;
        list-style: none;
      }

      .zda-chip,
      .zda-stil-chip {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        padding: 1px 8px;
        border: 1px solid var(--linie);
        border-radius: var(--border-radius-large);
        background: var(--primaer-tint);
        color: var(--akzent-schrift);
        font-size: 13px;
        line-height: 1.5;
      }

      /* Passt nicht: ausgegraut, gestrichelt; Grau wie Nebentext, damit es AA hält */
      .zda-chip--aus {
        border-style: dashed;
        background: none;
        color: var(--text-leise);
      }

      .zda-chip-icon {
        width: 14px;
        height: 14px;
        font-size: 14px;
      }

      .zda-stil-chip {
        margin-bottom: 4px;
      }

      .zda-guete-kopf {
        font-family: PTSans-bold, Roboto, sans-serif;
      }

      .zda-gross {
        font-size: 28px;
        line-height: 1.1;
        color: var(--akzent-schrift);
      }

      .zda-von {
        font-size: 16px;
        color: var(--text-leise);
      }

      .zda-gross-text {
        font-family: PTSans-bold, Roboto, sans-serif;
        font-size: 18px;
        line-height: 1.3;
      }

      /* Erfüllte Kriterien als kompakte Häkchen-Liste, zweispaltig */
      .zda-kriterien {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 2px var(--spacing-sm);
        margin: 4px 0;
        padding: 0;
        list-style: none;
        font-size: 13px;
        line-height: 1.3;
      }

      .zda-kriterien li {
        display: flex;
        align-items: flex-start;
        gap: 2px;
      }

      .zda-haken {
        flex: none;
        width: 16px;
        height: 16px;
        font-size: 16px;
        color: var(--akzent-schrift);
      }

      .zda-mehr {
        display: inline-flex;
        align-items: center;
        min-height: 24px;
        color: var(--akzent-schrift);
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
  readonly HOECHSTE_GUETE = HOECHSTE_GUETE;
  /** Plattformen mit derselben Grenze (PLATTFORM_GRENZE), wie die Marke der vollen Karte. */
  readonly PLATTFORMEN = ['Mastodon', 'Bluesky', 'X'];

  private get aktuell(): KartenKennzahlen | null {
    return this.kennzahlen?.id === this.karte.id ? this.kennzahlen : null;
  }

  private get guete() {
    const aktuell = this.aktuell;
    return aktuell ? aktuell.guete : this.karte.guete;
  }

  /** Wie das Stil-Etikett der Karte, dazu die Erklaerung; nur am Kommentar mit Stil. */
  get stil(): { label: string; erklaerung: string } | null {
    const stil = this.karte.extra?.stil;
    return stil ? { label: STIL_LABEL[stil], erklaerung: STIL_ERKLAERUNG[stil] } : null;
  }

  /** Dieselbe Erklaerung wie im Siegel-Menue der Karte; ohne Guete (alte Antwort) keine. */
  get erklaerung(): SiegelErklaerung | null {
    const g = this.guete;
    return g ? siegelErklaerung(g.wert, g.erfuellt, g.stimmenZaehlen) : null;
  }

  /** Die Guete als Zahl 1–10 fuer die grosse Anzeige und das Siegel; neu (ohne Daten) null. */
  get note(): number | null {
    return normierteGuete(this.guete?.wert);
  }

  get glanz(): boolean {
    const aktuell = this.aktuell;
    return hatGlanz(aktuell ? aktuell.nutzung : this.karte.nutzung);
  }
}
