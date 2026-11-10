import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { HAND, SCHATTEN } from '../../marke/hand';
import { normierteGuete, siegelFarbe, siegelText, siegelWinkel } from './siegel-zeichnung';

/** Wie lange die Funken nach einem Aufstieg im DOM bleiben (ms), etwas länger als ihre Animation. */
const FUNKEN_DAUER_MS = 900;
const FUNKEN_ANZAHL = 9;

let naechsteId = 0;

/**
 * Das Siegel: die kleine Fassung des Logos, die die Güte eines Beitrags zeigt (#416).
 * Ohne Güte (`null`) grau und waagrecht, mit steigender Güte dreht der Daumen nach oben
 * und wird von Grau über Gelb tannengrün. Steigt die Güte, dreht die Hand mit leichtem
 * Überschwingen und es sprühen kurz Funken; bei `prefers-reduced-motion` wechselt nur
 * die Farbe und der Winkel.
 *
 * Glanz (der Beitrag hat viel Wirkung) und Krone (Auszeichnung der Person) sind eigene
 * Abzeichen, keine Stufen der Güte: Sie können bei jeder Güte auftreten, auch bei „neu“
 * (vergeben in #351). Wer sie wem zeigen darf, entscheidet die einbindende Komponente.
 *
 * Die Größe setzt die einbindende Komponente über `width` am Element (Standard 24 px).
 */
@Component({
  selector: 'app-siegel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './siegel.component.html',
  styleUrls: ['./siegel.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[class.springt]': 'funken.length > 0' },
})
export class SiegelComponent implements OnChanges, OnDestroy {
  /** Güte 1–10; `null` (oder 0) für einen neuen Beitrag ohne Daten. */
  @Input() guete: number | null = null;
  /** Abzeichen: Der Beitrag hat viel Wirkung (#351). Unabhängig von der Güte. */
  @Input() glanz = false;
  /** Abzeichen: Auszeichnung der Person (#351). Unabhängig von der Güte. */
  @Input() krone = false;

  readonly HAND = HAND;
  readonly SCHATTEN = SCHATTEN;
  /** Eindeutig je Siegel: Mehrere Siegel auf einer Seite teilen sich das Dokument. */
  readonly glanzId = `siegel-glanz-${naechsteId++}`;

  /** Funken des letzten Aufstiegs; leer, solange keiner läuft. */
  funken: { dx: number; dy: number }[] = [];
  private funkenTimer: ReturnType<typeof setTimeout> | null = null;

  /** Dunkelmodus des Geräts (#588): Das Siegel endet dann in Klee statt Tannengrün. */
  private dunkel = false;
  private readonly dunkelAbfrage: MediaQueryList | null =
    typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  private readonly dunkelGeaendert = (e: MediaQueryListEvent): void => {
    this.dunkel = e.matches;
    this.cdr.markForCheck();
  };

  constructor(private readonly cdr: ChangeDetectorRef) {
    this.dunkel = this.dunkelAbfrage?.matches ?? false;
    this.dunkelAbfrage?.addEventListener?.('change', this.dunkelGeaendert);
  }

  get winkel(): number {
    return siegelWinkel(this.guete);
  }

  get farbe(): string {
    return siegelFarbe(this.guete, this.dunkel);
  }

  get text(): string {
    return siegelText(this.guete, this.glanz, this.krone);
  }

  ngOnChanges(changes: SimpleChanges): void {
    const aenderung = changes['guete'];
    if (!aenderung || aenderung.firstChange) return;
    const vorher = normierteGuete(aenderung.previousValue) ?? 0;
    const jetzt = normierteGuete(aenderung.currentValue) ?? 0;
    if (jetzt > vorher && !this.bewegungReduziert()) this.funkeln();
  }

  ngOnDestroy(): void {
    if (this.funkenTimer) clearTimeout(this.funkenTimer);
    this.dunkelAbfrage?.removeEventListener?.('change', this.dunkelGeaendert);
  }

  private funkeln(): void {
    if (this.funkenTimer) clearTimeout(this.funkenTimer);
    this.funken = Array.from({ length: FUNKEN_ANZAHL }, (_, i) => {
      const richtung = (i / FUNKEN_ANZAHL) * 2 * Math.PI;
      return { dx: Math.round(Math.cos(richtung) * 300), dy: Math.round(Math.sin(richtung) * 300) };
    });
    this.funkenTimer = setTimeout(() => {
      this.funken = [];
      this.funkenTimer = null;
      this.cdr.markForCheck();
    }, FUNKEN_DAUER_MS);
  }

  private bewegungReduziert(): boolean {
    return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
}
