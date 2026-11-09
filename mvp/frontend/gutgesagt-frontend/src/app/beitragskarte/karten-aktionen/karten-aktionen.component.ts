import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime } from 'rxjs/operators';

import { AuthService } from '../../auth/auth.service';
import { LoggingService } from '../../services/logging.service';
import { UsageTrackingService } from '../../services/usage-tracking.service';
import { VotingService } from '../../services/voting.service';
import { meldeDialogOeffnen } from '../../shared/components/report-dialog/report-dialog.component';
import { HAND_UMRISS } from '../../shared/marke/hand';
import { ROUTES } from '../../shared/constants/app.constants';
import type { Fassung } from '../../shared/fassung';
import { kannVorlageSein, vorlageAdresse } from '../../beitragsformular/vorlage';
import { einwilligungFehlt } from '../../services/art9-einwilligung.service';

/**
 * Die Aktionsleiste der vollen Beitragskarte: abstimmen, kopieren, melden, im
 * Menue der Weg zur eigenen Adresse des Beitrags (/beitrag/:id, #300) und,
 * angemeldet, als Vorlage nehmen (#356).
 * Hat der Beitrag eine Herkunft, steht die zweite Kopier-Variante (mit oder ohne
 * Herkunft) im Menue; welche der Knopf kopiert, entscheidet die Karte (#641).
 *
 * Abstimmen ist optimistisch mit Entprellung und Ruecknahme, dazu 401/403/429-Behandlung
 * (urspruenglich aus BaseResultItemComponent). Die Leiste sitzt in einer eigenen
 * Komponente, damit kompakte Karten und Einwurf-Karten, die als Ganzes antippbar sind,
 * keine Knoepfe und keine Dienste mitschleppen.
 *
 * In der Formular-Vorschau ist die Leiste sichtbar wie in der Suche, reagiert aber
 * nicht: kein Zeiger, kein Fokus, aria-disabled. Ausgegraut wird sie bewusst nicht,
 * die Vorschau soll zeigen, wie der Beitrag aussehen wird.
 */
type Stimme = 'like' | 'dislike' | null;

/** Eine zweite Art zu kopieren, als Eintrag im ⋮-Menue (#641). */
export interface KopierVariante {
  text: string;
  wort: string;
}

@Component({
  selector: 'app-karten-aktionen',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule],
  templateUrl: './karten-aktionen.component.html',
  styleUrls: ['./karten-aktionen.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[class.ist-vorschau]': 'vorschau' },
})
export class KartenAktionenComponent implements OnInit, OnChanges, OnDestroy {
  @Input({ required: true }) inhaltId!: string;
  /** Registry-Schluessel, geht an den Melde-Dialog. */
  @Input() typ: string | null = null;
  @Input() kopierText = '';
  @Input() kopierBeschriftung = 'Kopieren';
  /** Was der Knopf kopiert, als Tooltip (MatTooltip haengt ihn als Beschreibung an); leer = keiner. */
  @Input() kopierHinweis = '';
  /** Die andere Variante (mit oder ohne Herkunft) im Menue; null = es gibt nur eine. */
  @Input() zweiteKopie: KopierVariante | null = null;
  @Input() stimme?: 'like' | 'dislike';
  @Input() vorschau = false;
  /** Aus beim eigenen Beitrag (Album-Sheet in Meine Beitraege); Kopieren und Melden bleiben. */
  @Input() abstimmenSichtbar = true;
  /** Die angezeigte Fassung eines Kommentars, gezaehlt wird je Fassung (#355); sonst null. */
  @Input() fassung: Fassung | null = null;
  /** Der Menueeintrag "Beitrag öffnen"; aus auf der eigenen Adresse selbst. */
  @Input() ansichtVerlinkt = true;
  /**
   * Zaehler an den Stimm-Knoepfen (#427), wie der Server sie zuletzt gemeldet hat;
   * null = unter der Mindestzahl (der Server schickt dann keine, DSFA M5) oder
   * unbekannt, dann ohne Zahl. Die eigene Stimme rechnet die Leiste sofort ein.
   */
  @Input() hilfreich: number | null = null;
  @Input() nichtHilfreich: number | null = null;
  /** Aus am eigenen Beitrag: Die Zaehler zeigen nur Stimmen anderer (#427). */
  @Input() eigeneStimmeImZaehler = true;

