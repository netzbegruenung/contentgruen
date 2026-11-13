import { ChangeDetectionStrategy, Component, ElementRef, Input, NgZone, OnDestroy, OnInit, inject } from '@angular/core';
import { AsyncPipe, NgIf } from '@angular/common';
import { AbstractControl } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { map } from 'rxjs/operators';

import { zurEinwilligungFuehren } from '../services/art9-einwilligung.service';
import { Art9EinwilligungZustand } from '../services/art9-einwilligung-zustand';
import { entwurfHolen, entwurfSichern as entwurfAblegen } from './entwurf-vor-einwilligung';


export const EINWILLIGUNG_HINWEIS_TITEL = 'Zum Beitragen brauchst du deine Einwilligung.';
export const EINWILLIGUNG_HINWEIS_TEXT =
  'Suchen und Lesen geht auch ohne. Was du hier schon eingegeben hast, bleibt stehen, bis du zurück bist.';
export const EINWILLIGUNG_HINWEIS_KNOPF = 'Einwilligen';

/**
 * Der Hinweiskasten über einem Formular, wenn die Art.-9-Einwilligung fehlt (UX-Review
 * B4): erklärt, warum hier nichts gespeichert wird, und führt mit „Einwilligen“ auf
 * /einwilligung und danach zurück. Die bis dahin getippte Eingabe von ``formular``
 * hält er im Arbeitsspeicher (entwurf-vor-einwilligung.ts) und setzt sie beim
 * Zurückkommen wieder ein; nur ein Neuladen dazwischen verliert sie.
 *
 * Solange der Kasten auf der Seite ist, zeigt der Interceptor bei einem 403 keinen
 * zweiten Hinweis als Snackbar; die Formulare zeigen dann auch keine Fehlermeldung.
 * Stattdessen holt der Kasten sich in den Blick, wenn eine Aktion der Person (Absenden,
 * Weiter) an der fehlenden Einwilligung scheitert (Review zu #670): Auf langen
 * Formularen steht er sonst ausser Sicht, und Absenden taete scheinbar nichts. Den Fokus
 * nimmt er nur, wenn er nicht in einem Eingabefeld steht; Speichern im Hintergrund
 * holt ihn nie (``hinweisZeigen`` rufen nur die Formulare bei einer Aktion).
 */
@Component({
  selector: 'app-einwilligung-hinweis',
  standalone: true,
  imports: [NgIf, AsyncPipe, MatButtonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div *ngIf="zeigen$ | async" class="hinweis-box einwilligung-hinweis" role="status" tabindex="-1"
         data-testid="einwilligung-hinweis">
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
      .einwilligung-hinweis:focus-visible {
        outline: 2px solid var(--akzent-tanne);
        outline-offset: 2px;
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
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly zone = inject(NgZone);
  readonly zeigen$ = this.zustand.zustand$.pipe(map((zustand) => zustand === 'fehlt'));
  private abmelden?: () => void;
  private blickAbo?: { unsubscribe(): void };

  ngOnInit(): void {
    this.abmelden = this.zustand.hinweisAnmelden();
    this.blickAbo = this.zustand.hinweisInDenBlick$.subscribe(() => this.inDenBlick());
    this.entwurfEinsetzen();
  }

  ngOnDestroy(): void {
    this.abmelden?.();
    this.blickAbo?.unsubscribe();
  }

  /**
   * Den Kasten zeigen und fokussieren. Nach dem Rendern: Er kann mit demselben 403 erst
   * entstanden sein.
   */
  private inDenBlick(): void {
    setTimeout(() =>
      this.zone.run(() => {
        const kasten = this.host.nativeElement.querySelector<HTMLElement>('.einwilligung-hinweis');
        if (!kasten) return;
        kasten.scrollIntoView?.({ block: 'center', behavior: 'smooth' });
        if (!imEingabefeld()) kasten.focus({ preventScroll: true });
      }),
    );
  }

  einwilligen(): void {
    this.entwurfSichern();
    zurEinwilligungFuehren(this.router);
  }

  private get kennung(): string | null {
    return this.zustand.kennung;
  }

  private get adresse(): string {
    return this.router.url ?? '/';
  }

  private entwurfSichern(): void {
    if (this.formular) entwurfAblegen(this.adresse, this.formular.getRawValue(), this.kennung);
  }

  /** Nur nicht leere Werte: Was die Seite selbst vorbelegt hat, bleibt sonst stehen. */
  private entwurfEinsetzen(): void {
    if (!this.formular) return;
    const gelesen = entwurfHolen(this.adresse, this.kennung);
    if (gelesen === undefined) return;
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

/** Steht der Fokus gerade in einem Feld, in das die Person tippt? */
function imEingabefeld(): boolean {
  const el = document.activeElement as HTMLElement | null;
  if (!el) return false;
  return el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName);
}

function leer(wert: unknown): boolean {
  return wert === null || wert === undefined || wert === '' || (Array.isArray(wert) && wert.length === 0);
}
