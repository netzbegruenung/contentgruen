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
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  FangkorbZustand,
  KartenDaten,
  KartenVariante,
  RohlingAktion,
  RohlingDaten,
  RohlingSatz,
} from './karten-daten';
import { KartenAktionenComponent } from './karten-aktionen/karten-aktionen.component';
import { CONTENT_TYPE_REGISTRY, typLabel } from '../shared/content-type-registry';
import { KETTEN_ICONS } from '../shared/fangkorb-texte';
import { AuthService } from '../auth/auth.service';
import { kurzeKennung } from '../shared/kennung';
import { RelativeTimePipe } from '../shared/pipes/relative-time.pipe';

type TextModus = 'short' | 'standard' | 'long';

const NEU_STUNDEN = 24;
const BELIEBT_AB = 5;

/** So viele Saetze stehen in der Rohling-Karte; der Rest wird nur gezaehlt. */
const SAETZE_SICHTBAR = 3;

/**
 * Die Stufe, an der der Rohling gerade steht - dasselbe Icon wie ueberall entlang
 * der Kette. Das Band zeigt damit den Ist-Zustand: Ein Einwurf ohne Satz traegt
 * das Einwurf-Icon, ein destillierter das der Destille. Der Primaerknopf zeigt
 * dagegen die naechste Stufe (siehe primaerAktion). Verworfenes behaelt das Icon
 * des Einwurfs.
 */
const STUFEN: Record<FangkorbZustand, { emoji: string; name: string }> = {
  destillieren: { emoji: KETTEN_ICONS.einwerfen, name: 'Zu destillieren' },
  ausformulieren: { emoji: KETTEN_ICONS.destillieren, name: 'Auszuformulieren' },
  erledigt: { emoji: KETTEN_ICONS.verfassen, name: 'Erledigt' },
  verworfen: { emoji: KETTEN_ICONS.einwerfen, name: 'Verworfen' },
};

