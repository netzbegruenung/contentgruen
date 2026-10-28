import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DestroyRef,
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
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { animate, style, transition, trigger } from '@angular/animations';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  KartenDaten,
  KartenVariante,
  EinwurfAktion,
  EinwurfAngaben,
  EinwurfSatz,
  STUFEN,
} from './karten-daten';
import { KartenAktionenComponent } from './karten-aktionen/karten-aktionen.component';
import { herkunftText, tragtHerkunftsangaben } from './herkunft-text';
import { CONTENT_TYPE_REGISTRY, typLabel } from '../shared/content-type-registry';
import { KETTEN_ICONS } from '../shared/fangkorb-texte';
import { AuthService } from '../auth/auth.service';
import { RelativeTimePipe } from '../shared/pipes/relative-time.pipe';

type TextModus = 'short' | 'standard' | 'long';

const NEU_STUNDEN = 24;
const BELIEBT_AB = 5;

/** So viele Saetze stehen in der Einwurf-Karte; der Rest wird nur gezaehlt. */
const SAETZE_SICHTBAR = 3;

/**
 * Die eine Karte fuer Beitraege, in vier Varianten (siehe KartenVariante).
 *
 * Die Karte kennt keine Datenquelle, nur KartenDaten; die Adapter in karten-daten.ts
 * bringen Suche, Meine Beitraege und Fangkorb darauf. Abstimmen, Kopieren und Melden
 * stecken in app-karten-aktionen und erscheinen nur in der vollen Variante.
 *
 * Die volle Karte hat Knoepfe und ist deshalb selbst kein Tipp-Ziel. Kompakte Karten
 * sind als Ganzes antippbar und melden das ueber `angetippt`. Die Einwurf-Karte traegt
 * statt eines Flaechentipps genau einen Primaerknopf und ein ⋮-Menue und meldet
 * beides ueber `aktion`; wohin es geht, entscheidet die Seite.
 *
 * Der Kopf ist nur das Band - Symbol und Titel, ohne Badges, Inhalt und Aktionen.
 * Das Beitragsformular zeigt damit die Aussage, auf die geantwortet wird, und
 * mit Einwurf-Daten den Einwurf, aus dem der Beitrag entsteht (Sandband, Link,
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
  @Input() variante: KartenVariante = 'voll';
  @Input({ required: true }) daten!: KartenDaten;
  /** Formular-Vorschau: Aktionen sichtbar, aber ohne Wirkung. */
  @Input() vorschau = false;
  /** Durchgereicht an app-karten-aktionen; aus beim eigenen Beitrag im Album-Sheet. */
  @Input() abstimmenSichtbar = true;
  /**
   * Einwurf-Karte: die Stufe als Wort in der Meta-Zeile statt des Einwerfers. Fuer
   * "Meine Einwuerfe", wo alle Karten die eigenen sind und die Stufe die Rueckmeldung ist.
   */
  @Input() stufeZeigen = false;

  /** Tipp auf eine antippbare Karte (kompakt). */
  @Output() angetippt = new EventEmitter<KartenDaten>();
  /** Primaerknopf oder Menueeintrag auf einer Einwurf-Karte. */
  @Output() aktion = new EventEmitter<EinwurfAktion>();

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
    destroyRef: DestroyRef,
  ) {
    // Die Karte steht oft schon, bevor /api/user-info beantwortet ist. Ohne dieses
    // Abonnement blieben die Getter bei dem, was beim ersten Zeichnen galt: kein
    // "Von: Du" am eigenen Beitrag, kein Verwerfen am eigenen Einwurf - und die
    // eigene Kopie zaehlte optimistisch hoch, waehrend das Backend sie verwirft.
    // OnPush zeichnet von sich aus nicht neu, wenn sich nur der Dienst aendert.
    this.authService.userInfo$
      .pipe(takeUntilDestroyed(destroyRef))
      .subscribe(() => this.cdr.markForCheck());
  }

  private get istAdmin(): boolean {
    return !!this.authService.getUserInfo()?.isAdmin;
  }

  private get angemeldet(): boolean {
    return !!this.authService.getUserInfo()?.isAuthenticated;
  }

  /**
   * Der eigene Beitrag oder Einwurf. Ohne Anmeldung nie. Ob es der eigene ist, sagt
   * allein das Kennzeichen vom Server (#333, #385); fehlt es, ist es nicht der eigene.
   */
  get istEigen(): boolean {
    return this.angemeldet && this.daten.eigen === true;
  }

  /**
   * Wer etwas eingestellt hat, sieht nur, wer angemeldet ist: Ohne Anmeldung steht in
   * der Meta-Zeile allein das Alter.
   */
  get zeigtAutor(): boolean {
    return this.angemeldet && (!!this.daten.autor || !!this.daten.autorName || this.daten.eigen != null);
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

  /** Die Einwurf-Daten: in der Variante einwurf und im Kopf, wenn er aus einem Einwurf kommt. */
  get einwurfAngaben(): EinwurfAngaben | null {
    return this.variante === 'einwurf' || this.variante === 'kopf' ? (this.daten.einwurfAngaben ?? null) : null;
  }

  get kartenKlassen(): string[] {
    const klassen = [`karte--${this.variante}`, `typ-${this.daten.typ ?? 'ohne'}`];
    if (this.einwurfAngaben) {
      klassen.push(`stufe-${this.einwurfAngaben.stufe}`);
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
   * Der eine Griff im Fuss, nach Stufe. Verworfenes bietet keinen an: Ansehen
   * gibt es ohne Beitrag nicht, und Weiterarbeiten steht im ⋮-Menue.
   *
   * Das Zeichen auf dem Knopf ist das der *naechsten* Stufe - es sagt, wohin der
   * Griff fuehrt, nicht wo der Einwurf steht (das zeigt das Band). Ansehen fuehrt
   * auf keine Stufe der Kette weiter und traegt deshalb ein Material-Icon.
   */
  get primaerAktion(): { aktion: EinwurfAktion; wort: string; emoji?: string; icon?: string } | null {
    switch (this.einwurfAngaben?.stufe) {
      case 'offen':
        return { aktion: 'destillieren', wort: 'Destillieren', emoji: KETTEN_ICONS.destillieren };
      case 'destilliert':
        return { aktion: 'ausformulieren', wort: 'Ausformulieren', emoji: KETTEN_ICONS.verfassen };
      case 'ausformuliert':
        return { aktion: 'ansehen', wort: 'Ansehen', icon: 'visibility' };
      default:
        return null;
    }
  }

  /**
   * Das Zeichen im Kopfband. Ausformuliertes traegt das Emoji des verknuepften
   * Beitrags - dieselbe Marke, unter der er in Suche und Album steht; die
   * unfertigen Stufen tragen das Icon der Kette.
   */
  get stufenEmoji(): string {
    if (!this.einwurfAngaben) {
      return '';
    }
    if (this.einwurfAngaben.stufe === 'ausformuliert' && this.daten.typ) {
      return CONTENT_TYPE_REGISTRY[this.daten.typ]?.emoji || STUFEN.ausformuliert.emoji;
    }
    return STUFEN[this.einwurfAngaben.stufe].emoji;
  }

  get stufenName(): string {
    if (!this.einwurfAngaben) {
      return '';
    }
    if (this.einwurfAngaben.stufe === 'ausformuliert' && this.daten.typ) {
      return `${STUFEN.ausformuliert.name}: ${typLabel(this.daten.typ)}`;
    }
    return STUFEN[this.einwurfAngaben.stufe].name;
  }

  /**
   * Den Einwerfer nennt die Karte, beim eigenen als "Du" (autorAnzeige) - ausser sie
   * zeigt die Stufe. Nur bei bekanntem Einwerfer: Das Kennzeichen fehlt, wenn niemand
   * Bekanntes einwarf (#385).
   */
  get zeigtEinwerfer(): boolean {
    return (!!this.daten.autor || this.daten.eigen != null) && !this.stufeZeigen;
  }

  get sichtbareSaetze(): EinwurfSatz[] {
    return (this.einwurfAngaben?.saetze ?? []).slice(0, SAETZE_SICHTBAR);
  }

  get weitereSaetze(): number {
    return Math.max((this.einwurfAngaben?.saetze.length ?? 0) - SAETZE_SICHTBAR, 0);
  }

  /** Rechts am Satz: ein Haken je verknuepftem Beitrag, sonst nichts. */
  satzStatus(satz: EinwurfSatz): string {
    if (!satz.beitraege) {
      return '';
    }
    return satz.beitraege === 1 ? '✓' : `✓ ${satz.beitraege}`;
  }

  satzBeschriftung(satz: EinwurfSatz): string {
    if (!satz.beitraege) {
      return 'noch kein Beitrag';
    }
    return satz.beitraege === 1 ? 'mit einem Beitrag verknüpft' : `mit ${satz.beitraege} Beiträgen verknüpft`;
  }

  /**
   * Verwerfen duerfen der Einwerfer und Admins - und nur, solange kein Beitrag
   * dranhaengt. Admins nehmen so Einwuerfe aus dem Fangkorb, um die sich kein
   * Einwerfer mehr kuemmert (toter Link, inaktive Person, kein Einwerfer).
   */
  get darfVerwerfen(): boolean {
    return !!this.einwurfAngaben?.verwerfbar && (this.istEigen || this.istAdmin);
  }

  /**
   * Das ⋮-Menue: alles, was nicht der eine Primaergriff ist.
   *
   * Ausformuliertes und Verworfenes laesst sich weiter destillieren - das Backend
   * erlaubt beides ausdruecklich, ein zweiter Beitrag aus demselben Einwurf ist
   * kein Fehler.
   */
  get menueEintraege(): { aktion: EinwurfAktion; wort: string; icon: string }[] {
    const angaben = this.einwurfAngaben;
    if (!angaben) {
      return [];
    }
    const eintraege: { aktion: EinwurfAktion; wort: string; icon: string }[] = [];
    if (angaben.link) {
      eintraege.push({ aktion: 'linkKopieren', wort: 'Link kopieren', icon: 'link' });
    }
    if (angaben.stufe === 'ausformuliert') {
      eintraege.push({ aktion: 'weiterDestillieren', wort: 'Weiter destillieren', icon: 'science' });
    }
    if (angaben.stufe === 'verworfen') {
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

  get zeigtQuellen(): boolean {
    return tragtHerkunftsangaben(this.daten.typ);
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

  /** Die angezeigte Fassung samt Herkunft; leer ohne Herkunft, dann bietet die Leiste keine Wahl an. */
  get kopierTextMitHerkunft(): string {
    const herkunft = herkunftText(this.daten);
    return herkunft && this.kopierText ? `${this.kopierText}\n\n${herkunft}` : '';
  }

  get kopierBeschriftung(): string {
    return this.daten.typ === 'image' ? 'Bildunterschrift kopieren' : 'Kopieren';
  }

  /**
   * "Du" am eigenen Beitrag, sonst der Anzeigename ("Anna B."). Ohne Namen steht
   * "Mitglied" da - nie die Kennung: die ist kein Name und gehoert nicht auf die Karte.
   */
  get autorAnzeige(): string {
    if (this.istEigen) {
      return 'Du';
    }
    return this.daten.autorName || 'Mitglied';
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

  /** Knoepfe auf der Einwurf-Karte melden nur, was gewollt ist - wohin es fuehrt, weiss die Seite. */
  aktionAusloesen(aktion: EinwurfAktion, event?: Event): void {
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

  /**
   * Nach dem Kopieren eine Nutzung mehr - ausser am eigenen Beitrag: Den zaehlt
   * auch das Backend nicht (api/v1/usage.py), und die Karte soll nicht kurz etwas
   * anderes behaupten als der naechste Seitenaufruf zeigt.
   */
  nutzungHochzaehlen(): void {
    if (this.nutzung === null || this.istEigen) {
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
