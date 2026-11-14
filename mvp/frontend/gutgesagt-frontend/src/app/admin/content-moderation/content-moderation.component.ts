import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatBadgeModule } from '@angular/material/badge';
import { trigger, state, style, transition, animate } from '@angular/animations';
import { ModerationService, ContentReport, GemeldeterBeitrag } from '../../services/moderation.service';
import { ContentStatus } from '../../services/dtos/content-status-enum';
import { typLabel } from '../../shared/content-type-registry';
import { meldegrundLabel } from '../../shared/meldegruende';
import { sperrgrundLabel } from '../../shared/sperrgruende';
import { meldungsstatusLabel } from '../../shared/meldungsstatus';
import { SperrenDialogComponent, SperrenDialogDaten, SperrenDialogErgebnis } from './sperren-dialog.component';
import { AbweisenDialogComponent, AbweisenDialogDaten } from './abweisen-dialog.component';
import { kurzeKennung } from './kennung';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';
import { MeldungenEinerPersonComponent } from './meldungen-einer-person.component';
import { LoeschauftraegeComponent } from './loeschauftraege.component';
import { SuchanfragenFreigebenComponent } from './suchanfragen-freigeben.component';
import { MELDUNGEN_GRENZE, ZuTunService } from '../../services/zu-tun.service';
import { EMPTY, Observable, Subject, merge } from 'rxjs';
import { catchError, filter, tap } from 'rxjs/operators';
import { NACHLADEN_MS, SITZUNG_ABGELAUFEN, ohneRechte, selbstNachladen } from '../../shared/selbst-nachladen';
import { RouterLink } from '@angular/router';

// 'person': Meldungen einer Person nach Name oder E-Mail-Adresse (#494).
// 'loeschauftraege': Löschaufträge nach dem Widerruf der Art.-9-Einwilligung (DSFA R9b).
// 'suchanfragen': Suchanfragen freigeben (Vormoderation, 13.11.2026); lädt selbst.
type Ansicht = 'pending' | 'reviewed' | 'dismissed' | 'all' | 'gesperrt' | 'person' | 'loeschauftraege' | 'suchanfragen';
/** Die Ansichten, die eine Meldungsliste zeigen. */
type Meldungsansicht = 'pending' | 'reviewed' | 'dismissed' | 'all';
const ANSICHTEN: readonly Ansicht[] = ['pending', 'reviewed', 'dismissed', 'all', 'gesperrt', 'person', 'loeschauftraege', 'suchanfragen'];

/** Snackbar, wenn eine Aktion eine inzwischen erledigte Meldung träfe. */
export const MELDUNG_ERLEDIGT = 'Die Meldung ist inzwischen erledigt.';

/** Query-Parameter mit der gewählten Ansicht, etwa aus der Zeile „Zu tun“. */
export const ANSICHT_PARAM = 'ansicht';

function ansichtAus(wert: string | null): Ansicht | null {
  return ANSICHTEN.find((ansicht) => ansicht === wert) ?? null;
}

/** Rückfrage vor dem Entsperren (Persona-Runde 2, M1): ein Fehlklick machte Gesperrtes öffentlich. */
export const ENTSPERREN_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Sperre aufheben?',
  text: 'Der Beitrag ist danach wieder für alle sichtbar.',
  ja: 'Aufheben',
  nein: 'Abbrechen',
};

@Component({
  selector: 'app-content-moderation',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatButtonToggleModule,
    MatBadgeModule,
    MeldungenEinerPersonComponent,
    LoeschauftraegeComponent,
    RouterLink,
    SuchanfragenFreigebenComponent
  ],
  templateUrl: './content-moderation.component.html',
  styleUrls: ['./content-moderation.component.css'],
  animations: [
    trigger('expandCollapse', [
      state('collapsed', style({
        height: '0',
        overflow: 'hidden',
        opacity: 0,
        padding: '0'
      })),
      state('expanded', style({
        height: '*',
        overflow: 'visible',
        opacity: 1,
        padding: '16px'
      })),
      transition('collapsed <=> expanded', animate('300ms ease-in-out'))
    ])
  ]
})
/**
 * Die Moderation lädt selbst nach (Grundsatz 13.11.2026): beim Zurückkehren auf den Reiter
 * und alle NACHLADEN_MS, solange er sichtbar ist, ohne Spinner und ohne aufgeklappte Zeilen
 * zuzuklappen. Einen Knopf „Aktualisieren“ gibt es nicht mehr. Die Zahlen an „Offen“ und
 * „Löschaufträge“ kommen aus dem ZuTunService, den auch Kopf und Zeile „Zu tun“ nutzen.
 */