  @Output() likeToggled = new EventEmitter<string>();
  @Output() dislikeToggled = new EventEmitter<string>();
  /** Nach erfolgreichem Kopieren; die Karte zaehlt daraufhin ihre Nutzung hoch. */
  @Output() kopiert = new EventEmitter<void>();

  isLiked = false;
  isDisliked = false;
  isVoting = false;
  copyAnimationActive = false;
  readonly HAND_UMRISS = HAND_UMRISS;

  /**
   * Die Stimme, wie sie vor dem ersten Tippen seit dem letzten Abgleich stand;
   * undefined, solange nichts aussteht. Gegen sie wird nach der Entprellung
   * abgeglichen: gesendet wird, was noetig ist, um vom Ausgangs- zum Zielzustand
   * zu kommen.
   *
   * Frueher trugen zwei Subjects je Knopf "war vorher an" durch
   * distinctUntilChanged. Like -> Dislike -> Like schickte dort zweimal false auf
   * den Like-Strom, das zweite fiel weg - die Karte zeigte Like, gespeichert war
   * Dislike.
   */
  private ausgang: Stimme | undefined;
  /** Die eigene Stimme, die in den zuletzt gemeldeten Zaehlern schon steckt. */
  private stimmeImZaehler: Stimme = null;
  private abgleich = new Subject<void>();
  private abonniert = false;

