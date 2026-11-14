import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { selbstNachladen } from '../../shared/selbst-nachladen';
import { NachladeHinweisComponent } from '../../shared/components/nachlade-hinweis/nachlade-hinweis.component';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { filter } from 'rxjs';
import { FeedbackEintrag, FeedbackListe, FeedbackService } from '../../shared/feedback/feedback.service';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

const LOESCHEN_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Feedback löschen?',
  text: 'Das Feedback wird samt Kontakt sofort gelöscht, nicht erst nach der Frist. Das lässt sich nicht rückgängig machen.',
  ja: 'Löschen',
  nein: 'Abbrechen',
};

/**
 * Feedback aus dem Knopf "Feedback" im Kopf (#343), das Neueste zuerst. Ohne
 * Bezug zu einem Konto; einen Kontakt gibt es nur, wenn die Person ihn angab.
 * Admins markieren Feedback als erledigt, nehmen das zurück und löschen es
 * einzeln (#425); die Liste zeigt entweder das offene oder das erledigte.
 */
@Component({
  selector: 'app-feedback-liste',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatDialogModule,
    MatIconModule,
    MatSnackBarModule,
    NachladeHinweisComponent,
  ],
  templateUrl: './feedback-liste.component.html',
  styleUrls: ['./feedback-liste.component.css'],
})
export class FeedbackListeComponent implements OnInit {
  daten: FeedbackListe | null = null;
  fehler = false;
  /** false: offenes Feedback, true: erledigtes. */
  erledigt = false;
  /** Ids, für die gerade eine Anfrage läuft; ihre Knöpfe sind gesperrt. */
  laeuft = new Set<string>();

  constructor(
    private feedbackService: FeedbackService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  private readonly destroyRef = inject(DestroyRef);

  /** Laedt selbst nach, solange der Reiter sichtbar ist (still, ohne die Liste zu leeren). */
  ngOnInit() {
    this.laden();
    // Still, ohne die Liste zu leeren; eine Antwort fuer den anderen Filter zaehlt nicht.
    selbstNachladen(
      () => {
        const erledigt = this.erledigt;
        return this.feedbackService.liste(erledigt, true).pipe(filter(() => erledigt === this.erledigt));
      },
      this.destroyRef,
      {
        next: (daten) => {
          this.daten = daten;
          this.fehler = false;
        },
        error: () => (this.fehler = true),
      }
    );
  }

  filtern(erledigt: boolean) {
    if (erledigt !== this.erledigt) {
      this.erledigt = erledigt;
      this.laden();
    }
  }

  erledigtSetzen(e: FeedbackEintrag, erledigt: boolean) {
    this.laeuft.add(e.id);
    this.feedbackService.erledigtSetzen(e.id, erledigt).subscribe({
      next: () => this.entfernen(e),
      error: () => this.fehlschlag(e, 'Das Feedback konnte nicht geändert werden.'),
    });
  }

  loeschen(e: FeedbackEintrag) {
    this.dialog
      .open(BestaetigungsDialogComponent, { data: LOESCHEN_FRAGE, autoFocus: 'dialog' })
      .afterClosed()
      .pipe(filter((ja) => ja === true))
      .subscribe(() => {
        this.laeuft.add(e.id);
        this.feedbackService.loeschen(e.id).subscribe({
          next: () => this.entfernen(e),
          error: () => this.fehlschlag(e, 'Das Feedback konnte nicht gelöscht werden.'),
        });
      });
  }

  /** JJJJ-MM-TT als TT.MM.JJJJ, ohne Umweg ueber Date und Zeitzone. */
  tag(iso: string): string {
    const [jahr, monat, tag] = iso.split('-');
    return `${tag}.${monat}.${jahr}`;
  }

  private laden() {
    this.daten = null;
    this.fehler = false;
    const erledigt = this.erledigt;
    this.feedbackService.liste(erledigt).subscribe({
      next: (daten) => {
        // Eine Antwort fuer den anderen Filter kommt zu spaet und zaehlt nicht.
        if (erledigt !== this.erledigt) return;
        this.daten = daten;
        this.fehler = false;
      },
      error: () => {
        if (erledigt !== this.erledigt) return;
        this.fehler = true;
      },
    });
  }

  /** Der Eintrag bleibt stehen, seine Knöpfe gehen wieder. */
  private fehlschlag(e: FeedbackEintrag, meldung: string) {
    this.laeuft.delete(e.id);
    this.snackBar.open(meldung, 'OK', { duration: 5000 });
  }

  /** Nach Umschalten oder Löschen gehört der Eintrag nicht mehr in diese Liste. */
  private entfernen(e: FeedbackEintrag) {
    this.laeuft.delete(e.id);
    if (this.daten) {
      this.daten = { ...this.daten, eintraege: this.daten.eintraege.filter((x) => x.id !== e.id) };
    }
  }
}
