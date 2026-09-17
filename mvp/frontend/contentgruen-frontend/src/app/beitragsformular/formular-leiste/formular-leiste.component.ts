import { AfterViewInit, Component, ElementRef, HostListener, Inject, Input, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { DOCUMENT, NgIf } from '@angular/common';

/** Klasse am body, solange eine feste Leiste da ist: haelt unten Platz frei. */
export const FESTE_LEISTE_KLASSE = 'hat-feste-leiste';

/** CSS-Variable am body mit der gemessenen Hoehe der Leiste. */
export const LEISTEN_HOEHE_VARIABLE = '--feste-leiste-hoehe';

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
 *
 * Ein Fehler beim Speichern steht knapp in der Leiste ueber dem Knopf: Die
 * ausfuehrliche Meldung im Formular laege sonst genau hinter ihr. Der body haelt
 * die gemessene Hoehe frei, also auch die der Fehlerzeile.
 */
@Component({
  standalone: true,
  selector: 'app-formular-leiste',
  imports: [NgIf],
  template: `
    <div #leiste class="leiste" [class.leiste--beim-tippen]="tippt">
      <p *ngIf="fehler" class="leiste-fehler" role="alert">{{ fehler }}</p>
      <ng-content></ng-content>
    </div>
  `,
  styles: [`
    .leiste {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 12px;
    }

    /* Am Desktop steht die Meldung direkt darueber im Formular */
    .leiste-fehler {
      display: none;
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

      .leiste-fehler {
        display: block;
        flex-basis: 100%;
        margin: 0;
        padding: 8px 12px;
        border-left: 4px solid var(--error, #d32f2f);
        border-radius: 4px;
        background: rgba(211, 47, 47, 0.08);
        font-size: 0.9rem;
      }

      .leiste ::ng-deep button {
        flex: 1;
        min-height: 48px;
      }
    }
  `],
})
export class FormularLeisteComponent implements OnInit, AfterViewInit, OnDestroy {
  /** Knappe Fehlermeldung ueber dem Knopf, null ohne Fehler. */
  @Input() fehler: string | null = null;
  @ViewChild('leiste') leiste?: ElementRef<HTMLElement>;

  /** Ein Textfeld hat den Fokus. */
  tippt = false;

  private beobachter?: ResizeObserver;

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

  ngAfterViewInit(): void {
    const element = this.leiste?.nativeElement;
    if (!element || typeof ResizeObserver === 'undefined') {
      return;
    }
    // Ausgeblendet (beim Tippen) misst 0 - dann die letzte Hoehe behalten, damit nichts springt.
    this.beobachter = new ResizeObserver(() => {
      const hoehe = element.offsetHeight;
      if (hoehe > 0) {
        this.document.body.style.setProperty(LEISTEN_HOEHE_VARIABLE, `${hoehe}px`);
      }
    });
    this.beobachter.observe(element);
  }

  ngOnDestroy(): void {
    this.beobachter?.disconnect();
    this.document.body.style.removeProperty(LEISTEN_HOEHE_VARIABLE);
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