export class ContentModerationComponent implements OnInit {
  reports: ContentReport[] = [];
  // Ansicht "Gesperrt": gesperrte Beiträge, auch ohne Meldung; offene Widersprüche zuerst.
  gesperrte: GemeldeterBeitrag[] = [];
  /** Zahl am Umschalter "Gesperrt": Widersprüche, die auf erneute Prüfung warten. */
  offeneWidersprueche = 0;
  /** Zahl am Umschalter "Löschaufträge": offene Aufträge. */
  offeneLoeschauftraege = 0;
  /** Zahl am Umschalter "Offen": offene Meldungen. */
  offeneMeldungen = 0;
  /** Zahl am Umschalter "Suchanfragen": warten auf Freigabe (SuchanfragenFreigebenComponent). */
  zuPruefendeSuchanfragen = 0;
  loading = true;
  error: string | null = null;
  /** Ein stilles Nachladen ist gescheitert; die Liste zeigt den letzten Stand. */
  nachladefehler = false;
  selectedStatus: Ansicht = 'pending';
  displayedColumns: string[] = ['expand', 'content_type', 'reason', 'reporter', 'created', 'actions'];
  expandedReports = new Set<string>();
  private readonly destroyRef = inject(DestroyRef);
  private readonly zuTun = inject(ZuTunService);
  private readonly route = inject(ActivatedRoute, { optional: true });
  private readonly router = inject(Router, { optional: true });