  constructor(
    private clipboard: Clipboard,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
    private usageTrackingService: UsageTrackingService,
    private votingService: VotingService,
    private authService: AuthService,
    private logger: LoggingService,
    private dialog: MatDialog,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.initializeVoteState();

    if (this.abonniert) {
      return;
    }
    this.abonniert = true;
    this.abgleich.pipe(debounceTime(50)).subscribe(() => this.abgleichen());
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['stimme'] || changes['inhaltId']) {
      this.initializeVoteState();
      this.stimmeImZaehler = this.stimme ?? null;
    } else if (changes['hilfreich'] || changes['nichtHilfreich']) {
      // Frisch geladen nach einer abgeglichenen Stimme: Die angezeigte steckt jetzt drin.
      this.stimmeImZaehler = this.angezeigt;
    }
  }

  get zahlHilfreich(): number | null {
    return this.zahl(this.hilfreich, 'like');
  }

  get zahlNichtHilfreich(): number | null {
    return this.zahl(this.nichtHilfreich, 'dislike');
  }

  /** Der unsichtbare Name eines Stimm-Knopfs, mit Zaehler, sofern bekannt. */
  beschriftung(name: string, zahl: number | null): string {
    if (zahl === null) {
      return name;
    }
    return `${name}, ${zahl} ${zahl === 1 ? 'Stimme' : 'Stimmen'}`;
  }

  private zahl(gemeldet: number | null, richtung: 'like' | 'dislike'): number | null {
    if (gemeldet === null || !this.eigeneStimmeImZaehler) {
      return gemeldet;
    }
    const jetzt = this.angezeigt === richtung ? 1 : 0;
    const drin = this.stimmeImZaehler === richtung ? 1 : 0;
    return Math.max(0, gemeldet + jetzt - drin);
  }

  ngOnDestroy(): void {
    this.abgleich.complete();
  }

  toggleLike(): void {
    this.umschalten(this.isLiked ? null : 'like');
  }

  toggleDislike(): void {
    this.umschalten(this.isDisliked ? null : 'dislike');
  }

  /** Was die Karte als Standard vorgibt. */
  kopieren(): void {
    this.inZwischenablage(this.kopierText);
  }

  /** Die zweite Variante aus dem Menue; zaehlt wie Kopieren als Nutzung. */
  zweiteKopieren(): void {
    this.inZwischenablage(this.zweiteKopie?.text ?? '');
  }

  private inZwischenablage(text: string): void {
    if (this.vorschau || !text) {
      return;
    }
    this.clipboard.copy(text);
    this.snackBar.open('Erfolgreich kopiert!', 'Schließen', { duration: 1500 });

    this.copyAnimationActive = true;
    setTimeout(() => {
      this.copyAnimationActive = false;
      this.cdr.markForCheck();
    }, 600);

    if (this.inhaltId) {
      this.usageTrackingService.trackContentUsage(this.inhaltId, this.fassung ?? undefined);
      this.kopiert.emit();
    }
    this.cdr.markForCheck();
  }

  beitragOeffnen(): void {
    if (this.vorschau || !this.inhaltId) {
      return;
    }
    this.router.navigate([ROUTES.BEITRAG, this.inhaltId]);
  }

  /**
   * "Als Vorlage nehmen" (#356): nur angemeldet und nur, wo sich das Formular
   * vorbelegen laesst (Kommentar, Hintergrundinfo). Besucher sehen den Eintrag
   * nicht: Das Formular verlangt ohnehin eine Anmeldung.
   */
  get kannAlsVorlage(): boolean {
    return !this.vorschau && kannVorlageSein(this.typ) && !!this.authService.getUserInfo()?.isAuthenticated;
  }

  alsVorlageNehmen(): void {
    if (!this.kannAlsVorlage || !kannVorlageSein(this.typ)) {
      return;
    }
    const { pfad, queryParams } = vorlageAdresse(this.typ, this.inhaltId);
    this.router.navigate([pfad], { queryParams });
  }

  openReportDialog(): void {
    if (this.vorschau) {
      return;
    }
    meldeDialogOeffnen(this.dialog, { contentId: this.inhaltId, contentType: this.typ ?? '' });
  }

  private initializeVoteState(): void {
    this.anzeigen(this.stimme ?? null);
    this.ausgang = undefined;
  }

  private get angezeigt(): Stimme {
    return this.isLiked ? 'like' : this.isDisliked ? 'dislike' : null;
  }

  private anzeigen(stimme: Stimme): void {
    this.isLiked = stimme === 'like';
    this.isDisliked = stimme === 'dislike';
  }

  private umschalten(ziel: Stimme): void {
    // Waehrend eine Anfrage laeuft, bleibt der Knopf ohne Wirkung - die Anzeige
    // aendert sich dann auch nicht, es geht also keine Stimme stumm verloren.
    if (this.vorschau || this.isVoting) {
      return;
    }
    if (this.ausgang === undefined) {
      this.ausgang = this.angezeigt;
    }
    this.anzeigen(ziel);
    this.cdr.markForCheck();
    this.abgleich.next();
  }

  private abgleichen(): void {
    const ausgang = this.ausgang;
    const ziel = this.angezeigt;
    if (ausgang === undefined) {
      return;
    }
    if (ziel === ausgang) {
      this.ausgang = undefined;
      return;
    }

    const userInfo = this.authService.getUserInfo();
    if (!userInfo || !userInfo.isAuthenticated) {
      this.zuruecknehmen(ausgang);
      this.promptLogin();
      return;
    }

    const contentId = this.inhaltId;
    this.isVoting = true;

    const anfrage =
      ziel === 'like'
        ? this.votingService.setLike(contentId)
        : ziel === 'dislike'
          ? this.votingService.setDislike(contentId)
          : ausgang === 'like'
            ? this.votingService.removeLike(contentId)
            : this.votingService.removeDislike(contentId);
    const gemeldet = ziel === 'like' || (ziel === null && ausgang === 'like') ? this.likeToggled : this.dislikeToggled;

    anfrage.subscribe({
      next: () => {
        this.ausgang = undefined;
        this.isVoting = false;
        gemeldet.emit(contentId);
        this.cdr.markForCheck();
      },
      error: (error) => {
        this.logger.error('Failed to submit vote:', error);
        this.isVoting = false;
        this.zuruecknehmen(ausgang);
        this.handleVoteError(error);
      },
    });
  }

  private zuruecknehmen(ausgang: Stimme): void {
    this.anzeigen(ausgang);
    this.ausgang = undefined;
    this.cdr.markForCheck();
  }

  private promptLogin(): void {
    this.snackBar
      .open('Bitte melde dich an, um abzustimmen', 'Anmelden', { duration: 5000 })
      .onAction()
      .subscribe(() => {
        this.authService.login();
      });
  }

  private handleVoteError(error: any): void {
    if (einwilligungFehlt(error)) {
      // Den Hinweis mit Knopf zur Einwilligung zeigt der Auth-Interceptor (#489).
      return;
    }
    if (error.status === 401 || error.status === 403) {
      this.promptLogin();
    } else if (error.status === 429) {
      const retryAfter = error.headers?.get('Retry-After') || '60';
      this.snackBar.open(`Zu viele Anfragen. Bitte warte ${retryAfter} Sekunden.`, 'OK', {
        duration: 5000,
      });
    } else {
      this.snackBar.open('Fehler beim Abstimmen', 'Schließen', { duration: 3000 });
    }
  }
}
