import { Component, Input } from '@angular/core';
import { SearchResponse } from '../services/dtos/searchDtos';
import { WorkflowService } from '../services/workflow.service'; // Import WorkflowService
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { NavigationService } from '../services/navigation.service';
import { FORMULAR_PFAD, aussageParameter } from '../shared/formular-adresse';

@Component({
  selector: 'app-commentary-search-results',
  standalone: true,
  imports: [
    ...SHARED_IMPORTS,
    CommonModule,
    MatButtonModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './commentary-search-results.component.html',
  styleUrls: ['./commentary-search-results.component.css'],
})
export class CommentarySearchResultsComponent {
  @Input() searchResponse!: SearchResponse; // Input for the search response data
  @Input() loading = false;                // Input to display loading state
  @Input() error = '';                     // Input to display error messages
  @Input() searchQuery: string = '';       // Input for the search query
  @Input() showMinimalEmptyState: boolean = false; // Show minimal version when other component has results

  // Popular topics for empty state suggestions
  popularTopics: string[] = ['Klimaschutz', 'Mobilität', 'Energie', 'Soziales', 'Digitalisierung', 'Bildung'];

  constructor(
    private workflowService: WorkflowService,
    private router: Router,
    private dialog: MatDialog,
    private navigationService: NavigationService
  ) { } // Inject services

  /** Ins Formular, als Antwort auf die Aussage dieser Suche - per ID, sonst mit ihrem Text. */
  navigateToContributeView(): void {
    this.router.navigate([FORMULAR_PFAD.commentary], {
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
