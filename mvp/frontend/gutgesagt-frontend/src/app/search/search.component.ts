import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, Input, ChangeDetectionStrategy, NgZone, OnDestroy, ViewChild } from '@angular/core';
import { HOT_TAKES } from '../shared/startbeispiel';
import { NavigationService } from '../services/navigation.service';
import { LoggingService } from '../services/logging.service';
import { SearchService } from '../services/search.service';
import { Router, RouterLink } from '@angular/router';
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
 * auf den der Link springt (Persona-Test Gerd). Wortlaut rechtlich abgestimmt (16.11.2026):
 * nur nach Ruecksprache aendern.
 */
export const SUCHHINWEIS = 'Suchtexte speichern wir ohne deinen Namen. Nach Prüfung können sie öffentlich werden.';
/**
 * Über den Treffern nur der erste Satz und „Mehr“ (Freigabe E5, 14.11.2026): Der volle
 * Hinweis schob die erste Antwort mobil aus dem ersten Bildschirm. Der Start behält ihn ganz.
 */
export const SUCHHINWEIS_KURZ = 'Suchtexte speichern wir ohne deinen Namen.';
/** Sprungmarke des Abschnitts „Deine Suchanfragen“ in der Datenschutzerklärung. */
export const SUCHANFRAGEN_ABSCHNITT = 'suchanfragen';
/** Zaehler fuer eindeutige Kennungen des Hinweises, falls mehrere Suchfelder zugleich da sind. */
let naechsterHinweis = 0;

@Component({
  selector: 'app-search',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [...SHARED_IMPORTS, RouterLink],
  templateUrl: './search.component.html',
  styleUrls: ['./search.component.css'],
})
export class SearchComponent implements AfterViewInit, OnDestroy {
  @Input() searchQuery: string = '';
  @Input() compactMode: boolean = false; // Enable compact mode on result view
  /**
   * Fokus beim Laden ins Feld. Nur der Start setzt es, und nur am Desktop: Mobil
   * sprang sonst gleich die Tastatur auf (#644).
   */
  @Input() autofokus = false;
  /** Ziel des Skip-Links „Zur Suche“ im Kopf; nur das Feld auf dem Start traegt es (leer: eigene Kennung von Material). */
  @Input() feldId = '';
  @ViewChild('feld') private feld?: ElementRef<HTMLInputElement>;
  /**
   * Auf dem Start tippt das leere Feld typische Hot Takes als Platzhalter ein, daneben
   * blinkt „Ausprobieren“ (Designrunde 17.11.). Zwei Durchläufe, dann bleibt das erste
   * Beispiel stehen (WCAG 2.2.2). Bei reduzierter Bewegung kein Tippen, nur das Beispiel.
   * Klickt oder tippt man selbst ins Feld, ist der Platzhalter sofort weg.
   */
  @Input() beispielAnimation = false;
  beispielText = '';
  beispielFertig = false;
  private beispielAus = false;
  private beispielTimer?: ReturnType<typeof setTimeout>;
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
    private cdr: ChangeDetectorRef
  ) { }

  ngAfterViewInit(): void {
    if (this.autofokus) {
      this.feld?.nativeElement.focus({ preventScroll: true });
    }
    if (this.beispielAnimation) {
      const ruhig = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      if (ruhig) {
        this.beispielZeigen(HOT_TAKES[0], true);
      } else {
        this.zone.runOutsideAngular(() => this.tippen(0, 0, 0));
      }
    }
  }

  /** Eigene Eingabe beendet die Vorführung und leert den Platzhalter. */
  beispielBeenden(): void {
    if (this.beispielAus) {
      return;
    }
    this.beispielAus = true;
    clearTimeout(this.beispielTimer);
    this.beispielZeigen('', false);
  }

  beispielAusprobieren(): void {
    const text = this.beispielText;
    this.beispielBeenden();
    this.performSearch(text);
  }

  private beispielZeigen(text: string, fertig: boolean): void {
    this.zone.run(() => {
      this.beispielText = text;
      this.beispielFertig = fertig;
      this.cdr.markForCheck();
    });
  }

  private tippen(nr: number, zeichen: number, runde: number): void {
    if (this.beispielAus) {
      return;
    }
    const satz = HOT_TAKES[nr];
    if (zeichen <= satz.length) {
      this.beispielZeigen(satz.slice(0, zeichen), zeichen === satz.length);
      this.beispielTimer = setTimeout(() => this.tippen(nr, zeichen + 1, runde), zeichen === satz.length ? 2600 : 45);
      return;
    }
    const naechster = (nr + 1) % HOT_TAKES.length;
    const neueRunde = naechster === 0 ? runde + 1 : runde;
    if (neueRunde >= 2) {
      this.beispielZeigen(HOT_TAKES[0], true);
      return;
    }
    this.beispielZeigen('', false);
    this.beispielTimer = setTimeout(() => this.tippen(naechster, 0, neueRunde), 400);
  }

  onSearch(): void {
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
