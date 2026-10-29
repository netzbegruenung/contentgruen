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
 * Ein Bild, das von einem fremden Server kommt, laedt erst auf Klick (#447): Bis dahin
 * steht ein Platzhalter "Bild laden", und der fremde Server erfaehrt nichts von der Person.
 * Der Klick laedt nur dieses Bild; gemerkt wird er nicht. Bilder vom eigenen Server zeigt
 * die Komponente sofort. Das Bild fuellt den Host; Groesse und Zuschnitt bestimmt die
 * Stelle, die sie einbindet.
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

  constructor(
    private readonly host: ElementRef<HTMLElement>,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['src']) {
      this.geladen = false;
    }
  }

  get zeigen(): boolean {
    return this.geladen || !istFremdeAdresse(this.src);
  }

  /** Nur der Hostname, damit der Hinweis kurz bleibt. */
  get server(): string {
    return alsUrl(this.src, location.origin)?.hostname || 'einem fremden Server';
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
