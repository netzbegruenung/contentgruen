import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, Input, ChangeDetectionStrategy, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { HOT_TAKES } from '../shared/startbeispiel';
import { NavigationService } from '../services/navigation.service';
import { LoggingService } from '../services/logging.service';
import { SearchService } from '../services/search.service';
import { Router, RouterLink } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { TextFieldModule } from '@angular/cdk/text-field';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

/**
 * Was ins Suchfeld gehoert, als Beschriftung des Feldes (#644): der fremde Text, auf den man
 * antworten will. "Text oder Post einfügen" lasen Testerinnen als "mein Post?" (Ersteindruck-Test 14.11.).
 */
export const SUCHFELD_NAME = 'Worauf willst du antworten? Text einfügen';
/** Kurz fuer das kompakte Feld ueber den Treffern: Daneben steht der Such-Knopf (#644). */
export const SUCHFELD_NAME_KOMPAKT = 'Worauf antworten? Text einfügen';
/**
 * Unter dem Feld: dass der Suchtext gespeichert wird und nach der Vormoderation (#664)
 * sichtbar werden kann. Die Einzelheiten stehen im Abschnitt der Datenschutzerklärung,
 * auf den der Link springt (Persona-Test Gerd). Wortlaut rechtlich abgestimmt (16.11.2026),
 * am 18.11.2026 vom Maintainer bestätigt. Kein „nur“: Proxy-Logs halten Suchtexte mit IP
 * befristet (siehe Löschkonzept). Nur nach Ruecksprache aendern.
 */
export const SUCHHINWEIS = 'Suchtexte speichern wir ohne deinen Namen. Nach Prüfung können sie öffentlich werden.';
/**
 * Über den Treffern nur der erste Satz und „Mehr“ (Freigabe E5, 14.11.2026): Der volle
 * Hinweis schob die erste Antwort mobil aus dem ersten Bildschirm. Der Start behält ihn ganz.
 */
export const SUCHHINWEIS_KURZ = 'Suchtexte speichern wir ohne deinen Namen.';
/** Sprungmarke des Abschnitts „Deine Suchanfragen“ in der Datenschutzerklärung. */
export const SUCHANFRAGEN_ABSCHNITT = 'suchanfragen';
/** Ab hier abwärts wird das Feld mehrzeilig (Designrunde 18.11.). */
export const SCHMAL = '(max-width: 599px)';
/** Zaehler fuer eindeutige Kennungen des Hinweises, falls mehrere Suchfelder zugleich da sind. */
let naechsterHinweis = 0;

