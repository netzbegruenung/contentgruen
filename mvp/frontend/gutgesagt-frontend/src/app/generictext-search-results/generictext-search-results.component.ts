import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { SearchResponse } from '../services/dtos/searchDtos';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { NavigationService } from '../services/navigation.service';
import { FORMULAR_PFAD, aussageParameter } from '../shared/formular-adresse';

@Component({
  selector: 'app-generictext-search-results',
  standalone: true,
  imports: [
    ...SHARED_IMPORTS
  ],
  templateUrl: './generictext-search-results.component.html',
  styleUrls: ['./generictext-search-results.component.css']
})
export class GenerictextSearchResultsComponent {
  @Input() searchResponse!: SearchResponse;       // Input for the search response data
  @Input() loading = false;                      // Input to display loading state
  @Input() error = '';                           // Input to display error messages
  @Input() searchQuery: string = '';             // Input for the search query
  @Input() showMinimalEmptyState: boolean = false; // Show minimal version when other component has results
  showAddGenerictext = false;               // Tracks whether the add generictext section is visible

  // Popular topics for empty state suggestions
  popularTopics: string[] = ['Klimaschutz', 'Mobilität', 'Energie', 'Soziales', 'Digitalisierung', 'Bildung'];

  constructor(
    private router: Router,
    private navigationService: NavigationService
  ) {}

  /**
 * Toggles the visibility of the "Add Generictext" section.
 */
  toggleAddGenerictext(): void {
    this.showAddGenerictext = !this.showAddGenerictext;
  }

  /** Ins Formular, als Antwort auf die Aussage dieser Suche - per ID, sonst mit ihrem Text. */
  navigateToContributeView(): void {
    this.router.navigate([FORMULAR_PFAD.generictext], {
      queryParams: aussageParameter(
        this.searchResponse?.statement_id,
        this.searchResponse?.statement_text || this.searchQuery,
      ),
    });
  }

  /**
 * Performs a search for the selected topic
 */
  searchForTopic(topic: string): void {
    this.navigationService.navigateToResult(topic);
  }
}
