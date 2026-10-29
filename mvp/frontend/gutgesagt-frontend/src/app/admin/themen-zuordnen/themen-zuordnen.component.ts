import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AussageMitThemen, Thema } from '../../services/dtos/themenDtos';
import { ThemenService, schluesselVon } from '../../services/themen.service';
import { ThemenAuswahlComponent } from '../../shared/themen/themen-auswahl.component';

/** Dateiname des Testsets beim Herunterladen. */
export const TESTSET_DATEI = 'themen-testset.json';

/**
 * Themen nachtraeglich zuordnen (#363): alle Aussagen ohne die unbeantworteten
 * Suchanfragen, die ohne Thema zuerst. Jede Aenderung wird gleich gespeichert.
 * Die Zuordnungen von Hand lassen sich als Testset fuer spaetere Themenvorschlaege
 * herunterladen, ohne Personendaten.
 */
@Component({
  selector: 'app-themen-zuordnen',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, ThemenAuswahlComponent],
  templateUrl: './themen-zuordnen.component.html',
  styleUrls: ['./themen-zuordnen.component.css'],
})
export class ThemenZuordnenComponent implements OnInit {
  themen: Thema[] = [];
  aussagen: AussageMitThemen[] | null = null;
  fehler: string | null = null;

  constructor(private themenService: ThemenService) {}

  ngOnInit(): void {
    this.themenService.liste().subscribe({
      next: (themen) => (this.themen = themen),
      error: () => (this.fehler = 'Die Themenliste konnte nicht geladen werden.'),
    });
    this.themenService.aussagenZumZuordnen().subscribe({
      next: (aussagen) => (this.aussagen = aussagen),
      error: () => (this.fehler = 'Die Aussagen konnten nicht geladen werden.'),
    });
  }

  get zugeordnet(): number {
    return (this.aussagen ?? []).filter((a) => a.themen.length > 0).length;
  }

  /** Wie viele Zuordnungen ins Testset gehen; Aussagen aus Suchanfragen nicht. */
  get imTestset(): number {
    return (this.aussagen ?? []).filter((a) => a.themen.length > 0 && a.im_testset).length;
  }

  readonly schluessel = schluesselVon;

  /** Jede Aenderung der Auswahl wird gleich gespeichert (ThemenService.aendern). */
  setzen(aussage: AussageMitThemen, themen: string[]): void {
    this.fehler = null;
    this.themenService.aendern(aussage, themen, this.themen, () => {
      this.fehler = 'Die Themen konnten nicht gespeichert werden.';
    });
  }

  testsetHerunterladen(): void {
    this.fehler = null;
    this.themenService.testset().subscribe({
      next: (testset) => {
        const blob = new Blob([JSON.stringify(testset, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = TESTSET_DATEI;
        link.click();
        URL.revokeObjectURL(url);
      },
      error: () => (this.fehler = 'Das Testset konnte nicht geladen werden.'),
    });
  }
}
