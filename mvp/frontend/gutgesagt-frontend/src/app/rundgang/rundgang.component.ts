import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostBinding,
  HostListener,
  NgZone,
  OnDestroy,
  ViewChild,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { A11yModule } from '@angular/cdk/a11y';
import { RundgangService, RundgangStand } from './rundgang.service';
import { RundgangSchritt, jeGeraet } from './rundgang-daten';

/** Wie lange ein Schritt auf sein Ziel wartet (Seite laden, Suche läuft), bevor er ohne Lichtkegel erscheint. */
export const ZIEL_WARTEZEIT_MS = 6000;
const ZIEL_TAKT_MS = 100;
/** Abstand des Lichtkegels um das Ziel und der Sprechblase zum Rand. */
const POLSTER = 8;
const RAND = 12;
const ABSTAND = 16;

interface Kasten {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Mobile Sprechblase als Karte am unteren Rand (Klickdummy: 390 px breit). */
const SCHMAL = '(max-width: 599px)';
/** Ab hier zeigt die App den mobilen Kopf mit Menü statt der Knöpfe (app.component.ts). */
const KOPF_MOBIL = '(max-width: 959px)';
const RUHIG = '(prefers-reduced-motion: reduce)';

function passt(query: string): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(query).matches;
}

/**
 * Der laufende Rundgang (#389): Ein Lichtkegel hebt das echte Element hervor, daneben
 * (mobil: am unteren Rand) eine Sprechblase mit Weiter, Zurück und Beenden. Die Seite
 * darunter ist gesperrt, der Fokus bleibt in der Sprechblase, Escape beendet,
 * Pfeiltasten blättern. Was gezeigt wird, steht in rundgang-daten.ts.
 */
