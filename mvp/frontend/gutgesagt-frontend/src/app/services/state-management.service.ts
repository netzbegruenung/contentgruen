import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { distinctUntilChanged, map } from 'rxjs/operators';
import { SearchResponse } from './dtos/searchDtos';

interface AppState {
  searchQuery: string;
  searchResults: SearchResponse | null;
  loading: boolean;
  error: string | null;
  contributions: any[];
  metrics: any | null;
}

@Injectable({
  providedIn: 'root'
})
export class StateManagementService {
  private readonly initialState: AppState = {
    searchQuery: '',
    searchResults: null,
    loading: false,
    error: null,
    contributions: [],
    metrics: null
  };

  private state$ = new BehaviorSubject<AppState>(this.initialState);

  // Selectors
  readonly searchQuery$ = this.select(state => state.searchQuery);
  readonly searchResults$ = this.select(state => state.searchResults);
  readonly loading$ = this.select(state => state.loading);
  readonly error$ = this.select(state => state.error);
  readonly contributions$ = this.select(state => state.contributions);
  readonly metrics$ = this.select(state => state.metrics);

  // Get current state
  get currentState(): AppState {
    return this.state$.value;
  }

  // Update methods
  setSearchQuery(query: string): void {
    this.updateState({ searchQuery: query });
  }

  setSearchResults(results: SearchResponse | null): void {
    this.updateState({ searchResults: results, loading: false, error: null });
  }

  setLoading(loading: boolean): void {
    this.updateState({ loading });
  }

  /** Eine gescheiterte Suche laesst keine Ergebnisse der vorigen stehen. */
  setError(error: string | null): void {
    this.updateState({ error, loading: false, searchResults: null });
  }

  /**
   * Eine neue Suche beginnt: Ergebnisse der vorigen - und damit ihre Aussage-ID -
   * gelten nicht mehr. Wird gerufen, bevor irgendetwas angefragt ist, damit in
   * diesem Fenster kein Knopf die alte Aussage-ID aufgreift.
   */
  neueSucheBeginnen(): void {
    this.updateState({ searchResults: null, error: null });
  }

  setContributions(contributions: any[]): void {
    this.updateState({ contributions });
  }

  setMetrics(metrics: any): void {
    this.updateState({ metrics });
  }

  clearSearch(): void {
    this.updateState({
      searchQuery: '',
      searchResults: null,
      error: null
    });
  }

  reset(): void {
    this.state$.next(this.initialState);
  }

  // Private helper methods
  private select<T>(selector: (state: AppState) => T): Observable<T> {
    return this.state$.pipe(
      map(selector),
      distinctUntilChanged()
    );
  }

  private updateState(partial: Partial<AppState>): void {
    const currentState = this.state$.value;
    this.state$.next({ ...currentState, ...partial });
  }
}
