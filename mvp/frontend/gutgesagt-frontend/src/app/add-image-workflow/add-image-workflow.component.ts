import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AddImageComponent } from '../add-image/add-image.component';
import { ContentRefreshService } from '../services/content-refresh.service';
import { gespeichertPfad } from '../shared/formular-adresse';
import { BeitragGespeichert, GespeichertZustand } from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';

/**
 * Die Seite unter /workflow/add-image. Nach dem Speichern die Ergebnisseite wie bei
 * Kommentar, Hintergrundinfo und Post (#619); sie ersetzt das Formular im Verlauf.
 */
@Component({
  standalone: true,
  selector: 'app-add-image-workflow',
  templateUrl: './add-image-workflow.component.html',
  styleUrls: ['./add-image-workflow.component.css'],
  imports: [CommonModule, AddImageComponent],
})
export class AddImageWorkflowComponent {
  constructor(
    private router: Router,
    private contentRefreshService: ContentRefreshService,
  ) {}

  onSuccess(ergebnis: BeitragGespeichert): void {
    this.contentRefreshService.triggerRefresh();
    const state: GespeichertZustand = {
      ...(ergebnis.aussage.text ? { aussage: ergebnis.aussage } : {}),
      verknuepft: ergebnis.verknuepft,
      ...(ergebnis.themenHinweis ? { themenHinweis: ergebnis.themenHinweis } : {}),
    };
    this.router.navigate(gespeichertPfad('image', ergebnis.id), { state, replaceUrl: true });
  }
}
