import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  QueryList,
  ViewChildren,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

/**
 * Aussagekarte: eine unbeantwortete Aussage als Karte im Stil der Beitragskarte
 * (Kopfband, Koerper, Fuss mit "Antworten"). Inhalte erscheinen als Karten; die
 * Beitragskarte gibt es fuer Beitraege und Einwuerfe, diese hier fuer Aussagen.
 * Zusaetzliches im Koerper (etwa die Themen) kommt per Content Projection.
 * Mehrere Karten stehen in einer ul.aussagekarten (aussagekarten.scss).
 *
 * Der Titel ist eine Ueberschrift (ebene: h2 oder h3, je nach Seite) und zeigt
 * zugeklappt hoechstens vier Zeilen; "Ganz lesen" erscheint nur, wenn etwas fehlt.
 * Gekuerzt wird nur sichtbar: Screenreader hoeren ueber aria-describedby am
 * Knopf immer den vollen Text.
 */
/**
 * Merkt sich ein Ergebnis je statement_id, etwa die Query-Parameter von "Antworten":
 * Ein neues Objekt bei jedem Durchlauf liesse OnPush in der Karte ins Leere laufen.
 * Haengt das Ergebnis noch an mehr als der ID (etwa der Nachfrage), nennt `schluessel`
 * das mit, sonst bliebe nach dem Nachladen der alte Wert stehen.
 */
export function jeAussage<A extends { statement_id: string }, E>(
  bilden: (aussage: A) => E,
  schluessel: (aussage: A) => string = (aussage) => aussage.statement_id,
): (aussage: A) => E {
  const gemerkt = new Map<string, E>();
  return (aussage) => {
    const s = schluessel(aussage);
    let wert = gemerkt.get(s);
    if (wert === undefined) {
      wert = bilden(aussage);
      gemerkt.set(s, wert);
    }
    return wert;
  };
}

@Component({
  selector: 'app-aussagekarte',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './aussagekarte.component.html',
  styleUrls: ['./aussagekarte.component.scss'],
})
export class AussagekarteComponent implements AfterViewInit, OnChanges, OnDestroy {
  /** Text der Aussage, steht als Titel im Kopfband. */
  @Input({ required: true }) text = '';
  /** Id des Titels; Karte (aria-labelledby) und "Antworten" (aria-describedby) verweisen darauf. */
  @Input({ required: true }) titelId = '';
  /** Ueberschriftenebene des Titels: 2 direkt unter dem Seitentitel, 3 unter einer Abschnittsueberschrift. */
  @Input() ebene: 2 | 3 = 2;
  /** "haupt": gefuellter Hauptknopf; "neben", wo die Seite schon einen Hauptknopf hat. */
  @Input() knopf: 'haupt' | 'neben' = 'haupt';
  /** Nachfrage, etwa "3 Personen suchten das ohne Treffer"; leer = keine Zeile. */
  @Input() gesucht = '';
  /** Ziel von "Antworten" (Kommentarformular) samt Query-Parametern. */
  @Input({ required: true }) antwortenPfad = '';
  @Input() antwortenParams: Record<string, string> = {};

  @ViewChildren('titel') private titel!: QueryList<ElementRef<HTMLElement>>;

  aufgeklappt = false;
  gekuerzt = false;
  private beobachter?: ResizeObserver;

  constructor(
    private readonly cdr: ChangeDetectorRef,
    private readonly zone: NgZone,
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    // Anderer Text: nach dem Rendern neu messen, ob "Ganz lesen" noch gebraucht wird
    if (changes['text'] && !changes['text'].firstChange) {
      this.spaeterMessen();
    }
  }

  ngAfterViewInit(): void {
    const element = this.titel.first?.nativeElement;
    if (!element) {
      return;
    }
    this.messen(element);
    if (typeof ResizeObserver !== 'undefined') {
      this.beobachter = new ResizeObserver(() => this.zone.run(() => this.messen(element)));
      this.beobachter.observe(element);
    }
  }

  ngOnDestroy(): void {
    this.beobachter?.disconnect();
  }

  umschalten(): void {
    this.aufgeklappt = !this.aufgeklappt;
    this.cdr.markForCheck();
    // Waehrend die Aussage offen war, kann das Fenster breiter geworden sein:
    // nach dem Zuklappen neu messen, sonst bliebe "Ganz lesen" grundlos stehen.
    if (!this.aufgeklappt) {
      this.spaeterMessen();
    }
  }

  /** Nach dem naechsten Rendern messen, wie fassungWaehlen in der Beitragskarte. */
  private spaeterMessen(): void {
    requestAnimationFrame(() =>
      this.zone.run(() => {
        const element = this.titel?.first?.nativeElement;
        if (element) {
          this.messen(element);
        }
      }),
    );
  }

  /** Zugeklappt fehlt etwas, wenn der Text hoeher ist als die vier sichtbaren Zeilen. */
  private messen(element: HTMLElement): void {
    if (this.aufgeklappt) {
      return;
    }
    const gekuerzt = element.scrollHeight > element.clientHeight + 1;
    if (gekuerzt !== this.gekuerzt) {
      this.gekuerzt = gekuerzt;
      this.cdr.markForCheck();
    }
  }
}
