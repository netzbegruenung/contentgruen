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

import { HAND, SCHATTEN, normierteGuete, siegelFarbe, siegelText, siegelWinkel } from './siegel-zeichnung';

/** Wie lange die Funken nach einem Aufstieg im DOM bleiben (ms), etwas länger als ihre Animation. */
const FUNKEN_DAUER_MS = 900;
const FUNKEN_ANZAHL = 9;

let naechsteId = 0;

/**
 * Das Siegel: die kleine Fassung des Logos, die die Güte eines Beitrags zeigt (#416).
 * Ohne Güte (`null`) grau und waagrecht, mit steigender Güte dreht der Daumen nach oben
 * und wird von Grau über Gelb grün. Steigt die Güte, dreht die Hand mit leichtem
 * Überschwingen und es sprühen kurz Funken; bei `prefers-reduced-motion` wechselt nur
 * die Farbe und der Winkel.
 *
 * Glanz (Auszeichnung des Beitrags) und Krone (Auszeichnung der Person) sind Varianten
 * für #351; wer sie wem zeigen darf, entscheidet die einbindende Komponente.
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
  /** Güte 1–10; `null` für einen neuen Beitrag ohne Daten. */
  @Input() guete: number | null = null;
  @Input() glanz = false;
  @Input() krone = false;

  readonly HAND = HAND;
  readonly SCHATTEN = SCHATTEN;
  /** Eindeutig je Siegel: Mehrere Siegel auf einer Seite teilen sich das Dokument. */
  readonly glanzId = `siegel-glanz-${naechsteId++}`;

  /** Funken des letzten Aufstiegs; leer, solange keiner läuft. */
  funken: { dx: number; dy: number }[] = [];
  private funkenTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private readonly cdr: ChangeDetectorRef) {}

  get winkel(): number {
    return siegelWinkel(this.guete);
  }

  get farbe(): string {
    return siegelFarbe(this.guete);
  }

  get text(): string {
    return siegelText(this.guete);
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
