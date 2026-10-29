import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  OnChanges,
  SimpleChanges,
} from '@angular/core';

/**
 * Ob der Browser fuer ``adresse`` einen fremden Server anspraeche. Eigene und relative
 * Adressen sowie eingebettete (``data:``, ``blob:``) sind nicht fremd; was sich nicht lesen
 * laesst, gilt vorsichtshalber als fremd.
 */
export function istFremdeAdresse(adresse: string, eigenerOrigin: string = location.origin): boolean {
  let url: URL;
  try {
    url = new URL(adresse, eigenerOrigin);
  } catch {
    return true;
  }
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
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (zeigen) {
      <!-- Nach dem Klick sofort laden; was ohne Klick sichtbar ist, darf warten -->
      <img [src]="src" [alt]="alt" [attr.loading]="geladen ? 'eager' : 'lazy'" tabindex="-1" />
    } @else {
      <button type="button" class="bild-laden"
              [attr.aria-label]="alt ? 'Bild laden: ' + alt : 'Bild laden'"
              [attr.title]="'Lädt das Bild von ' + server"
              (click)="laden($event)" (keyup)="$event.stopPropagation()">
        @if (symbol) {
          <span class="bild-laden-symbol" aria-hidden="true">🖼️</span>
        }
        <span>Bild laden</span>
      </button>
    }
  `,
  styleUrl: './fremdes-bild.component.scss',
})
export class FremdesBildComponent implements OnChanges {
  @Input({ required: true }) src!: string;
  @Input() alt = '';
  /** Ohne Symbol, wo schon eines daneben steht (Kopfband der Album-Karte). */
  @Input() symbol = true;

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
    try {
      return new URL(this.src, location.origin).hostname;
    } catch {
      return 'einem fremden Server';
    }
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
