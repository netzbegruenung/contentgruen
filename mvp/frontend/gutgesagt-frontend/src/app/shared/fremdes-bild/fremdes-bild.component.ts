import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  Input,
  OnChanges,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';

/** ``adresse`` als URL, relativ zu ``eigenerOrigin`` gelesen; ``null``, wenn sie sich nicht lesen laesst. */
function alsUrl(adresse: string, eigenerOrigin: string): URL | null {
  try {
    return new URL(adresse, eigenerOrigin);
  } catch {
    return null;
  }
}

/**
 * Ob der Browser fuer ``adresse`` einen fremden Server anspraeche. Eigene und relative
 * Adressen sowie eingebettete (``data:``, ``blob:``) sind nicht fremd; was sich nicht lesen
 * laesst, gilt vorsichtshalber als fremd.
 */
export function istFremdeAdresse(adresse: string, eigenerOrigin: string = location.origin): boolean {
  const url = alsUrl(adresse, eigenerOrigin);
  if (!url) return true;
  if (url.protocol === 'data:' || url.protocol === 'blob:') return false;
  return url.origin !== eigenerOrigin;
}

/**
 * Ein Bild von einem fremden Server laedt erst auf Klick (#447): Bis dahin steht ein
 * Platzhalter "Bild laden", und der fremde Server erfaehrt nichts von der Person. Der Klick
 * laedt nur dieses Bild; gemerkt wird er nicht. Bilder vom eigenen Server zeigt die
 * Komponente sofort.
 *
 * Das Bild fuellt den Host und erbt von ihm ``object-fit``, ``max-height``,
 * ``border-radius`` und ``background``; Groesse und Zuschnitt bestimmt also die Stelle,
 * die die Komponente einbindet. Die Mindesthoehe des Platzhalters setzt sie ueber
 * ``--fremdes-bild-hoehe`` (Standard 96px, ``0`` fuer ein Band fester Hoehe).
 */
@Component({
  selector: 'app-fremdes-bild',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './fremdes-bild.component.html',
  styleUrl: './fremdes-bild.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FremdesBildComponent implements OnChanges {
  @Input({ required: true }) src!: string;
  @Input() alt = '';
  /** Ohne Symbol, wo schon eines daneben steht (Kopfband der Album-Karte). */
  @Input() mitSymbol = true;

  protected geladen = false;
  protected fremd = true;
  /** Nur der Hostname, damit der Hinweis kurz bleibt. */
  protected server = '';

  constructor(
    private readonly host: ElementRef<HTMLElement>,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes['src']) return;
    // Jede neue Adresse fragt wieder nach; die Adresse wird nur hier gelesen.
    this.geladen = false;
    this.fremd = istFremdeAdresse(this.src);
    this.server = alsUrl(this.src, location.origin)?.hostname || 'einem fremden Server';
  }

  get zeigen(): boolean {
    return this.geladen || !this.fremd;
  }

  /**
   * Nach dem Klick liegt der Fokus auf dem Bild. Ohne eigenen Alternativtext saehe ein
   * Screenreader dort nichts; dann nennt er wenigstens, woher das Bild kommt.
   */
  get bildAlt(): string {
    return this.alt || (this.fremd ? `Bild von ${this.server}` : '');
  }

  /**
   * Enter loest am Knopf schon beim Druecken den Klick aus; das keyup landet danach auf dem
   * Bild. Die Karte darum oeffnet bei keyup.enter die Detailansicht, deshalb endet es hier.
   */
  @HostListener('keyup.enter', ['$event'])
  enterAbfangen(ereignis: Event): void {
    ereignis.stopPropagation();
  }

  laden(ereignis: Event): void {
    // Die Karte darum oeffnet sonst bei Klick die Detailansicht.
    ereignis.stopPropagation();
    const hatteFokus = this.host.nativeElement.contains(document.activeElement);
    this.geladen = true;
    this.cdr.detectChanges();
    if (hatteFokus) {
      this.host.nativeElement.querySelector('img')?.focus();
    }
  }
}
