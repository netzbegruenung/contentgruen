import { Component, OnInit } from '@angular/core';
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
import { AUSSAGE_PARAM, FORMULAR_PFAD } from '../shared/formular-adresse';
import {
  VON_HIER_FEHLT_EINE_ANTWORT,
  VON_PARAM,
} from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';

/**
 * "Hier fehlt eine Antwort": Mitwirkende sehen die unbeantworteten Aussagen (ohne
 * Kommentar oder mit Suchen ohne Treffer von mindestens zwei Personen), sortiert
 * nach Bedarf, und koennen sie selbst beantworten. Fuer absehbare Themen legen sie
 * hier Aussagen vorab an. Zahlen der Kennzahl zeigt die Seite nicht, und eine Aussage
 * aus einer Suchanfrage erst ab der Schwelle der Kennzahl (zwei Personen).
 */
@Component({
  selector: 'app-hier-fehlt-eine-antwort',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './hier-fehlt-eine-antwort.component.html',
  styleUrls: ['./hier-fehlt-eine-antwort.component.css'],
})
export class HierFehltEineAntwortComponent implements OnInit {
  readonly kommentarFormular = FORMULAR_PFAD.commentary;
  readonly maxZeichen = AUSSAGE_MAX_ZEICHEN;

  aussagen: UnbeantworteteAussage[] | null = null;
  ladefehler = false;

  neueAussage = '';
  speichert = false;
  meldung = '';

  constructor(private statementService: StatementService) {}

  ngOnInit(): void {
    this.laden();
  }

  /**
   * Query-Parameter fuer "Selbst beantworten": das Kommentarformular mit dieser
   * Aussage; ?von= fuehrt die Pfeile hierher zurueck.
   */
  beantwortenParams(aussage: UnbeantworteteAussage): Record<string, string> {
    return { [AUSSAGE_PARAM]: aussage.statement_id, [VON_PARAM]: VON_HIER_FEHLT_EINE_ANTWORT };
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
    this.statementService.aussageVorabAnlegen(this.neueAussage).subscribe({
      next: (antwort) => {
        this.speichert = false;
        this.neueAussage = '';
        this.meldung = antwort.statement_was_new
          ? 'Aussage angelegt.'
          : `Diese Aussage gibt es schon: „${antwort.statement_text}“`;
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
    this.statementService.unbeantworteteAussagen().subscribe({
      next: (aussagen) => (this.aussagen = aussagen),
      error: () => (this.ladefehler = true),
    });
  }
}
