import { ChangeDetectionStrategy, Component, Input, OnDestroy, OnInit, inject } from '@angular/core';
import { AsyncPipe, NgIf } from '@angular/common';
import { AbstractControl } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { map } from 'rxjs/operators';

import { zurEinwilligungFuehren } from '../services/art9-einwilligung.service';
import { Art9EinwilligungZustand } from '../services/art9-einwilligung-zustand';

/** Unter diesem Praefix plus Adresse der Seite liegt eine begonnene Eingabe, solange die Person einwilligt. */
export const ENTWURF_PRAEFIX = 'gutgesagt-entwurf-vor-einwilligung:';

export const EINWILLIGUNG_HINWEIS_TITEL = 'Zum Beitragen brauchst du deine Einwilligung.';
export const EINWILLIGUNG_HINWEIS_TEXT =
  'Suchen und Lesen geht auch ohne. Was du hier schon eingegeben hast, bleibt stehen, bis du zurück bist.';
export const EINWILLIGUNG_HINWEIS_KNOPF = 'Einwilligen';

/**
 * Der Hinweiskasten über einem Formular, wenn die Art.-9-Einwilligung fehlt (UX-Review
 * B4): erklärt, warum hier nichts gespeichert wird, und führt mit „Einwilligen“ auf
 * /einwilligung und danach zurück. Die bis dahin getippte Eingabe von ``formular``
 * legt er in den sessionStorage und setzt sie beim Zurückkommen wieder ein; ohne
 * Speicher geht nur die Eingabe verloren, der Weg klappt trotzdem.
 *
 * Solange der Kasten auf der Seite ist, zeigt der Interceptor bei einem 403 keinen
 * zweiten Hinweis als Snackbar; die Formulare zeigen dann auch keine Fehlermeldung.
 */
@Component({
  selector: 'app-einwilligung-hinweis',
  standalone: true,
  imports: [NgIf, AsyncPipe, MatButtonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div *ngIf="zeigen$ | async" class="hinweis-box einwilligung-hinweis" role="status" data-testid="einwilligung-hinweis">
      <p>
        <strong>{{ titel }}</strong>
        {{ text }}
      </p>
      <button mat-raised-button color="primary" type="button" class="einwilligen" (click)="einwilligen()">
        {{ knopf }}
      </button>
    </div>
  `,
  styles: [
    `
      .einwilligung-hinweis {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }
      .einwilligung-hinweis p {
        flex: 1 1 240px;
      }
    `,
  ],
})
export class EinwilligungHinweisComponent implements OnInit, OnDestroy {
  /** Das Formular, dessen Eingabe den Umweg über die Einwilligung übersteht. */
  @Input() formular?: AbstractControl | null;

  readonly titel = EINWILLIGUNG_HINWEIS_TITEL;
  readonly text = EINWILLIGUNG_HINWEIS_TEXT;
  readonly knopf = EINWILLIGUNG_HINWEIS_KNOPF;
  private readonly zustand = inject(Art9EinwilligungZustand);
  private readonly router = inject(Router);
  readonly zeigen$ = this.zustand.zustand$.pipe(map((zustand) => zustand === 'fehlt'));
  private abmelden?: () => void;

  ngOnInit(): void {
    this.abmelden = this.zustand.hinweisAnmelden();
    this.entwurfEinsetzen();
  }

  ngOnDestroy(): void {
    this.abmelden?.();
  }

  einwilligen(): void {
    this.entwurfSichern();
    zurEinwilligungFuehren(this.router);
  }

  private get schluessel(): string {
    return ENTWURF_PRAEFIX + (this.router.url ?? '/');
  }

  private entwurfSichern(): void {
    if (!this.formular) return;
    try {
      sessionStorage.setItem(this.schluessel, JSON.stringify(this.formular.getRawValue()));
    } catch {
      // Ohne Speicher geht nur die Eingabe verloren; der Weg zur Einwilligung klappt.
    }
  }

  /** Nur nicht leere Werte: Was die Seite selbst vorbelegt hat, bleibt sonst stehen. */
  private entwurfEinsetzen(): void {
    if (!this.formular) return;
    let gelesen: unknown;
    try {
      const wert = sessionStorage.getItem(this.schluessel);
      if (!wert) return;
      sessionStorage.removeItem(this.schluessel);
      gelesen = JSON.parse(wert);
    } catch {
      return;
    }
    if (gelesen !== null && typeof gelesen === 'object' && !Array.isArray(gelesen)) {
      const nichtLeer = Object.fromEntries(
        Object.entries(gelesen as Record<string, unknown>).filter(([, v]) => !leer(v)),
      );
      this.formular.patchValue(nichtLeer);
    } else if (!leer(gelesen)) {
      this.formular.setValue(gelesen);
    }
  }
}

function leer(wert: unknown): boolean {
  return wert === null || wert === undefined || wert === '' || (Array.isArray(wert) && wert.length === 0);
}