@Component({
  selector: 'app-rundgang',
  standalone: true,
  imports: [A11yModule],
  templateUrl: './rundgang.component.html',
  styleUrls: ['./rundgang-knoepfe.css', './rundgang.component.css'],
})
export class RundgangComponent implements OnDestroy {
  private readonly rundgang = inject(RundgangService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly zone = inject(NgZone);

  @ViewChild('blase') blase?: ElementRef<HTMLElement>;

  /** Der angezeigte Schritt; erst gesetzt, wenn sein Ziel gefunden (oder die Wartezeit um) ist. */
  readonly stand = signal<RundgangStand | null>(null);
  readonly kegel = signal<Kasten | null>(null);
  readonly blasenOrt = signal<{ left?: number; top?: number }>({});
  readonly pfeil = signal<{ seite: 'oben' | 'links' | 'unten'; versatz: number } | null>(null);
  /** Text für Screenreader, wenn ein Schritt wechselt oder der Rundgang endet. */
  readonly ansage = signal('');

  @HostBinding('class.schmal') schmal = passt(SCHMAL);
  @HostBinding('class.ruhig') ruhig = passt(RUHIG);

  private ziel: HTMLElement | null = null;
  private vorher: HTMLElement | null = null;
  private lauf = 0;
  private readonly beimScrollen = () => this.ausrichten();

  constructor() {
    effect(() => {
      const s = this.rundgang.aktiv();
      untracked(() => void this.zeigen(s));
    });
    this.zone.runOutsideAngular(() => document.addEventListener('scroll', this.beimScrollen, true));
  }

  get schritt(): RundgangSchritt | null {
    const s = this.stand();
    return s ? s.rundgang.schritte[s.index] : null;
  }

  get text(): string {
    return this.schritt ? jeGeraet(this.schritt.text, passt(KOPF_MOBIL)) : '';
  }

  get letzter(): boolean {
    const s = this.stand();
    return !!s && s.index === s.rundgang.schritte.length - 1;
  }

  weiter(): void {
    this.rundgang.weiter();
  }

  zurueck(): void {
    this.rundgang.zurueck();
  }

  beenden(): void {
    this.rundgang.beenden();
  }

  @HostListener('document:keydown', ['$event'])
  taste(e: KeyboardEvent): void {
    if (!this.stand()) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      this.beenden();
      return;
    }
    const inBlase = !!this.blase?.nativeElement.contains(document.activeElement);
    if (!inBlase) return;
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      this.weiter();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      this.zurueck();
    }
  }

  @HostListener('window:resize')
  beiGroesse(): void {
    this.schmal = passt(SCHMAL);
    this.ausrichten();
  }

  ngOnDestroy(): void {
    document.removeEventListener('scroll', this.beimScrollen, true);
  }

  private async zeigen(s: RundgangStand | null): Promise<void> {
    const lauf = ++this.lauf;
    if (!s) {
      if (this.stand()) {
        this.stand.set(null);
        this.ziel = null;
        this.ansage.set('Rundgang beendet.');
        this.cdr.detectChanges();
        if (this.vorher?.isConnected) this.vorher.focus();
        this.vorher = null;
      }
      return;
    }
    if (!this.stand() && document.activeElement instanceof HTMLElement) {
      this.vorher = document.activeElement;
    }
    const schritt = s.rundgang.schritte[s.index];
    const ziel = await this.zielFinden(schritt.ziel, lauf);
    if (lauf !== this.lauf) return; // inzwischen weitergeklickt
    this.ziel = ziel;
    this.stand.set(s);
    const n = s.rundgang.schritte.length;
    this.ansage.set(`Schritt ${s.index + 1} von ${n}: ${schritt.titel}. ${this.text}`);
    this.cdr.detectChanges();
    if (ziel) this.insBild(ziel);
    this.ausrichten();
    this.blase?.nativeElement.focus({ preventScroll: true });
  }

  /** Das erste sichtbare Element zum Selektor; wartet, solange die Seite lädt. */
  private zielFinden(selektor: string, lauf: number): Promise<HTMLElement | null> {
    return new Promise((fertig) => {
      const start = Date.now();
      const suchen = () => {
        if (lauf !== this.lauf) return fertig(null);
        const el = sichtbaresElement(selektor);
        if (el || Date.now() - start >= ZIEL_WARTEZEIT_MS) return fertig(el);
        setTimeout(suchen, ZIEL_TAKT_MS);
      };
      suchen();
    });
  }

  /**
   * Holt das Ziel in den sichtbaren Bereich: mobil über die Karte am unteren Rand,
   * auf Desktop mit Platz für die Sprechblase. Ohne Animation, damit Kegel und Ziel
   * gleich zusammenpassen.
   */
  private insBild(ziel: HTMLElement): void {
    const r = ziel.getBoundingClientRect();
    const blasenHoehe = this.blase?.nativeElement.offsetHeight ?? 0;
    const unten = document.documentElement.clientHeight - (this.schmal ? blasenHoehe + 2 * RAND : RAND);
    if (r.top >= RAND && r.bottom <= unten) return;
    const oben = this.schmal ? 72 : 112;
    const alt = ziel.style.scrollMarginTop;
    ziel.style.scrollMarginTop = `${oben}px`;
    ziel.scrollIntoView({ block: 'start', behavior: 'auto' });
    ziel.style.scrollMarginTop = alt;
  }

  /** Setzt Lichtkegel, Sprechblase und Pfeil an das Ziel, wie es gerade im Fenster steht. */
  private ausrichten(): void {
    const blase = this.blase?.nativeElement;
    if (!this.stand() || !blase) return;
    const b = { w: blase.offsetWidth, h: blase.offsetHeight };
    const vw = document.documentElement.clientWidth;
    const vh = document.documentElement.clientHeight;

    if (!this.ziel?.isConnected) {
      this.kegel.set(null);
      this.pfeil.set(null);
      this.blasenOrt.set(this.schmal ? {} : { left: (vw - b.w) / 2, top: (vh - b.h) / 2 });
      this.cdr.detectChanges();
      return;
    }

    const r = this.ziel.getBoundingClientRect();
    const k: Kasten = { x: r.left - POLSTER, y: r.top - POLSTER, w: r.width + 2 * POLSTER, h: r.height + 2 * POLSTER };

    if (this.schmal) {
      // Die Karte steht unten; der Kegel endet über ihr
      const blasenOben = vh - RAND - b.h - RAND;
      if (k.y + k.h > blasenOben) k.h = Math.max(40, blasenOben - k.y);
      this.blasenOrt.set({});
      this.pfeil.set(null);
    } else {
      const mitte = (a: number, l: number) => Math.max(RAND, Math.min(a, vw - l - RAND));
      const pfeilX = (x: number) => Math.max(16, Math.min(k.x + k.w / 2 - x - 8, b.w - 32));
      if (k.y + k.h + ABSTAND + b.h <= vh - RAND) {
        const x = mitte(k.x + k.w / 2 - 60, b.w);
        this.blasenOrt.set({ left: x, top: k.y + k.h + ABSTAND });
        this.pfeil.set({ seite: 'oben', versatz: pfeilX(x) });
      } else if (k.x + k.w + ABSTAND + b.w <= vw - RAND) {
        const y = Math.max(RAND, Math.min(k.y, vh - b.h - RAND));
        this.blasenOrt.set({ left: k.x + k.w + ABSTAND, top: y });
        this.pfeil.set({ seite: 'links', versatz: Math.max(16, Math.min(k.y + Math.min(k.h, 80) / 2 - y - 8, b.h - 32)) });
      } else {
        const x = mitte(k.x + k.w / 2 - 60, b.w);
        this.blasenOrt.set({ left: x, top: Math.max(RAND, k.y - ABSTAND - b.h) });
        this.pfeil.set({ seite: 'unten', versatz: pfeilX(x) });
      }
    }
    this.kegel.set(k);
    this.cdr.detectChanges();
  }
}

/** Das erste Element zum Selektor, das eine Fläche hat (nicht versteckt, nicht display:none). */
export function sichtbaresElement(selektor: string): HTMLElement | null {
  for (const el of Array.from(document.querySelectorAll<HTMLElement>(selektor))) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden') return el;
  }
  return null;
}
