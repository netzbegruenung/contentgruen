import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleChange, MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ModerationService, Schalter, SchalterListe } from '../../services/moderation.service';
import { ohneRechte, selbstNachladen } from '../../shared/selbst-nachladen';

/** Anzeigenamen der Schalter; unbekannte zeigen ihren technischen Namen. */
const TITEL: Record<string, string> = {
  punkte: 'Punkte und Meilensteine',
  abzeichen_sichtbar: 'Abzeichen am Anzeigenamen',
  gepostet: 'Rückfrage „Ja, gepostet“',
};

/**
 * Schalter (#708, Glossar „Schalter“): je Schalter Erklärung, ob der Server ihn erlaubt
 * (Obergrenze aus der Umgebung) und der Admin-Wert als Umschalter. Wirksam ist er nur mit
 * beidem. Ist die Obergrenze aus, ist der Umschalter gesperrt. Die Seite lädt selbst nach,
 * nach dem Umschalten aus der Antwort des Servers.
 */
@Component({
  selector: 'app-schalter',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule, MatSlideToggleModule, MatSnackBarModule],
  template: `
    <h2>Schalter</h2>
    <p class="hinweis">
      Ein Schalter wirkt nur, wenn der Server ihn erlaubt und er hier eingeschaltet ist. Ohne Eintrag hier ist er aus.
    </p>

    <div *ngIf="liste === null" class="laedt" role="status">
      <mat-spinner diameter="32"></mat-spinner>
      <span>{{ fehler ? 'Schalter gerade nicht erreichbar, neuer Versuch in Kürze …' : 'Lade Schalter …' }}</span>
    </div>

    <ng-container *ngIf="liste !== null">
      <div *ngIf="fehler" class="laedt klein" role="status">
        <mat-spinner diameter="16"></mat-spinner>
        <span>Aktualisieren gerade nicht möglich, neuer Versuch in Kürze …</span>
      </div>
      <section *ngFor="let s of liste" class="schalter mat-elevation-z1" data-testid="schalter">
        <div class="kopf">
          <h3>{{ titel(s) }}</h3>
          <mat-slide-toggle
            [checked]="s.admin_wert"
            [disabled]="!s.obergrenze && !s.admin_wert || setzend !== null"
            [aria-label]="titel(s) + ', Admin'"
            [aria-describedby]="'zustand-' + s.name"
            (change)="umschalten(s, $event)"
          >
            Admin
          </mat-slide-toggle>
        </div>
        <p class="zustand" [id]="'zustand-' + s.name" [class.wirkt]="s.wirksam" data-testid="zustand">
          {{ zustand(s) }}
        </p>
        <p>{{ s.erklaerung }}</p>
        <p class="obergrenze" [class.aus]="!s.obergrenze">
          <mat-icon aria-hidden="true">{{ s.obergrenze ? 'check_circle' : 'block' }}</mat-icon>
          Server erlaubt: {{ s.obergrenze ? 'ja' : 'nein' }}
          <code>{{ s.umgebungsvariable }}</code>
        </p>
        <p *ngIf="!s.obergrenze" class="gesperrt" data-testid="gesperrt">
          Gesperrt: Erst wenn der Server ihn erlaubt, lässt er sich hier einschalten.
        </p>
        <p *ngIf="s.dsfa_hinweis" class="dsfa" data-testid="dsfa-hinweis">
          <mat-icon aria-hidden="true">gavel</mat-icon>
          {{ s.dsfa_hinweis }}
        </p>
      </section>
    </ng-container>
  `,
  styles: [`
    h2 { margin: 0 0 8px; }
    .hinweis { margin: 0 0 16px; }
    .laedt { display: flex; align-items: center; gap: 12px; margin: 16px 0; }
    .laedt.klein { margin: 0 0 8px; font-size: 0.875rem; color: var(--text-leise); }
    /* Karte wie die Beitragskarten: Kopf als Band in Klee-zart, Titel fett (Admin-Design 21.11.) */
    .schalter { overflow: hidden; padding: 0 0 12px; margin-bottom: 12px; overflow-wrap: anywhere; background: var(--flaeche); }
    .schalter p { margin: 4px 16px; }
    .kopf {
      display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
      min-height: 48px; margin-bottom: 8px; padding: 4px 8px 4px 16px; background: var(--karte-kommentar);
    }
    .kopf h3 { margin: 0; font-family: inherit; font-size: 17px; font-weight: 700; color: var(--akzent-schrift); }
    .zustand { font-weight: 500; color: var(--text-leise); }
    .zustand.wirkt { color: inherit; }
    .obergrenze, .dsfa { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
    .obergrenze code { font-size: 0.8125rem; color: var(--text-leise); }
    .obergrenze.aus, .gesperrt { color: var(--text-leise); }
    .schalter .dsfa {
      align-items: flex-start; flex-wrap: nowrap; margin-top: 8px; padding: 8px 12px;
      font-size: 0.875rem; background: var(--hinweis-tint); color: var(--text); border-radius: var(--border-radius-medium);
    }
    .dsfa mat-icon { flex-shrink: 0; font-size: 20px; width: 20px; height: 20px; color: var(--hinweis-text); }
  `],
})
export class SchalterComponent implements OnInit {
  /** null: noch nie geladen. */
  liste: Schalter[] | null = null;
  fehler = false;
  /** Name des Schalters, der gerade gesetzt wird. */
  setzend: string | null = null;

