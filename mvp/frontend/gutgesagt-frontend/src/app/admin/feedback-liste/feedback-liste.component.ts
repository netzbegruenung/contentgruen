import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { FeedbackListe, FeedbackService } from '../../shared/feedback/feedback.service';

/**
 * Feedback aus dem Knopf "Feedback" im Kopf (#343), das Neueste zuerst. Ohne
 * Bezug zu einem Konto; einen Kontakt gibt es nur, wenn die Person ihn angab.
 */
@Component({
  selector: 'app-feedback-liste',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule],
  templateUrl: './feedback-liste.component.html',
  styleUrls: ['./feedback-liste.component.css'],
})
export class FeedbackListeComponent implements OnInit {
  daten: FeedbackListe | null = null;
  fehler = false;

  constructor(private feedbackService: FeedbackService) {}

  ngOnInit() {
    this.feedbackService.liste().subscribe({
      next: (daten) => (this.daten = daten),
      error: () => (this.fehler = true),
    });
  }

  /** JJJJ-MM-TT als TT.MM.JJJJ, ohne Umweg ueber Date und Zeitzone. */
  tag(iso: string): string {
    const [jahr, monat, tag] = iso.split('-');
    return `${tag}.${monat}.${jahr}`;
  }
}
