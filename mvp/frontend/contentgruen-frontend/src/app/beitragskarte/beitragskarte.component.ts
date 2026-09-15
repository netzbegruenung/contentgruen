import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { animate, style, transition, trigger } from '@angular/animations';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { KartenDaten, KartenVariante, RohlingDaten, RohlingRolle } from './karten-daten';
import { KartenAktionenComponent } from './karten-aktionen/karten-aktionen.component';
import { CONTENT_TYPE_REGISTRY, typLabel } from '../shared/content-type-registry';
import { KETTEN_ICONS } from '../shared/fangkorb-texte';
import { kurzeKennung } from '../shared/kennung';
import { RelativeTimePipe } from '../shared/pipes/relative-time.pipe';

type TextModus = 'short' | 'standard' | 'long';

const NEU_STUNDEN = 24;
const BELIEBT_AB = 5;

const ROLLEN: Record<RohlingRolle, string> = {
  eingeworfen: 'eingeworfen von',
  destilliert: 'destilliert von',
  ausformuliert: 'ausformuliert von',
};

/**
 * Die eine Karte fuer Beitraege, in drei Varianten (siehe KartenVariante).
 *
 * Die Karte kennt keine Datenquelle, nur KartenDaten; die Adapter in karten-daten.ts
 * bringen Suche, Meine Beitraege und Fangkorb darauf. Abstimmen, Kopieren und Melden
 * stecken in app-karten-aktionen und erscheinen nur in der vollen Variante.
 *
 * Die volle Karte hat Knoepfe und ist deshalb selbst kein Tipp-Ziel. Kompakte Karten
 * und nicht verworfene Rohlinge sind als Ganzes antippbar und melden das ueber
 * `angetippt`; wohin es geht, entscheidet die Seite. Links und Knoepfe darin halten
 * den Tipp mit stopPropagation von der Karte fern.
 *
 * Die Hoehe ergibt sich aus dem Inhalt. Langer Text wird gekuerzt und laesst sich mit
 * "mehr" aufklappen; ob gekuerzt wurde, misst die Karte am Element selbst.
 */
@Component({
  selector: 'app-beitragskarte',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatTooltipModule,
    RelativeTimePipe,
    KartenAktionenComponent,
  ],
  templateUrl: './beitragskarte.component.html',
  styleUrls: ['./beitragskarte.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [
    trigger('expandCollapse', [
      transition(':enter', [
        style({ height: '0', opacity: 0 }),
        animate('300ms cubic-bezier(0.4, 0, 0.2, 1)', style({ height: '*', opacity: 1 })),
      ]),
      transition(':leave', [
        animate('200ms cubic-bezier(0.4, 0, 0.2, 1)', style({ height: '0', opacity: 0 })),
      ]),
    ]),
  ],
})
export class BeitragskarteComponent implements OnChanges, OnDestroy {
  readonly kurzeKennung = kurzeKennung;

  @Input() variante: KartenVariante = 'voll';
  @Input({ required: true }) daten!: KartenDaten;
  /** Formular-Vorschau: Aktionen sichtbar, aber ohne Wirkung. */
  @Input() vorschau = false;
  /** Durchgereicht an app-karten-aktionen; aus beim eigenen Beitrag im Album-Sheet. */
  @Input() abstimmenSichtbar = true;

  /** Tipp auf eine antippbare Karte (kompakt, Rohling). */
  @Output() angetippt = new EventEmitter<KartenDaten>();
  /** "In der Suche anzeigen" auf einem ausformulierten Rohling, mit dem Satz. */
  @Output() inSuche = new EventEmitter<string>();

  nutzung: number | null = null;
  nutzungAnimiert = false;
  istNeu = false;
  istBeliebt = false;
  statementOffen = false;
  textModus: TextModus = 'standard';
  textAufgeklappt = false;
  textGekuerzt = false;

  private textElement?: HTMLElement;
  private beobachter?: ResizeObserver;

  constructor(
    private cdr: ChangeDetectorRef,
    private zone: NgZone,
  ) {}

  @ViewChild('textElement')
  set textElementRef(ref: ElementRef<HTMLElement> | undefined) {
    const element = ref?.nativeElement;
    if (element === this.textElement) {
      return;
    }
    this.beobachter?.disconnect();
    this.textElement = element;
    if (element && typeof ResizeObserver !== 'undefined') {
      this.beobachter = new ResizeObserver(() => this.zone.run(() => this.pruefeKuerzung()));
      this.beobachter.observe(element);
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['daten'] && this.daten) {
      this.nutzung = this.daten.nutzung;
      this.istNeu = this.stundenSeit(this.daten.erstellt) < NEU_STUNDEN;
      this.istBeliebt = (this.nutzung ?? 0) >= BELIEBT_AB;
      this.statementOffen = false;
      this.textModus = 'standard';
      this.textAufgeklappt = false;
    }
  }

  ngOnDestroy(): void {
    this.beobachter?.disconnect();
  }

  get istVoll(): boolean {
    return this.variante === 'voll';
  }

  get istKompakt(): boolean {
    return this.variante === 'kompakt';
  }

  /** Die Rohling-Daten, nur in der Variante rohling. */
  get rohling(): RohlingDaten | null {
    return this.variante === 'rohling' ? (this.daten.rohling ?? null) : null;
  }

  get istEinwurf(): boolean {
    return this.rohling?.art === 'einwurf';
  }

  get kartenKlassen(): string[] {
    const klassen = [`karte--${this.variante}`, `typ-${this.daten.typ ?? 'ohne'}`];
    if (this.rohling) {
      klassen.push(`art-${this.rohling.art}`, `zustand-${this.rohling.zustand}`);
    }
    return klassen;
  }