/**
 * Die eine Karte fuer Beitraege, in vier Varianten (siehe KartenVariante).
 *
 * Die Karte kennt keine Datenquelle, nur KartenDaten; die Adapter in karten-daten.ts
 * bringen Suche, Meine Beitraege und Fangkorb darauf. Abstimmen, Kopieren und Melden
 * stecken in app-karten-aktionen und erscheinen nur in der vollen Variante.
 *
 * Die volle Karte hat Knoepfe und ist deshalb selbst kein Tipp-Ziel. Kompakte Karten
 * sind als Ganzes antippbar und melden das ueber `angetippt`. Der Rohling traegt
 * statt eines Flaechentipps genau einen Primaerknopf und ein ⋮-Menue und meldet
 * beides ueber `aktion`; wohin es geht, entscheidet die Seite.
 *
 * Der Kopf ist nur das Band - Symbol und Titel, ohne Badges, Inhalt und Aktionen.
 * Das Beitragsformular zeigt damit die Aussage, auf die geantwortet wird, und
 * mit Rohling-Daten den Einwurf, aus dem der Beitrag entsteht (Sandband, Link,
 * der eine Satz - ohne Saetze-Liste, Aktionen, ⋮ und Meta).
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
    MatMenuModule,
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

  /** Tipp auf eine antippbare Karte (kompakt). */
  @Output() angetippt = new EventEmitter<KartenDaten>();
  /** Primaerknopf oder Menueeintrag auf einer Rohling-Karte. */
  @Output() aktion = new EventEmitter<RohlingAktion>();

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
    private authService: AuthService,
  ) {}

  /**
   * Die angemeldete Person - dieselbe Kennung, die als ``original_author`` am Beitrag
   * und als ``submitted_by`` am Einwurf steht. Die Karte holt sie sich selbst, statt
   * sie von jeder Seite durchgereicht zu bekommen: So steht "Du" in der Suche, im
   * Album-Sheet und im Fangkorb gleichermassen.
   */
  private get eigeneKennung(): string | null {
    return this.authService.getUserInfo()?.userId ?? null;
  }

  private get angemeldet(): boolean {
    return !!this.authService.getUserInfo()?.isAuthenticated;
  }

  /** Der eigene Beitrag oder Einwurf. Ohne Anmeldung nie. */
  get istEigen(): boolean {
    return !!this.daten.autor && this.daten.autor === this.eigeneKennung;
  }

  /**
   * Wer etwas eingestellt hat, sieht nur, wer angemeldet ist: Ohne Anmeldung steht in
   * der Meta-Zeile allein das Alter.
   */
  get zeigtAutor(): boolean {
    return this.angemeldet && (!!this.daten.autor || !!this.daten.autorName);
  }

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

  get istKopf(): boolean {
    return this.variante === 'kopf';
  }

  /** Die Rohling-Daten: in der Variante rohling und im Kopf, wenn er aus einem Einwurf kommt. */
  get rohling(): RohlingDaten | null {
    return this.variante === 'rohling' || this.variante === 'kopf' ? (this.daten.rohling ?? null) : null;
  }

  get kartenKlassen(): string[] {
    const klassen = [`karte--${this.variante}`, `typ-${this.daten.typ ?? 'ohne'}`];
    if (this.rohling) {
      klassen.push(`zustand-${this.rohling.zustand}`);
    }
    return klassen;
  }

  get typName(): string {
    return typLabel(this.daten.typ);
  }

  get emoji(): string {
    const typEmoji = this.daten.typ ? CONTENT_TYPE_REGISTRY[this.daten.typ]?.emoji : undefined;
    return typEmoji || '📝';
  }

  /**
   * Der eine Griff im Fuss, nach Zustand. Verworfenes bietet keinen an: Ansehen
   * gibt es ohne Beitrag nicht, und Weiterarbeiten steht im ⋮-Menue.
   *
   * Das Zeichen auf dem Knopf ist das der *naechsten* Stufe - es sagt, wohin der
   * Griff fuehrt, nicht wo der Rohling steht (das zeigt das Band). Ansehen fuehrt
   * auf keine Stufe der Kette weiter und traegt deshalb ein Material-Icon.
   */
  get primaerAktion(): { aktion: RohlingAktion; wort: string; emoji?: string; icon?: string } | null {
    switch (this.rohling?.zustand) {
      case 'destillieren':
        return { aktion: 'destillieren', wort: 'Destillieren', emoji: KETTEN_ICONS.destillieren };
      case 'ausformulieren':
        return { aktion: 'ausformulieren', wort: 'Ausformulieren', emoji: KETTEN_ICONS.verfassen };
      case 'erledigt':
        return { aktion: 'ansehen', wort: 'Ansehen', icon: 'visibility' };
      default:
        return null;
    }
  }

  /**
   * Das Zeichen im Kopfband. Erledigtes traegt das Emoji des entstandenen
   * Beitrags - dieselbe Marke, unter der er in Suche und Album steht; die
   * unfertigen Stufen tragen das Icon der Kette.
   */
  get stufenEmoji(): string {
    if (!this.rohling) {
      return '';
    }
    if (this.rohling.zustand === 'erledigt' && this.daten.typ) {
      return CONTENT_TYPE_REGISTRY[this.daten.typ]?.emoji || STUFEN.erledigt.emoji;
    }
    return STUFEN[this.rohling.zustand].emoji;
  }

  get stufenName(): string {
    if (!this.rohling) {
      return '';
    }
    if (this.rohling.zustand === 'erledigt' && this.daten.typ) {
      return typLabel(this.daten.typ);
    }
    return STUFEN[this.rohling.zustand].name;
  }

  /** Den Einwerfer nennt die Karte immer; beim eigenen Einwurf als "Du" (autorAnzeige). */
  get zeigtEinwerfer(): boolean {
    return !!this.daten.autor;
  }

  get sichtbareSaetze(): RohlingSatz[] {
    return (this.rohling?.saetze ?? []).slice(0, SAETZE_SICHTBAR);
  }

  get weitereSaetze(): number {
    return Math.max((this.rohling?.saetze.length ?? 0) - SAETZE_SICHTBAR, 0);
  }

  /** Rechts am Satz: ein Haken je Beitrag daraus, sonst das Wort "Entwurf". */
  satzStatus(satz: RohlingSatz): string {
    if (!satz.beitraege) {
      return 'Entwurf';
    }
    return satz.beitraege === 1 ? '✓' : `✓ ${satz.beitraege}`;
  }

  satzBeschriftung(satz: RohlingSatz): string {
    if (!satz.beitraege) {
      return 'Entwurf, noch kein Beitrag';
    }
    return satz.beitraege === 1 ? 'ein Beitrag daraus' : `${satz.beitraege} Beiträge daraus`;
  }

  /** Verwerfen darf nur, wer eingeworfen hat - und nur, solange kein Beitrag dranhaengt. */
  get darfVerwerfen(): boolean {
    return (
      !!this.rohling?.verwerfbar && this.istEigen
    );
  }

  /**
   * Das ⋮-Menue: alles, was nicht der eine Primaergriff ist.
   *
   * Erledigtes und Verworfenes laesst sich weiter destillieren - das Backend
   * erlaubt beides ausdruecklich, ein zweiter Beitrag aus demselben Einwurf ist
   * kein Fehler.
   */
  get menueEintraege(): { aktion: RohlingAktion; wort: string; icon: string }[] {
    const rohling = this.rohling;
    if (!rohling) {
      return [];
    }
    const eintraege: { aktion: RohlingAktion; wort: string; icon: string }[] = [];
    if (rohling.link) {
      eintraege.push({ aktion: 'linkKopieren', wort: 'Link kopieren', icon: 'link' });
    }
    if (rohling.zustand === 'erledigt') {
      eintraege.push({ aktion: 'weiterDestillieren', wort: 'Weiter destillieren', icon: 'science' });
    }
    if (rohling.zustand === 'verworfen') {
      eintraege.push({ aktion: 'weiterDestillieren', wort: 'Trotzdem destillieren', icon: 'science' });
    }
    if (this.darfVerwerfen) {
      eintraege.push({ aktion: 'verwerfen', wort: 'Verwerfen', icon: 'delete_outline' });
    }
    return eintraege;
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
    return this.istKompakt;
  }

  get beschriftung(): string {
    return `${this.typName}: ${this.titelAnzeige ?? ''}`;
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

  /** "Du" am eigenen Beitrag, sonst der Anzeigename und, solange es keinen gibt, die Kennung. */
  get autorAnzeige(): string {
    if (this.istEigen) {
      return 'Du';
    }
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

  /** Knoepfe im Rohling melden nur, was gewollt ist - wohin es fuehrt, weiss die Seite. */
  aktionAusloesen(aktion: RohlingAktion, event?: Event): void {
    event?.stopPropagation();
    this.aktion.emit(aktion);
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
