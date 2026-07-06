import { Component, Input, ChangeDetectionStrategy, OnDestroy } from '@angular/core';
import { NavigationService } from '../services/navigation.service';
import { LoggingService } from '../services/logging.service';
import { SearchService } from '../services/search.service';
import { Router } from '@angular/router';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';


@Component({
  selector: 'app-search',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: SHARED_IMPORTS,
  templateUrl: './search.component.html',
  styleUrls: ['./search.component.css'],
})
export class SearchComponent implements OnDestroy {
  @Input() searchQuery: string = '';
  @Input() compactMode: boolean = false; // Enable compact mode on result view
  private destroy$ = new Subject<void>();

  constructor(
    private navigationService: NavigationService,
    private logger: LoggingService,
    private searchService: SearchService,
    private router: Router
  ) { }

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
