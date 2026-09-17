import { Component, HostListener, Inject, OnDestroy, OnInit } from '@angular/core';
import { DOCUMENT } from '@angular/common';

/** Klasse am body, solange eine feste Leiste da ist: haelt unten Platz frei. */
export const FESTE_LEISTE_KLASSE = 'hat-feste-leiste';

/**
 * Die Leiste mit dem Speichern-Knopf eines Beitragsformulars.
 *
 * Am Handy steht sie fest am unteren Rand. Ohne safe-area-Abstand: der braeuchte
 * viewport-fit=cover und damit Anpassungen an Kopfzeile, FAB und Menue. Fest statt sticky: main hat overflow: hidden, daran klebt
 * position: sticky nicht. Damit sie nichts verdeckt, haelt der body unten Platz
 * frei, solange sie da ist. Der Consent-Hinweis steht darueber im Fluss.
 *
 * Solange ein Textfeld den Fokus hat, blendet sie sich am Handy aus: Die
 * Tastatur nimmt dann ohnehin die halbe Hoehe, und die Leiste saesse direkt ueber
 * dem Feld, in das man tippt.
 */
@Component({
  standalone: true,
  selector: 'app-formular-leiste',
  template: `<div class="leiste" [class.leiste--beim-tippen]="tippt"><ng-content></ng-content></div>`,
  styles: [`
    .leiste {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 12px;
    }

    @media (max-width: 599px) {
      .leiste {
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 50;
        margin: 0;
        padding: 12px 16px;
        background: white;
        border-top: 1px solid var(--divider-color);
        box-shadow: 0 -2px 6px rgba(0, 0, 0, 0.06);
      }

      .leiste--beim-tippen {
        display: none;
      }

      .leiste ::ng-deep button {
        flex: 1;
        min-height: 48px;
      }
    }
  `],
})
export class FormularLeisteComponent implements OnInit, OnDestroy {
  /** Ein Textfeld hat den Fokus. */
  tippt = false;

  constructor(@Inject(DOCUMENT) private document: Document) {}

  ngOnInit(): void {
    this.document.body.classList.add(FESTE_LEISTE_KLASSE);
  }

  @HostListener('document:focusin', ['$event'])
  fokusRein(event: FocusEvent): void {
    this.tippt = istTextfeld(event.target);
  }

  @HostListener('document:focusout', ['$event'])
  fokusRaus(event: FocusEvent): void {
    // relatedTarget: wohin der Fokus geht - von Feld zu Feld bleibt die Leiste weg.
    this.tippt = istTextfeld(event.relatedTarget);
  }

  ngOnDestroy(): void {
    this.document.body.classList.remove(FESTE_LEISTE_KLASSE);
  }
}

const KEIN_TEXT = new Set(['button', 'checkbox', 'radio', 'submit', 'reset', 'file', 'range', 'color']);

function istTextfeld(ziel: EventTarget | null): boolean {
  if (ziel instanceof HTMLTextAreaElement) {
    return true;
  }
  if (ziel instanceof HTMLInputElement) {
    return !KEIN_TEXT.has(ziel.type);
  }
  return ziel instanceof HTMLElement && ziel.isContentEditable;
}
