import { AfterViewInit, Component, ElementRef, EventEmitter, Inject, Input, NgZone, OnDestroy, OnInit, Output, ViewChild } from '@angular/core';
import { DOCUMENT, NgIf } from '@angular/common';

/** Klasse am body, solange eine feste Leiste da ist: haelt unten Platz frei. */
export const FESTE_LEISTE_KLASSE = 'hat-feste-leiste';

/** CSS-Variable am Wurzelelement mit der gemessenen Hoehe der Leiste (body-Abstand, scroll-padding). */
export const LEISTEN_HOEHE_VARIABLE = '--feste-leiste-hoehe';

/**
 * Die Leiste mit dem Speichern-Knopf eines Beitragsformulars.
 *
 * Am Handy steht sie fest am unteren Rand. Ohne safe-area-Abstand: der braeuchte
 * viewport-fit=cover und damit Anpassungen an Kopfzeile, FAB und Menue. Fest statt sticky: main hat overflow: hidden, daran klebt
 * position: sticky nicht. Damit sie nichts verdeckt, haelt der body unten Platz
 * frei, solange sie da ist. Der Consent-Hinweis steht darueber im Fluss.
 *
 * Auch beim Tippen bleibt sie stehen, ueber der Bildschirmtastatur (#616): Der
 * sichtbare Ausschnitt (visualViewport) wird kleiner als das Fenster, und die
 * Leiste rueckt um die Differenz nach oben. Damit das fokussierte Feld nicht
 * hinter ihr landet, haelt das Wurzelelement unten scroll-padding in ihrer Hoehe.
 *
 * Ein Fehler beim Speichern steht knapp in der Leiste ueber dem Knopf: Die
 * ausfuehrliche Meldung im Formular laege sonst genau hinter ihr. Ein Hinweis
 * (etwa: Es gibt schon einen sehr aehnlichen) steht dort in Hinweisfarbe statt
 * rot. Der body haelt die gemessene Hoehe frei, also auch die der Meldung.
 */
@Component({
  standalone: true,
  selector: 'app-formular-leiste',
  imports: [NgIf],
  template: `
    <div #leiste class="leiste">
      <p *ngIf="fehler" class="leiste-meldung leiste-fehler" role="alert">
        {{ fehler }}
        <button *ngIf="aktion" type="button" class="leiste-aktion" (click)="aktionGeklickt.emit()">{{ aktion }}</button>
      </p>
      <!-- Ohne role="status": der Kasten im Formular sagt den Hinweis schon an -->
      <p *ngIf="!fehler && hinweis" class="leiste-meldung leiste-hinweis">
        {{ hinweis }}
        <button *ngIf="aktion" type="button" class="leiste-aktion" (click)="aktionGeklickt.emit()">{{ aktion }}</button>
      </p>
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
    .leiste-meldung {
      display: none;
    }

    .leiste-aktion {
      margin-left: 4px;
      padding: 0;
      border: 0;
      background: none;
      color: var(--primary-dark);
      font: inherit;
      text-decoration: underline;
      cursor: pointer;
    }

    @media (max-width: 599px) {
      .leiste {
        position: fixed;
        left: 0;
        right: 0;
        /* Ueber der Bildschirmtastatur: gesetzt aus dem visualViewport */
        bottom: var(--leiste-ueber-tastatur, 0px);
        z-index: 50;
        margin: 0;
        padding: 12px 16px;
        background: var(--bg-card);
        border-top: 1px solid var(--divider-color);
        box-shadow: 0 -2px 6px rgba(0, 0, 0, 0.06);
      }

      .leiste-meldung {
        display: block;
        flex-basis: 100%;
        margin: 0;
        padding: 8px 12px;
        border-left: 4px solid var(--error-color);
        border-radius: 4px;
        background: var(--error-tint);
        font-size: 0.9rem;
      }

      .leiste-hinweis {
        border-left-color: var(--warning-edge);
        background: var(--warning-bg);
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
  /** Knapper Hinweis ueber dem Knopf, kein Fehler (Hinweisfarbe); ein Fehler geht vor. */
  @Input() hinweis: string | null = null;
  /** Optionaler Textlink hinter der Meldung, etwa "Zur Auswahl". */
  @Input() aktion: string | null = null;
  @Output() aktionGeklickt = new EventEmitter<void>();
  @ViewChild('leiste') leiste?: ElementRef<HTMLElement>;

  private beobachter?: ResizeObserver;
  private ausschnittGeaendert = () => this.ueberTastaturSetzen();

  constructor(
    @Inject(DOCUMENT) private document: Document,
    private zone: NgZone,
  ) {}

  ngOnInit(): void {
    this.document.body.classList.add(FESTE_LEISTE_KLASSE);
  }

  ngAfterViewInit(): void {
    const ausschnitt = this.document.defaultView?.visualViewport;
    if (ausschnitt) {
      // Ausserhalb der Zone: Scrollen und Tastatur sollen keine Change Detection ausloesen.
      this.zone.runOutsideAngular(() => {
        ausschnitt.addEventListener('resize', this.ausschnittGeaendert);
        ausschnitt.addEventListener('scroll', this.ausschnittGeaendert);
      });
      // Entsteht die Leiste bei schon offener Tastatur, gleich richtig stehen
      this.ueberTastaturSetzen();
    }
    const element = this.leiste?.nativeElement;
    if (!element || typeof ResizeObserver === 'undefined') {
      return;
    }
    // Am Desktop steht die Leiste im Fluss; die Variable wirkt nur in den Handy-Regeln.
    this.beobachter = new ResizeObserver(() => {
      const hoehe = element.offsetHeight;
      if (hoehe > 0) {
        this.document.documentElement.style.setProperty(LEISTEN_HOEHE_VARIABLE, `${hoehe}px`);
      }
    });
    this.beobachter.observe(element);
  }

  ngOnDestroy(): void {
    const ausschnitt = this.document.defaultView?.visualViewport;
    ausschnitt?.removeEventListener('resize', this.ausschnittGeaendert);
    ausschnitt?.removeEventListener('scroll', this.ausschnittGeaendert);
    this.beobachter?.disconnect();
    this.document.documentElement.style.removeProperty(LEISTEN_HOEHE_VARIABLE);
    this.document.body.classList.remove(FESTE_LEISTE_KLASSE);
  }

  /** Der Abstand vom unteren Fensterrand bis zur Oberkante der Tastatur, 0 ohne Tastatur. */
  private ueberTastaturSetzen(): void {
    const fenster = this.document.defaultView;
    const ausschnitt = fenster?.visualViewport;
    const element = this.leiste?.nativeElement;
    if (!fenster || !ausschnitt || !element) {
      return;
    }
    element.style.setProperty('--leiste-ueber-tastatur', `${ueberTastatur(fenster.innerHeight, ausschnitt)}px`);
  }
}

/**
 * Wie weit die Leiste ueber dem unteren Fensterrand stehen muss, damit sie am
 * unteren Rand des sichtbaren Ausschnitts steht - bei offener Tastatur deren Hoehe.
 */
export function ueberTastatur(fensterHoehe: number, ausschnitt: { height: number; offsetTop: number }): number {
  return Math.max(0, Math.round(fensterHoehe - ausschnitt.height - ausschnitt.offsetTop));
}