  get typName(): string {
    if (this.rohling) {
      if (this.istEinwurf) {
        return 'Einwurf';
      }
      return this.rohling.zustand === 'ausformuliert' && this.daten.typ ? typLabel(this.daten.typ) : 'Satz';
    }
    return typLabel(this.daten.typ);
  }

  get emoji(): string {
    const typEmoji = this.daten.typ ? CONTENT_TYPE_REGISTRY[this.daten.typ]?.emoji : undefined;
    if (this.rohling) {
      if (this.istEinwurf) {
        return KETTEN_ICONS.einwerfen;
      }
      return this.rohling.zustand === 'ausformuliert' ? typEmoji || KETTEN_ICONS.verfassen : KETTEN_ICONS.destillieren;
    }
    return typEmoji || '📝';
  }

  /** Kompakt steht ohne Titel (Altbestand) der Text im Titelfeld. */
  get titelAnzeige(): string | null {
    return this.istKompakt ? this.daten.titel || this.daten.text : this.daten.titel;
  }

  /** Bild im Kopfband, nur im Album; die volle Karte zeigt ihr Bild im Inhalt. */
  get kopfBild(): string | null {
    return this.istKompakt ? (this.daten.bildUrl ?? null) : null;
  }

  /** Text des Nutzungs-Badges fuer alle Varianten, "3×"; unbekannt zaehlt als 0. */
  get nutzungAnzeige(): string {
    return `${this.nutzung ?? 0}×`;
  }

  /** Anriss im Album: der Text unter dem Titel; ohne Titel steht er schon im Titelfeld. */
  get anriss(): string | null {
    return this.daten.titel ? this.daten.text : null;
  }

  get antippbar(): boolean {
    return this.istKompakt || !!this.rohling?.antippbar;
  }

  get beschriftung(): string {
    if (this.rohling) {
      const wer = this.istEinwurf ? 'Einwurf' : `Satz „${this.daten.titel ?? ''}“`;
      return this.rohling.antippbar ? `${wer}, ${this.rohling.zustand}: destillieren` : `${wer}, ${this.rohling.zustand}`;
    }
    return `${this.typName}: ${this.titelAnzeige ?? ''}`;
  }

  rolle(rolle: RohlingRolle): string {
    return ROLLEN[rolle];
  }

  get hatKurzOderLang(): boolean {
    return !!(this.daten.extra?.kurz || this.daten.extra?.lang);
  }

  /** Nur Kommentar und Hintergrundinfo tragen Herkunftsangaben. */
  get zeigtQuellen(): boolean {
    return this.daten.typ === 'commentary' || this.daten.typ === 'generictext';
  }

  get angezeigterText(): string {
    const text = this.daten.text ?? '';
    if (this.textModus === 'short') {
      return this.daten.extra?.kurz || text;
    }
    if (this.textModus === 'long') {
      return this.daten.extra?.lang || text;
    }
    return text;
  }

  get kopierText(): string {
    return this.angezeigterText;
  }

  get kopierBeschriftung(): string {
    return this.daten.typ === 'image' ? 'Bildunterschrift kopieren' : 'Kopieren';
  }

  get autorAnzeige(): string {
    return this.daten.autorName || kurzeKennung(this.daten.autor);
  }

  get postHerkunft(): string {
    return [this.daten.extra?.postAutor, this.daten.extra?.plattform].filter(Boolean).join(' · ');
  }

  /** Eine UUID ohne Adresse zeigt die Vorschau als "Herkunft n" statt als Kennung. */
  quellenName(id: string, index: number): string {
    return /^[0-9a-f-]{36}$/i.test(id) ? `Herkunft ${index + 1}` : id;
  }

  antippen(): void {
    if (this.antippbar) {
      this.angetippt.emit(this.daten);
    }
  }

  sucheOeffnen(event: Event): void {
    event.stopPropagation();
    if (this.rohling?.suchSatz) {
      this.inSuche.emit(this.rohling.suchSatz);
    }
  }

  statementUmschalten(): void {
    this.statementOffen = !this.statementOffen;
    this.cdr.markForCheck();
  }

  textModusSetzen(modus: TextModus): void {
    this.textModus = modus;
    this.textAufgeklappt = false;
    this.cdr.markForCheck();
    requestAnimationFrame(() => this.zone.run(() => this.pruefeKuerzung()));
  }

  textUmschalten(): void {
    this.textAufgeklappt = !this.textAufgeklappt;
    this.cdr.markForCheck();
  }

  nutzungHochzaehlen(): void {
    if (this.nutzung === null) {
      return;
    }
    this.nutzung++;
    this.nutzungAnimiert = true;
    setTimeout(() => {
      this.nutzungAnimiert = false;
      this.cdr.markForCheck();
    }, 300);
    this.cdr.markForCheck();
  }

  /** Misst, ob der gekuerzte Text abgeschnitten ist. Aufgeklappt bleibt der Knopf stehen. */
  pruefeKuerzung(): void {
    if (!this.textElement || this.textAufgeklappt) {
      return;
    }
    const gekuerzt = this.textElement.scrollHeight > this.textElement.clientHeight + 1;
    if (gekuerzt !== this.textGekuerzt) {
      this.textGekuerzt = gekuerzt;
      this.cdr.markForCheck();
    }
  }

  private stundenSeit(zeitpunkt: string): number {
    const millis = new Date(zeitpunkt).getTime();
    return Number.isNaN(millis) ? Infinity : (Date.now() - millis) / (1000 * 60 * 60);
  }
}