  constructor(
    private moderationService: ModerationService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    const gewuenscht = ansichtAus(this.route?.snapshot?.queryParamMap?.get(ANSICHT_PARAM) ?? null);
    if (gewuenscht) {
      this.selectedStatus = gewuenscht;
    }
    // Links aus „Zu tun“ führen auch hierher, wenn die Moderation schon offen ist.
    this.route?.queryParamMap?.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const ansicht = ansichtAus(params.get(ANSICHT_PARAM));
      if (ansicht && ansicht !== this.selectedStatus) {
        this.selectedStatus = ansicht;
        this.loadReports();
      }
    });
    // Die Zahlen an den Umschaltern laden selbst nach, auch wenn ein anderer Umschalter offen ist.
    this.zuTun.meldungen$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((stand) => {
      if (stand.daten) {
        this.offeneMeldungen = stand.daten.anzahl;
      }
    });
    this.zuTun.loeschauftraege$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((stand) => {
      if (stand.daten) {
        this.offeneLoeschauftraege = stand.daten.anzahl;
      }
    });
    // Erst nach den Abos laden: Die offene Liste speist den ZuTunService gleich beim Laden.
    this.loadReports();
    if (this.selectedStatus !== 'gesperrt') {
      this.offeneWiderspruecheZaehlen();
    }
    selbstNachladen(() => this.stillesNachladen(), this.destroyRef, {
      next: () => {
        this.sitzungAbgelaufen = false;
        this.nachladenGestoppt = false;
      },
      // Nach 401/403 hört das Nachladen auf; statt „neuer Versuch“ der Weg zur Anmeldung.
      // Ob es gestoppt ist, merkt sich ein eigenes Flag: sitzungAbgelaufen setzt auch ein
      // ausdrückliches Laden zurück, das Nachladen bliebe dann unbemerkt stehen.
      error: (fehler) => {
        this.nachladenGestoppt = ohneRechte(fehler);
        if (this.nachladenGestoppt) this.sitzungAbgelaufen = true;
      },
    }, { ms: NACHLADEN_MS, aufhoerenBei: ohneRechte, anstoss$: this.wiederanlauf$ });
  }

  /** Für trackBy: Zeilen bleiben beim Nachladen dieselben DOM-Knoten, der Fokus bleibt. */
  readonly nachId = (_index: number, meldung: ContentReport) => meldung.id;
  readonly nachBeitragsId = (_index: number, beitrag: GemeldeterBeitrag): string => beitrag['id'];

  /** Ansichten, die selbst laden: die Suche nach Person, die Löschaufträge und die Suchanfragen. */
  get laedtSelbst(): boolean {
    return (
      this.selectedStatus === 'person' ||
      this.selectedStatus === 'loeschauftraege' ||
      this.selectedStatus === 'suchanfragen'
    );
  }

  /** Nach 401/403 beim Nachladen: Es wird nicht weiter gefragt, der Link führt zur Anmeldung. */
  sitzungAbgelaufen = false;

  /**
   * Startet das nach 401/403 gestoppte Nachladen wieder, sobald ausdrücklich geladen wird
   * (loadReports, auch nach einer Aktion). Ohne Stopp feuert es nicht: kein doppeltes Laden.
   */
  private readonly wiederanlauf$ = new Subject<void>();
  /** Das stille Nachladen ist nach 401/403 gestoppt (nachladeStrom, aufhoerenBei). */
  private nachladenGestoppt = false;

  /** Eine nachgeladene Liste wartet auf „neue anzeigen“ bzw. „Liste aktualisieren“. */
  get listeWartet(): boolean {
    return this.wartendeListe !== null;
  }
  readonly sitzungAbgelaufenText = SITZUNG_ABGELAUFEN;

  /** Wohin es nach dem Anmelden zurückgeht. */
  adresse(): string {
    return window.location.pathname + window.location.search;
  }

  /**
   * Zählt bei jedem ausdrücklichen Laden und jeder Aktion hoch. Ein stilles Nachladen, das
   * vorher losging, kommt mit altem Stand zurück und wird verworfen (auch fürs Speisen).
   */
  private generation = 0;

  /** Meldungen, die beim stillen Nachladen fehlten: ausgegraut stehen lassen bis zum nächsten Laden. */
  readonly erledigt = new Set<string>();

  istErledigt(meldung: ContentReport): boolean {
    return this.erledigt.has(meldung.id);
  }

  /** Lädt die Liste der gewählten Ansicht neu, mit Spinner; aufgeklappte Zeilen klappen zu. */
  loadReports() {
    const generation = ++this.generation;
    this.wartendeListe = null;
    this.neueMeldungen = 0;
    this.erledigt.clear();
    if (this.laedtSelbst) {
      // Die Suche lädt selbst, erst wenn Angaben eingegeben sind; die Löschaufträge
      // kommen aus dem ZuTunService, die Suchanfragen laden selbst und laden selbst nach.
      this.loading = false;
      this.error = null;
      this.nachladefehler = false;
      return;
    }
    this.loading = true;
    this.error = null;
    this.expandedReports.clear(); // Reset expanded rows on refresh
    if (this.nachladenGestoppt) {
      this.nachladenGestoppt = false;
      this.wiederanlauf$.next();
    }
    // Antworten einer Ansicht, die inzwischen verlassen ist, verwerfen: Sonst zeigt
    // etwa „Nach Person“ den Fehler einer alten Liste (#494). Ebenso Antworten, die ein
    // neueres Laden oder eine Aktion überholt hat.
    const ansicht = this.selectedStatus;
    const verlassen = () => this.selectedStatus !== ansicht || this.generation !== generation;

    if (ansicht === 'gesperrt') {
      this.moderationService.getGesperrte().subscribe({
        next: (response) => {
          if (verlassen()) return;
          this.gesperrteUebernehmen(response.beitraege);
          this.geladen();
        },
        error: (error) => {
          console.error('Error loading blocked content:', error);
          if (verlassen()) return;
          this.ladefehler(false, 'Gesperrte Beiträge gerade nicht erreichbar, neuer Versuch in Kürze …', error);
        }
      });
      return;
    }

    this.moderationService.getReports(ansicht as Meldungsansicht, MELDUNGEN_GRENZE).subscribe({
      next: (response) => {
        if (verlassen()) return;
        // Force new array reference for change detection
        this.reports = [...response.reports];
        this.meldungenGeladen(ansicht, response.reports);
        this.geladen();
        this.updateDisplayedColumns();
      },
      error: (error) => {
        console.error('Error loading reports:', error);
        if (verlassen()) return;
        this.ladefehler(false, 'Meldungen gerade nicht erreichbar, neuer Versuch in Kürze …', error);
      }
    });
  }

  /**
   * Ein stilles Nachladen (selbstNachladen): ohne Spinner, aufgeklappte Zeilen bleiben offen,
   * neue Meldungen werden angekündigt statt oben unter den Zeiger geschoben. Ein Fehler lässt
   * die Liste stehen und geht an den Takt zurück (längere Pause). Die Ansichten „Person“ und
   * „Löschaufträge“ fragen hier nichts, „Gesperrt“ zählt die Widersprüche aus seinen Daten.
   */
  stillesNachladen(): Observable<unknown> {
    const ansicht = this.selectedStatus;
    if (this.loading || this.laedtSelbst) {
      return EMPTY;
    }
    // Ohne Fehler steht eine Liste; nach einem Fehler bleibt dessen Hinweis bis zum Erfolg.
    const leise = !this.error;
    // Überholt ein ausdrückliches Laden oder eine Aktion diesen Lauf, zählt seine Antwort nicht.
    const generation = this.generation;
    const verlassen = () => this.selectedStatus !== ansicht || this.generation !== generation;

    if (ansicht === 'gesperrt') {
      return this.moderationService.getGesperrte(true).pipe(
        tap({
          next: (response) => {
            if (verlassen()) return;
            this.gesperrteUebernehmen(response.beitraege);
            this.geladen();
          },
          error: (e) => {
            if (!verlassen()) this.ladefehler(leise, 'Gesperrte Beiträge gerade nicht erreichbar, neuer Versuch in Kürze …', e);
          },
        })
      );
    }

    const liste = this.moderationService.getReports(ansicht as Meldungsansicht, MELDUNGEN_GRENZE, 0, true).pipe(
      tap({
        next: (response) => {
          if (verlassen()) return;
          this.stillUebernehmen(response.reports);
          this.meldungenGeladen(ansicht, response.reports);
          this.geladen();
        },
        error: (e) => {
          if (!verlassen()) this.ladefehler(leise, 'Meldungen gerade nicht erreichbar, neuer Versuch in Kürze …', e);
        },
      })
    );
    // Die Zahl am Umschalter „Gesperrt“ steht in keiner Meldungsliste: hier mitzählen.
    const widersprueche = this.moderationService.getGesperrte(true).pipe(
      tap((response) => {
        if (!verlassen()) this.offeneWidersprueche = zaehleOffene(response.beitraege);
      }),
      catchError(() => EMPTY)
    );
    return merge(liste, widersprueche);
  }

  /** Meldungen, die seit dem letzten Stand dazukamen und noch nicht in der Liste stehen. */
  neueMeldungen = 0;
  private wartendeListe: ContentReport[] | null = null;

  /** Die angekündigten neuen Meldungen einfügen, in der Reihenfolge des Dienstes. */
  neueZeigen() {
    this.reports = this.wartendeListe ?? this.reports.filter((meldung) => !this.erledigt.has(meldung.id));
    this.wartendeListe = null;
    this.neueMeldungen = 0;
    this.erledigtAufraeumen();
  }

  /** Erledigte fallen weg, ihre aufgeklappten Zeilen auch. */
  private erledigtAufraeumen() {
    this.erledigt.forEach((id) => this.expandedReports.delete(id));
    this.erledigt.clear();
  }

  /**
   * Übernimmt eine nachgeladene Liste, ohne Zeilen zu verschieben: bekannte Meldungen bekommen
   * ihren neuen Stand, fehlende bleiben ausgegraut als „erledigt“ stehen (Knöpfe gesperrt),
   * neue warten auf „N neue Meldungen“. Weg sind erledigte erst beim nächsten Laden.
   */
  private stillUebernehmen(neu: ContentReport[]) {
    // „erledigt“ nur, wo es sicher stimmt: in „Offen“ und unter der Grenze. Sonst kann eine
    // fehlende Zeile auch nur hinter der Grenze liegen; dann fällt sie erst bei „neue anzeigen“ weg.
    const sicher = this.selectedStatus === 'pending' && neu.length < MELDUNGEN_GRENZE;
    if (!this.reports.length) {
      // Nichts steht unter dem Zeiger: gleich alles zeigen.
      this.reports = [...neu];
      this.wartendeListe = null;
      this.neueMeldungen = 0;
      return;
    }
    const frisch = new Map(neu.map((meldung) => [meldung.id, meldung]));
    const bekannt = new Set(this.reports.map((meldung) => meldung.id));
    this.reports = this.reports.map((meldung) => {
      const neuerStand = frisch.get(meldung.id);
      if (neuerStand) {
        this.erledigt.delete(meldung.id);
        return neuerStand;
      }
      if (sicher) {
        this.erledigt.add(meldung.id);
      }
      return meldung;
    });
    const neue = neu.filter((meldung) => !bekannt.has(meldung.id));
    // Fehlende ohne „erledigt“ (siehe oben) verschwinden leise mit „neue anzeigen“.
    const fehlenUnmarkiert = !sicher && this.reports.some((meldung) => !frisch.has(meldung.id));
    this.wartendeListe = neue.length || fehlenUnmarkiert ? [...neu] : null;
    this.neueMeldungen = neue.length;
  }

  /**
   * Nach einer Aktion: neu laden. Steht „Offen“, speist die Liste den ZuTunService; sonst
   * muss die Zahl der offenen eigens nachgezogen werden.
   */
  private nachAktion() {
    this.loadReports();
    if (this.selectedStatus !== 'pending') {
      this.zuTun.aktualisieren();
    }
  }

  private gesperrteUebernehmen(beitraege: GemeldeterBeitrag[]) {
    this.gesperrte = nachWiderspruch(beitraege);
    this.offeneWidersprueche = zaehleOffene(beitraege);
  }

  /** Die offene Liste speist den ZuTunService: Kopf und „Zu tun“ fragen dann nicht doppelt. */
  private meldungenGeladen(ansicht: Ansicht, meldungen: ContentReport[]) {
    if (ansicht === 'pending') {
      this.zuTun.meldungenGespeist(meldungen);
    }
  }

  private geladen() {
    this.loading = false;
    this.error = null;
    this.nachladefehler = false;
    this.sitzungAbgelaufen = false;
  }

  /**
   * Steht eine Liste, bleibt sie beim Fehler stehen; sonst ersetzt der Hinweis sie bis zum nächsten
   * Versuch. Bei 401/403 kein „neuer Versuch“ samt Spinner, sondern nur der Link zur Anmeldung.
   */
  private ladefehler(leise: boolean, text: string, fehler?: unknown) {
    this.loading = false;
    if (ohneRechte(fehler)) {
      this.sitzungAbgelaufen = true;
      this.error = null;
      this.nachladefehler = false;
      return;
    }
    if (leise) {
      this.nachladefehler = true;
    } else {
      this.error = text;
    }
  }

  onStatusFilterChange(status: Ansicht) {
    this.selectedStatus = status;
    this.loadReports();
    // Die Ansicht in der Adresse, damit ein Link aus „Zu tun“ auch danach wieder wirkt.
    this.router?.navigate([], {
      relativeTo: this.route ?? undefined,
      queryParams: { [ANSICHT_PARAM]: status },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  updateDisplayedColumns() {
    // Base columns
    const baseColumns = ['expand', 'content_type', 'reason', 'reporter', 'created'];

    // Add status column for non-pending views
    if (this.selectedStatus !== 'pending') {
      baseColumns.push('status');
    }

    // Add reviewed_by column for reviewed/dismissed/all views
    if (this.selectedStatus === 'reviewed' || this.selectedStatus === 'dismissed' || this.selectedStatus === 'all') {
      baseColumns.push('reviewed_by');
    }

    // Aktionen in jeder Ansicht: Entsperren betrifft bearbeitete Meldungen.
    baseColumns.push('actions');

    this.displayedColumns = baseColumns;
  }

  readonly kurzeKennung = kurzeKennung;

  /** Der Text eines Beitrags (Kommentar, Hintergrundinfo, Aussage); null ohne Text. */
  beitragsText(beitrag: GemeldeterBeitrag): string | null {
    const text = beitrag['text'] || beitrag['long_text'] || beitrag['short_text'];
    return typeof text === 'string' && text.trim() ? text : null;
  }

  /** Gesperrte Beiträge, deren Text aufgeklappt ist. */
  private readonly offeneTexte = new Set<string>();

  textOffen(beitrag: GemeldeterBeitrag): boolean {
    return this.offeneTexte.has(beitrag['id']);
  }

  textUmschalten(beitrag: GemeldeterBeitrag) {
    const id = beitrag['id'];
    if (!this.offeneTexte.delete(id)) {
      this.offeneTexte.add(id);
    }
  }

  /** Die interne Begründung; frühere Abweisungen trugen nur einen englischen Platzhalter. */
  entscheidungsBegruendung(report: ContentReport): string {
    const notiz = report.resolution_notes?.trim();
    if (!notiz || notiz === 'Report dismissed' || notiz === 'Dismissed by admin') {
      return 'ohne Begründung';
    }
    return notiz;
  }

  beitragsTitel(beitrag: GemeldeterBeitrag): string {
    return beitrag['title'] || beitrag['text'] || beitrag['id'];
  }

  istGesperrt(report: ContentReport): boolean {
    return report.content?.status === ContentStatus.BLOCKED;
  }

  /** Sperren nur mit Sperrgrund und Begründung (#448); beides fragt der Dialog ab. */
  sperren(report: ContentReport) {
    if (this.erledigtMelden(report)) return;
    const daten: SperrenDialogDaten = {
      art: 'sperren',
      titel: this.beitragsTitel(report.content ?? { id: report.content_id }),
      text: report.content ? this.beitragsText(report.content) : null,
    };
    this.dialog
      .open<SperrenDialogComponent, SperrenDialogDaten, SperrenDialogErgebnis>(SperrenDialogComponent, { data: daten, width: '520px' })
      .afterClosed()
      .subscribe((ergebnis) => {
        if (!ergebnis?.sperrgrund) {
          return;
        }
        // Während der Dialog offen war, kann die Meldung erledigt worden sein.
        if (this.erledigtMelden(report)) return;
        this.generation++; // ein stilles Nachladen von vorher zählt nicht mehr
        this.moderationService.sperren(report.content_id, ergebnis.sperrgrund, ergebnis.begruendung).subscribe({
          next: () => {
            this.snackBar.open('Beitrag gesperrt', 'OK', { duration: 3000 });
            this.nachAktion();
          },
          error: (error) => {
            const text = error?.status === 409 ? 'Der Beitrag ist schon gesperrt' : 'Fehler beim Sperren des Beitrags';
            this.snackBar.open(text, 'OK', { duration: 3000 });
            console.error('Error blocking content:', error);
          }
        });
      });
  }

  /** Nach einem Widerspruch bleibt die Sperre; die Begründung liest der Autor. */
  sperreBestaetigen(beitrag: GemeldeterBeitrag) {
    const sperre = beitrag.sperre;
    if (!sperre) {
      return;
    }
    const daten: SperrenDialogDaten = {
      art: 'bestaetigen',
      titel: this.beitragsTitel(beitrag),
      text: this.beitragsText(beitrag),
      widerspruch: sperre.widerspruch,
    };
    this.dialog
      .open<SperrenDialogComponent, SperrenDialogDaten, SperrenDialogErgebnis>(SperrenDialogComponent, { data: daten, width: '520px' })
      .afterClosed()
      .subscribe((ergebnis) => {
        if (!ergebnis) {
          return;
        }
        this.generation++;
        this.moderationService.sperreBestaetigen(sperre.id, ergebnis.begruendung).subscribe({
          next: () => {
            this.snackBar.open('Sperre bestätigt', 'OK', { duration: 3000 });
            this.loadReports();
          },
          error: (error) => {
            this.snackBar.open('Fehler beim Bestätigen der Sperre', 'OK', { duration: 3000 });
            console.error('Error confirming Sperre:', error);
          }
        });
      });
  }

  /** Lädt die gesperrten Beiträge nur, um die offenen Widersprüche am Umschalter zu zählen. */
  private offeneWiderspruecheZaehlen() {
    const generation = this.generation;
    this.moderationService.getGesperrte().subscribe({
      next: (response) => {
        // Überholt ein Laden oder eine Aktion die Zählung, zählt deren Stand.
        if (generation === this.generation) this.offeneWidersprueche = zaehleOffene(response.beitraege);
      },
      error: (error) => console.error('Error counting Widersprüche:', error)
    });
  }

  /** Die Liste der Löschaufträge meldet ihre Zahl (Ereignis „anzahl“); sie kommt aus demselben ZuTunService. */
  loeschauftraegeGezaehlt(anzahl: number) {
    this.offeneLoeschauftraege = anzahl;
  }

  getSperrgrundLabel(sperrgrund: string): string {
    return sperrgrundLabel(sperrgrund);
  }

  /** Entsperren aus einer Meldungszeile: nicht für eine erledigte (gesperrt dargestellte) Zeile. */
  meldungEntsperren(report: ContentReport) {
    if (this.erledigtMelden(report)) return;
    this.entsperren(report.content_id, () => !this.erledigtMelden(report));
  }

  /** Entsperren erst nach der Rückfrage (M1). */
  entsperren(contentId: string, vorher: () => boolean = () => true) {
    this.dialog
      .open(BestaetigungsDialogComponent, { data: ENTSPERREN_FRAGE, autoFocus: 'dialog' })
      .afterClosed()
      .pipe(filter((ja) => ja === true))
      .subscribe(() => {
        // Während der Dialog offen war, kann die Meldung erledigt worden sein.
        if (vorher()) this.entsperrenOhneFrage(contentId);
      });
  }

  private entsperrenOhneFrage(contentId: string) {
    this.generation++;
    this.moderationService.entsperren(contentId).subscribe({
      next: () => {
        this.snackBar.open('Sperre aufgehoben', 'OK', { duration: 3000 });
        this.nachAktion();
      },
      error: (error) => {
        this.snackBar.open('Fehler beim Entsperren des Beitrags', 'OK', { duration: 3000 });
        console.error('Error unblocking content:', error);
      }
    });
  }

  /**
   * Abweisen nur mit Begründung aus dem Dialog (Persona-Test 13.11.2026): Grund aus fester Liste,
   * dazu ein Satz. Sie geht als notes an den Suchdienst und bleibt intern an der Meldung.
   */
  dismissReport(report: ContentReport) {
    if (this.erledigtMelden(report)) return;
    const daten: AbweisenDialogDaten = {
      titel: this.beitragsTitel(report.content ?? { id: report.content_id }),
      meldegrund: this.getReasonLabel(report.reason),
      mitMail: !!report.melder_email,
    };
    this.dialog
      .open<AbweisenDialogComponent, AbweisenDialogDaten, string>(AbweisenDialogComponent, { data: daten, width: '520px' })
      .afterClosed()
      .subscribe((begruendung) => {
        if (begruendung) {
          this.abweisen(report, begruendung);
        }
      });
  }

  /** Eine erledigte Meldung (ausgegraut) bekommt keine Aktion mehr; das sagt eine Snackbar. */
  private erledigtMelden(report: ContentReport): boolean {
    if (!this.istErledigt(report)) {
      return false;
    }
    this.snackBar.open(MELDUNG_ERLEDIGT, 'OK', { duration: 5000 });
    return true;
  }

  private abweisen(report: ContentReport, begruendung: string) {
    // Während der Dialog offen war, kann die Meldung erledigt worden sein.
    if (this.erledigtMelden(report)) return;
    this.generation++;
    this.moderationService.dismissReport(report.id, begruendung).subscribe({
      next: (response) => {
        this.snackBar.open('Meldung abgewiesen', 'OK', { duration: 3000 });
        this.nachAktion(); // Reload to remove from list
      },
      error: (error) => {
        // 409: inzwischen bearbeitet oder abgewiesen (etwa aus einem anderen Fenster).
        const text = error?.status === 409 ? MELDUNG_ERLEDIGT : 'Fehler beim Abweisen der Meldung';
        this.snackBar.open(text, 'OK', { duration: 5000 });
        if (error?.status === 409) {
          this.nachAktion();
        }
        console.error('Error dismissing report:', error);
      }
    });
  }

  /**
   * Was hinter „Anonym“ steht. Offene anonyme Meldungen tragen das Tagespseudonym
   * („besucher:…“, #446): gleicher Anfang heißt dieselbe Quelle am selben Tag.
   * Erledigte tragen einen Zufallswert („anon:…“) und zeigen nichts; alte Meldungen
   * den Anfang ihrer Sitzungskennung.
   */
  melderQuelle(kennung: string): string | null {
    if (kennung.startsWith('anon:')) {
      return null;
    }
    if (kennung.startsWith('besucher:')) {
      return `Quelle ${kennung.substring('besucher:'.length, 'besucher:'.length + 8)}`;
    }
    return kennung.substring(0, 8);
  }

  /**
   * mailto-Link an die meldende Person (#438). Die Adresse kommt von aussen: `?` oder `&`
   * im lokalen Teil wuerden sonst Empfaenger oder Betreff anhaengen.
   */
  mailtoLink(email: string): string {
    const at = email.lastIndexOf('@');
    return `mailto:${encodeURIComponent(email.slice(0, at))}@${encodeURIComponent(email.slice(at + 1))}`;
  }

  getReasonLabel(reason: string): string {
    return meldegrundLabel(reason);
  }

  getContentTypeLabel(type: string): string {
    return typLabel(type);
  }

  /** Datum als Tag (mit Komma) und Uhrzeit, damit die Tabelle nur zwischen beiden umbricht. */
  datumTeile(dateString: string): { tag: string; zeit: string } {
    const text = this.formatDate(dateString);
    const komma = text.indexOf(', ');
    return komma < 0 ? { tag: text, zeit: '' } : { tag: text.slice(0, komma + 1), zeit: text.slice(komma + 2) };
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  toggleExpand(report: ContentReport): void {
    const reportId = report.id;
    if (this.expandedReports.has(reportId)) {
      this.expandedReports.delete(reportId);
    } else {
      this.expandedReports.add(reportId);
    }
  }

  isExpanded(report: ContentReport): boolean {
    return this.expandedReports.has(report.id);
  }

  getStatusLabel(status: string): string {
    return meldungsstatusLabel(status);
  }

  getStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      'pending': 'warn',
      'reviewed': 'accent',
      'dismissed': 'primary'
    };
    return colors[status] || '';
  }
}

function zaehleOffene(beitraege: GemeldeterBeitrag[]): number {
  return beitraege.filter((b) => b.sperre?.widerspruch_offen).length;
}

/** Offene Widersprüche zuerst, sonst in der Reihenfolge des Dienstes. */
function nachWiderspruch(beitraege: GemeldeterBeitrag[]): GemeldeterBeitrag[] {
  return [...beitraege].sort((a, b) => Number(!!b.sperre?.widerspruch_offen) - Number(!!a.sperre?.widerspruch_offen));
}
