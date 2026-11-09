import { AfterViewInit, Component, ElementRef, Input, ChangeDetectionStrategy, OnDestroy, ViewChild } from '@angular/core';
import { NavigationService } from '../services/navigation.service';
import { LoggingService } from '../services/logging.service';
import { SearchService } from '../services/search.service';
import { Router } from '@angular/router';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

/** Was ins Suchfeld gehoert, als Beschriftung des Feldes (#644). */
export const SUCHFELD_NAME = 'Was hast du gelesen? Text oder Post einfügen';
/** Kurz fuer das kompakte Feld ueber den Treffern: Daneben steht der Such-Knopf (#644). */
export const SUCHFELD_NAME_KOMPAKT = 'Text oder Post einfügen';

@Component({
  selector: 'app-search',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: SHARED_IMPORTS,
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
