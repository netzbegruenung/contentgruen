import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import {
  AUSSAGE_MAX_ZEICHEN,
  AUSSAGE_MIN_ZEICHEN,
  StatementService,
} from '../services/statement.service';
import { UnbeantworteteAussage } from '../services/dtos/statementDtos';
import { Thema } from '../services/dtos/themenDtos';
import { ThemenService } from '../services/themen.service';
import { ThemenAuswahlComponent } from '../shared/themen/themen-auswahl.component';
import { ThemenFilterComponent } from '../shared/themen/themen-filter.component';
import { AUSSAGE_PARAM, FORMULAR_PFAD } from '../shared/formular-adresse';
import {
  VON_HIER_FEHLT_EINE_ANTWORT,
  VON_PARAM,
} from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';

/**
 * "Hier fehlt eine Antwort": Mitwirkende sehen die unbeantworteten Aussagen (ohne
 * Kommentar oder mit Suchen ohne Treffer von mindestens zwei Personen), sortiert
 * nach Bedarf, und koennen sie selbst beantworten. Fuer absehbare Themen legen sie
 * hier Aussagen vorab an. Von der Kennzahl zeigt die Seite nur die Zahl der Personen,
 * die ohne Treffer gesucht haben, damit Hotspots sichtbar werden, nicht die Zahl der
 * Suchen; eine Aussage aus einer Suchanfrage erst ab der Schwelle der Kennzahl
 * (zwei Personen).
 *
 * Themen: Die Liste laesst sich nach einem Thema filtern, jede Aussage zeigt ihre
 * Themen, und Mitwirkende ordnen sie hier zu oder aendern sie, auch beim Anlegen
 * vorab. Ist die Themenliste nicht ladbar, fehlen Filter und Auswahl; die Seite
 * bleibt sonst nutzbar.
 */
@Component({
  selector: 'app-hier-fehlt-eine-antwort',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    ThemenAuswahlComponent,
    ThemenFilterComponent,
  ],
  templateUrl: './hier-fehlt-eine-antwort.component.html',
  styleUrls: ['./hier-fehlt-eine-antwort.component.css'],
})
export class HierFehltEineAntwortComponent implements OnInit, OnDestroy {
  readonly kommentarFormular = FORMULAR_PFAD.commentary;
  readonly maxZeichen = AUSSAGE_MAX_ZEICHEN;

  aussagen: UnbeantworteteAussage[] | null = null;
  ladefehler = false;

  /** Die feste Themenliste; leer, solange sie nicht geladen ist. */
  themen: Thema[] = [];
  /** Der Filter; null = alle Themen. */
  aktivesThema: string | null = null;
  /** Die Aussage, deren Themen gerade bearbeitet werden. */
  themenBearbeiten: string | null = null;
  themenFehler: string | null = null;

  neueAussage = '';
  neueThemen: string[] = [];
  /** Die laufende Abfrage der Liste; ein neuer Filter bricht sie ab. */
  private ladend?: Subscription;
  speichert = false;
  meldung = '';

  constructor(
    private statementService: StatementService,
    private themenService: ThemenService,
  ) {}

  ngOnInit(): void {
    this.themenService.liste().subscribe({
      next: (themen) => (this.themen = themen),
      error: () => (this.themen = []),
    });
    this.laden();
  }

  ngOnDestroy(): void {
    this.ladend?.unsubscribe();
  }

  filtern(thema: string | null): void {
    this.aktivesThema = thema;
    this.themenBearbeiten = null;
    this.laden();
  }

  /** Die Themen einer Aussage auf- oder zuklappen. */
  themenUmschalten(aussage: UnbeantworteteAussage): void {
    this.themenFehler = null;
    this.themenBearbeiten = this.themenBearbeiten === aussage.statement_id ? null : aussage.statement_id;
  }

  schluessel(aussage: UnbeantworteteAussage): string[] {
    return aussage.themen.map((t) => t.schluessel);
  }

  /** Jede Aenderung der Auswahl wird gleich gespeichert. */
  themenSetzen(aussage: UnbeantworteteAussage, themen: string[]): void {
    this.themenFehler = null;
    this.themenService.zuordnen(aussage.statement_id, themen).subscribe({
      next: (gespeichert) => (aussage.themen = gespeichert),
      error: () => (this.themenFehler = 'Die Themen konnten nicht gespeichert werden.'),
    });
  }

  /**
   * Query-Parameter fuer "Selbst beantworten": das Kommentarformular mit dieser
   * Aussage; ?von= fuehrt die Pfeile hierher zurueck.
   */
  beantwortenParams(aussage: UnbeantworteteAussage): Record<string, string> {
    return { [AUSSAGE_PARAM]: aussage.statement_id, [VON_PARAM]: VON_HIER_FEHLT_EINE_ANTWORT };
  }

  /** Der Marker an einer Aussage, nach der ohne Treffer gesucht wurde, mit Personenzahl. */
  gesuchtMarker(aussage: UnbeantworteteAussage): string {
    const n = aussage.personen_ohne_treffer;
    return `Danach wurde ohne Treffer gesucht: ${n} ${n === 1 ? 'Person' : 'Personen'}`;
  }

  get anlegbar(): boolean {
    return !this.speichert && this.neueAussage.trim().length >= AUSSAGE_MIN_ZEICHEN;
  }

  eingabe(wert: string): void {
    this.neueAussage = wert;
    this.meldung = '';
  }

  anlegen(): void {
    if (!this.anlegbar) {
      return;
    }
    this.speichert = true;
    this.meldung = '';
    const mitThemen = this.neueThemen.length > 0;
    this.statementService.aussageVorabAnlegen(this.neueAussage, this.neueThemen).subscribe({
      next: (antwort) => {
        this.speichert = false;
        this.neueAussage = '';
        this.neueThemen = [];
        this.meldung = antwort.statement_was_new
          ? 'Aussage angelegt.'
          : `Diese Aussage gibt es schon: „${antwort.statement_text}“` +
            (mitThemen ? ' Ihre Themen änderst du in der Liste.' : '');
        this.laden();
      },
      error: () => {
        this.speichert = false;
        this.meldung = 'Die Aussage konnte nicht angelegt werden. Bitte versuche es erneut.';
      },
    });
  }

  private laden(): void {
    this.ladefehler = false;
    // Sonst koennte eine langsame Antwort zum vorigen Filter die aktuelle ueberschreiben.
    this.ladend?.unsubscribe();
    this.ladend = this.statementService.unbeantworteteAussagen(this.aktivesThema).subscribe({
      next: (aussagen) => (this.aussagen = aussagen),
      error: () => (this.ladefehler = true),
    });
  }
}
