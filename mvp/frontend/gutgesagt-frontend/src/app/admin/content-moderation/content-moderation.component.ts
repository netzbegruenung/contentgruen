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
import { MeldungenEinerPersonComponent } from './meldungen-einer-person.component';
import { LoeschauftraegeComponent } from './loeschauftraege.component';
import { ZuTunService } from '../../services/zu-tun.service';
import { selbstNachladen } from '../../shared/selbst-nachladen';

// 'person': Meldungen einer Person nach Name oder E-Mail-Adresse (#494).
// 'loeschauftraege': Löschaufträge nach dem Widerruf der Art.-9-Einwilligung (DSFA R9b).
type Ansicht = 'pending' | 'reviewed' | 'dismissed' | 'all' | 'gesperrt' | 'person' | 'loeschauftraege';
const ANSICHTEN: readonly Ansicht[] = ['pending', 'reviewed', 'dismissed', 'all', 'gesperrt', 'person', 'loeschauftraege'];

/** Query-Parameter mit der gewählten Ansicht, etwa aus der Zeile „Zu tun“. */
export const ANSICHT_PARAM = 'ansicht';

function ansichtAus(wert: string | null): Ansicht | null {
  return ANSICHTEN.find((ansicht) => ansicht === wert) ?? null;
}

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
    LoeschauftraegeComponent
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
    this.loadReports();
    this.offeneWiderspruecheZaehlen();
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
    selbstNachladen(() => this.stillNachladen(), this.destroyRef);
  }

  /** Liste und Zahl der Widersprüche neu holen, ohne Spinner und ohne Zeilen zuzuklappen. */
  stillNachladen() {
    this.loadReports(true);
    this.offeneWiderspruecheZaehlen();
  }

  /** Ansichten, die selbst laden: die Suche nach Person und die Löschaufträge. */
  get laedtSelbst(): boolean {
    return this.selectedStatus === 'person' || this.selectedStatus === 'loeschauftraege';
  }

  /**
   * Lädt die Liste der gewählten Ansicht. ``still``: beim Nachladen ohne Spinner, aufgeklappte
   * Zeilen bleiben offen, und ein Fehler lässt den letzten Stand stehen.
   */
  loadReports(still = false) {
    if (this.selectedStatus === 'person' || this.selectedStatus === 'loeschauftraege') {
      // Die Suche lädt selbst, erst wenn Angaben eingegeben sind; die Löschaufträge
      // laden selbst und laden selbst nach.
      this.loading = false;
      this.error = null;
      this.nachladefehler = false;
      return;
    }
    if (still && this.loading) {
      return; // Das erste Laden läuft noch.
    }
    // Still und ohne Fehler steht eine Liste; scheitert das Nachladen, bleibt sie stehen.
    // Nach einem Fehler bleibt dessen Hinweis (mit Spinner) bis zum Erfolg stehen.
    const leise = still && !this.error;
    if (!still) {
      this.loading = true;
      this.error = null;
      this.expandedReports.clear(); // Reset expanded rows on refresh
    }
    // Antworten einer Ansicht, die inzwischen verlassen ist, verwerfen: Sonst zeigt
    // etwa „Nach Person“ den Fehler einer alten Liste (#494).
    const ansicht = this.selectedStatus;
    const verlassen = () => this.selectedStatus !== ansicht;

    if (ansicht === 'gesperrt') {
      this.moderationService.getGesperrte().subscribe({
        next: (response) => {
          if (verlassen()) return;
          this.gesperrte = nachWiderspruch(response.beitraege);
          this.offeneWidersprueche = zaehleOffene(response.beitraege);
          this.geladen();
        },
        error: (error) => {
          console.error('Error loading blocked content:', error);
          if (verlassen()) return;
          this.ladefehler(leise, 'Gesperrte Beiträge gerade nicht erreichbar, neuer Versuch in Kürze …');
        }
      });
      return;
    }

    this.moderationService.getReports(ansicht).subscribe({
      next: (response) => {
        if (verlassen()) return;
        // Force new array reference for change detection
        this.reports = [...response.reports];
        this.geladen();
        this.updateDisplayedColumns();
      },
      error: (error) => {
        console.error('Error loading reports:', error);
        if (verlassen()) return;
        this.ladefehler(leise, 'Meldungen gerade nicht erreichbar, neuer Versuch in Kürze …');
      }
    });
  }

  private geladen() {
    this.loading = false;
    this.error = null;
    this.nachladefehler = false;
  }

  /** Steht eine Liste, bleibt sie beim Fehler stehen; sonst ersetzt der Hinweis sie bis zum nächsten Versuch. */
  private ladefehler(leise: boolean, text: string) {
    this.loading = false;
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

  beitragsTitel(beitrag: GemeldeterBeitrag): string {
    return beitrag['title'] || beitrag['text'] || beitrag['id'];
  }

  istGesperrt(report: ContentReport): boolean {
    return report.content?.status === ContentStatus.BLOCKED;
  }

  /** Sperren nur mit Sperrgrund und Begründung (#448); beides fragt der Dialog ab. */
  sperren(report: ContentReport) {
    const daten: SperrenDialogDaten = { art: 'sperren', titel: this.beitragsTitel(report.content ?? { id: report.content_id }) };
    this.dialog
      .open<SperrenDialogComponent, SperrenDialogDaten, SperrenDialogErgebnis>(SperrenDialogComponent, { data: daten, width: '520px' })
      .afterClosed()
      .subscribe((ergebnis) => {
        if (!ergebnis?.sperrgrund) {
          return;
        }
        this.moderationService.sperren(report.content_id, ergebnis.sperrgrund, ergebnis.begruendung).subscribe({
          next: () => {
            this.snackBar.open('Beitrag gesperrt', 'OK', { duration: 3000 });
            this.loadReports();
            this.zuTun.aktualisieren();
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
    const daten: SperrenDialogDaten = { art: 'bestaetigen', titel: this.beitragsTitel(beitrag) };
    this.dialog
      .open<SperrenDialogComponent, SperrenDialogDaten, SperrenDialogErgebnis>(SperrenDialogComponent, { data: daten, width: '520px' })
      .afterClosed()
      .subscribe((ergebnis) => {
        if (!ergebnis) {
          return;
        }
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
    this.moderationService.getGesperrte().subscribe({
      next: (response) => (this.offeneWidersprueche = zaehleOffene(response.beitraege)),
      error: (error) => console.error('Error counting Widersprüche:', error)
    });
  }

  /** Die Liste der Löschaufträge hat sich geändert (Ereignis „anzahl“): Zahl und „Zu tun“ nachziehen. */
  loeschauftraegeGezaehlt(anzahl: number) {
    if (anzahl !== this.offeneLoeschauftraege) {
      this.offeneLoeschauftraege = anzahl;
      this.zuTun.aktualisieren();
    }
  }

  getSperrgrundLabel(sperrgrund: string): string {
    return sperrgrundLabel(sperrgrund);
  }

  entsperren(contentId: string) {
    this.moderationService.entsperren(contentId).subscribe({
      next: () => {
        this.snackBar.open('Sperre aufgehoben', 'OK', { duration: 3000 });
        this.loadReports();
        this.zuTun.aktualisieren();
      },
      error: (error) => {
        this.snackBar.open('Fehler beim Entsperren des Beitrags', 'OK', { duration: 3000 });
        console.error('Error unblocking content:', error);
      }
    });
  }

  dismissReport(report: ContentReport) {
    this.moderationService.dismissReport(report.id, 'Dismissed by admin').subscribe({
      next: (response) => {
        this.snackBar.open('Meldung abgewiesen', 'OK', { duration: 3000 });
        this.loadReports(); // Reload to remove from list
        this.zuTun.aktualisieren();
      },
      error: (error) => {
        this.snackBar.open('Fehler beim Abweisen der Meldung', 'OK', { duration: 3000 });
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