  private readonly destroyRef = inject(DestroyRef);
  private readonly moderation = inject(ModerationService);
  private readonly snackBar = inject(MatSnackBar);

  ngOnInit(): void {
    const folgen = {
      next: (daten: SchalterListe) => this.uebernehmen(daten),
      error: () => (this.fehler = true),
    };
    this.moderation.getSchalter().subscribe(folgen);
    selbstNachladen(() => this.moderation.getSchalter(true), this.destroyRef, folgen, { aufhoerenBei: ohneRechte });
  }

  titel(s: Schalter): string {
    return TITEL[s.name] ?? s.name;
  }

  /**
   * Admin-Wert und Wirkung in einer Zeile, damit ein eingeschalteter Umschalter neben
   * „aus“ nicht widersprüchlich aussieht: Der Umschalter zeigt den Admin-Wert, die Zeile
   * sagt, ob und warum er nicht wirkt.
   */
  zustand(s: Schalter): string {
    const admin = `Admin: ${s.admin_wert ? 'an' : 'aus'}`;
    if (s.wirksam) {
      return `${admin} · wirksam: an`;
    }
    if (s.admin_wert && !s.obergrenze) {
      return `${admin} · wirksam: aus (Server erlaubt nicht)`;
    }
    const punkte = this.liste?.find((p) => p.name === 'punkte');
    if (s.admin_wert && s.name === 'abzeichen_sichtbar' && punkte && !punkte.wirksam) {
      return `${admin} · wirksam: aus, weil Punkte aus`;
    }
    return `${admin} · wirksam: aus`;
  }

  umschalten(s: Schalter, ereignis: MatSlideToggleChange): void {
    this.setzend = s.name;
    this.moderation.schalterSetzen(s.name, ereignis.checked).subscribe({
      next: (daten) => {
        this.setzend = null;
        this.uebernehmen(daten);
      },
      error: (fehler: { status?: number; error?: { detail?: string } }) => {
        this.setzend = null;
        // Umschalter auf den Stand des Servers zurück
        ereignis.source.checked = s.admin_wert;
        const text =
          fehler?.status === 409 && fehler.error?.detail
            ? fehler.error.detail
            : 'Schalter nicht gesetzt, bitte gleich noch einmal versuchen.';
        this.snackBar.open(text, 'OK', { duration: 6000 });
      },
    });
  }

  private uebernehmen(daten: SchalterListe): void {
    this.liste = daten.schalter;
    this.fehler = false;
  }
}