@Component({
  selector: 'app-search',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [...SHARED_IMPORTS, RouterLink, TextFieldModule],
  templateUrl: './search.component.html',
  styleUrls: ['./search.component.css'],
})
export class SearchComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() searchQuery: string = '';
  @Input() compactMode: boolean = false; // Enable compact mode on result view
  /**
   * Fokus beim Laden ins Feld. Nur der Start setzt es, und nur am Desktop: Mobil
   * sprang sonst gleich die Tastatur auf (#644).
   */
  @Input() autofokus = false;
  /** Ziel des Skip-Links „Zur Suche“ im Kopf; nur das Feld auf dem Start traegt es (leer: eigene Kennung von Material). */
  @Input() feldId = '';
  private feld?: ElementRef<HTMLInputElement | HTMLTextAreaElement>;
  /** Beim Wechsel der Breite (Handy drehen) war das Feld fokussiert: das neue Feld übernimmt den Fokus. */
  private fokusZurueck = false;
  @ViewChild('feld') private set feldRef(ref: ElementRef<HTMLInputElement | HTMLTextAreaElement> | undefined) {
    this.feld = ref;
    if (ref && this.fokusZurueck) {
      this.fokusZurueck = false;
      const el = ref.nativeElement;
      el.focus({ preventScroll: true });
      // ngModel schreibt den Wert erst nach einem Mikrotask ins neue Feld; danach ans Ende
      Promise.resolve().then(() => el.setSelectionRange(el.value.length, el.value.length));
    }
  }
  /**
   * Unter 600 px ein mitwachsendes Textfeld (2 bis 4 Zeilen) statt der einen Zeile: Der
   * vorgetippte Hot Take bricht um, statt aus dem Feld zu laufen (Designrunde 18.11.).
   */
  schmal = false;
  /**
   * Auf dem Start tippt das leere Feld typische Hot Takes als Platzhalter ein (Designrunde
   * 17.11.). Solange das Feld leer ist, heißt der eine Knopf „Beispiel ausprobieren“ und
   * sucht den gezeigten Hot Take; mit Text im Feld heißt er wieder „Suchen“ (Designrunde
   * 18.11.). Die Vorführung stoppt, sobald man ins Feld klickt, tippt oder einfügt; Fokus
   * auf den Knopf hält sie beim aktuellen Beispiel an (WCAG 2.2.2); spätestens nach zwei
   * Durchläufen bleibt das erste Beispiel stehen. Tab beendet sie nicht, damit der Knopf
   * per Tastatur im Beispielzustand erreichbar bleibt. Bei reduzierter Bewegung kein
   * Tippen, nur das Beispiel.
   */
  @Input() beispielAnimation = false;
  beispielText = '';
  private beispielAus = false;
  private beispielTimer?: ReturnType<typeof setTimeout>;
  /** Der Hot Take, der gerade getippt wird oder steht; den sucht der Knopf ganz. */
  private beispielNr = 0;
  /**
   * Beispielzustand: Das Feld ist leer und zeigt einen Hot Take. Der Text bleibt von
   * Anfang an, auch zwischen zwei Hot Takes, damit der Knopf nicht flackert.
   */
  get beispielZustand(): boolean {
    return this.beispielAnimation && !this.compactMode && !this.beispielAus && !this.searchQuery;
  }
  /** Der ganze Hot Take, den der Knopf im Beispielzustand sucht. */
  get beispielSatz(): string {
    return HOT_TAKES[this.beispielNr].text;
  }
  get suchhinweis(): string {
    return this.compactMode ? SUCHHINWEIS_KURZ : SUCHHINWEIS;
  }
  readonly suchanfragenAbschnitt = SUCHANFRAGEN_ABSCHNITT;
  /** Screenreader lesen den Hinweis mit dem Feld vor (aria-describedby). */
  readonly hinweisId = `such-hinweis-${naechsterHinweis++}`;
  get feldName(): string {
    return this.compactMode ? SUCHFELD_NAME_KOMPAKT : SUCHFELD_NAME;
  }
  private destroy$ = new Subject<void>();

  constructor(
    private navigationService: NavigationService,
    private logger: LoggingService,
    private searchService: SearchService,
    private router: Router,
    private zone: NgZone,
    private cdr: ChangeDetectorRef,
    private breakpointObserver: BreakpointObserver
  ) { }

  /** Bei reduzierter Bewegung steht das Beispiel schon vor dem ersten Zeichnen. */
  private ruhig = false;

  ngOnInit(): void {
    this.ruhig = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (this.beispielAnimation && this.ruhig) {
      this.beispielText = HOT_TAKES[0].text;
    }
    this.breakpointObserver.observe(SCHMAL).pipe(takeUntil(this.destroy$)).subscribe((stand) => {
      if (stand.matches !== this.schmal && this.feld && document.activeElement === this.feld.nativeElement) {
        this.fokusZurueck = true;
      }
      this.schmal = stand.matches;
      this.cdr.markForCheck();
    });
  }

  /**
   * Enter sucht, auch im mehrzeiligen Feld; Umschalt+Enter macht keine neue Zeile.
   * Nur während einer laufenden IME-Komposition (etwa Japanisch) bestätigt Enter das Zeichen.
   * Annahme: Dann meldet der Browser isComposing oder keyCode 229. Handytastaturen wie Gboard
   * schließen das Wort vor Enter ab und schicken Enter ohne beides; am Gerät noch zu prüfen.
   */
  enterImFeld(ereignis: Event): void {
    const taste = ereignis as KeyboardEvent;
    if (taste.isComposing || taste.keyCode === 229) {
      return;
    }
    ereignis.preventDefault();
    this.onSearch();
  }

  /**
   * Ein Suchtext ist eine Zeile: Zeilenumbrueche aus eingefuegtem Text werden zu Leerzeichen.
   * Er landet in der Adresse der Trefferseite und dort wieder im Feld, und er wird als eine
   * Zeile gespeichert und angezeigt; fuer die Suche tragen Umbrueche nichts bei.
   */
  einzeilig(text: string): string {
    return (text ?? '').replace(/[^\S\r\n]*[\r\n]+[^\S\r\n]*/g, ' ');
  }

  /**
   * Eingabe im mehrzeiligen Feld: Umbrüche gleich im Feld ersetzen und den Cursor dort lassen,
   * wo er nach dem Einfügen stand, statt ihn ans Ende springen zu lassen.
   */
  feldGeaendert(text: string): void {
    const sauber = this.einzeilig(text);
    this.searchQuery = sauber;
    const el = this.feld?.nativeElement;
    if (el && sauber !== text && el.value === text) {
      const cursor = this.einzeilig(text.slice(0, el.selectionStart ?? text.length)).length;
      el.value = sauber;
      el.setSelectionRange(cursor, cursor);
    }
  }

  ngAfterViewInit(): void {
    if (this.autofokus) {
      this.feld?.nativeElement.focus({ preventScroll: true });
    }
    if (this.beispielAnimation && !this.ruhig) {
      // Erst nach dem ersten Zeichnen anfangen, ausserhalb der Zone
      this.zone.runOutsideAngular(() => {
        this.beispielTimer = setTimeout(() => this.tippen(0, 0, 0));
      });
    }
  }

  /** Eigene Eingabe beendet die Vorführung und leert den Platzhalter. */
  beispielBeenden(): void {
    if (this.beispielAus) {
      return;
    }
    this.beispielAus = true;
    clearTimeout(this.beispielTimer);
    this.beispielZeigen('');
  }

  /**
   * Fokus auf den Knopf im Beispielzustand: beim aktuellen Hot Take stehen bleiben und ihn
   * ganz zeigen, damit Feld und Knopf dasselbe meinen.
   */
  beispielAnhalten(): void {
    if (!this.beispielZustand) {
      return;
    }
    clearTimeout(this.beispielTimer);
    this.beispielTimer = undefined;
    this.beispielZeigen(this.beispielSatz);
  }

  private beispielAusprobieren(): void {
    const text = this.beispielSatz;
    this.beispielBeenden();
    this.performSearch(text);
  }

  /**
   * Die Vorführung läuft außerhalb der Zone: nur diese Komponente (OnPush) neu zeichnen,
   * nicht alle 45 ms die ganze App. Aus Template-Ereignissen (in der Zone) genügt markForCheck.
   */
  private beispielZeigen(text: string): void {
    this.beispielText = text;
    if (NgZone.isInAngularZone()) {
      this.cdr.markForCheck();
    } else {
      this.cdr.detectChanges();
    }
  }

  private tippen(nr: number, zeichen: number, runde: number): void {
    if (this.beispielAus) {
      return;
    }
    this.beispielNr = nr;
    const satz = HOT_TAKES[nr].text;
    if (zeichen <= satz.length) {
      this.beispielZeigen(satz.slice(0, zeichen));
      this.beispielTimer = setTimeout(() => this.tippen(nr, zeichen + 1, runde), zeichen === satz.length ? 2600 : 45);
      return;
    }
    const naechster = (nr + 1) % HOT_TAKES.length;
    const neueRunde = naechster === 0 ? runde + 1 : runde;
    if (neueRunde >= 2) {
      this.beispielNr = 0;
      this.beispielZeigen(HOT_TAKES[0].text);
      return;
    }
    this.beispielZeigen('');
    this.beispielTimer = setTimeout(() => this.tippen(naechster, 0, neueRunde), 400);
  }

  /** Im Beispielzustand sucht der Knopf (und Enter) den Hot Take, sonst den Feldinhalt. */
  onSearch(): void {
    if (this.beispielZustand) {
      this.beispielAusprobieren();
      return;
    }
    this.performSearch(this.searchQuery);
  }

  private performSearch(query: string): void {
    if (!query.trim()) {
      this.logger.warn('Search query is empty.');
      return;
    }

    this.logger.debug('Performing search for:', query);

    // Always navigate to update the URL, even if already on result page
    // The navigation service will handle the actual search
    this.navigationService.navigateToResult(query);
  }

  ngOnDestroy(): void {
    clearTimeout(this.beispielTimer);
    this.destroy$.next();
    this.destroy$.complete();
  }
}
