import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AddPostComponent } from '../add-post/add-post.component';
import { LoggingService } from '../services/logging.service';
import { ContentRefreshService } from '../services/content-refresh.service';
import { gespeichertPfad } from '../shared/formular-adresse';
import { BeitragGespeichert, GespeichertZustand } from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';
import { DestillierUebergabeService, Vorbefuellung } from '../destillieren/destillier-uebergabe.service';
import { EINWURF_PARAM } from '../destillieren/einwurf-adresse';

/**
 * Die Seite unter /workflow/add-post: verfassen oder, mit der ID eines Einwurfs
 * in der Adresse, aus dem Fangkorb ausformulieren. Dann kommen Satz und Link aus dem Einwurf, und
 * nach dem Speichern wird er mit dem Post verknuepft.
 *
 * Nach dem Speichern immer die Ergebnisseite; sie ersetzt das Formular im Verlauf.
 */
@Component({
  standalone: true,
  selector: 'app-add-post-workflow',
  templateUrl: './add-post-workflow.component.html',
  styleUrls: ['./add-post-workflow.component.css'],
  imports: [CommonModule, AddPostComponent],
})
export class AddPostWorkflowComponent implements OnInit {
  private destroyRef = inject(DestroyRef);
  /** Gesetzt, wenn das Formular aus dem Destillier-Ablauf geoeffnet wurde. */
  einwurfId: string | null = null;
  vorbefuellung: Vorbefuellung | null = null;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private logger: LoggingService,
    private contentRefreshService: ContentRefreshService,
    private uebergabe: DestillierUebergabeService,
  ) {}

  ngOnInit(): void {
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => this.einwurfUebernehmen(params.get(EINWURF_PARAM)));
  }

  private einwurfUebernehmen(einwurfId: string | null): void {
    if (einwurfId === this.einwurfId) {
      return;
    }
    this.einwurfId = einwurfId;
    this.vorbefuellung = null;
    if (einwurfId) {
      this.uebergabe.vorbefuellungLaden(einwurfId).subscribe({
        next: (vorbefuellung) => (this.vorbefuellung = vorbefuellung),
        error: (error) => this.logger.error('Einwurf fuer die Vorbefuellung nicht ladbar', error),
      });
    }
  }

  onSuccess(ergebnis: BeitragGespeichert): void {
    this.contentRefreshService.triggerRefresh();

    if (this.einwurfId) {
      const einwurfId = this.einwurfId;
      this.uebergabe
        .mitBeitragVerknuepfen(einwurfId, ergebnis.id, 'post')
        .subscribe((einwurfVerknuepft) =>
          this.zurErgebnisseite(ergebnis.id, { [EINWURF_PARAM]: einwurfId }, { einwurfVerknuepft }),
        );
      return;
    }
    this.zurErgebnisseite(ergebnis.id, {}, {});
  }

  private zurErgebnisseite(id: string, queryParams: Record<string, string>, state: GespeichertZustand): void {
    this.router.navigate(gespeichertPfad('post', id), { queryParams, state, replaceUrl: true });
  }
}
