import { AfterViewInit, Component, ElementRef, Input, ChangeDetectionStrategy, OnDestroy, ViewChild } from '@angular/core';
import { NavigationService } from '../services/navigation.service';
import { LoggingService } from '../services/logging.service';
import { SearchService } from '../services/search.service';
import { Router, RouterLink } from '@angular/router';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

/** Was ins Suchfeld gehoert, als Beschriftung des Feldes (#644). */
export const SUCHFELD_NAME = 'Was hast du gelesen? Text oder Post einfügen';
/** Kurz fuer das kompakte Feld ueber den Treffern: Daneben steht der Such-Knopf (#644). */
export const SUCHFELD_NAME_KOMPAKT = 'Text oder Post einfügen';
/**
 * Unter dem Feld: dass der Suchtext gespeichert wird und nach der Vormoderation (#664)
 * sichtbar werden kann. Die Einzelheiten stehen im Abschnitt der Datenschutzerklärung,
 * auf den der Link springt (Persona-Test Gerd).
 */
export const SUCHHINWEIS =
  'Suchtexte speichern wir ohne deinen Namen. Gibt es noch keine Antwort, können sie nach ' +
  'Prüfung durch das Moderationsteam für alle sichtbar werden.';
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
    private router: Router
  ) { }

  ngAfterViewInit(): void {
    if (this.autofokus) {
      this.feld?.nativeElement.focus({ preventScroll: true });
    }
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
    this.destroy$.next();
    this.destroy$.complete();
  }
}
