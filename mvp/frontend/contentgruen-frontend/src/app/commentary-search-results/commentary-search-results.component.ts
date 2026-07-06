import { Component, Input } from '@angular/core';
import { SearchResponse } from '../services/dtos/searchDtos';
import { CommentaryResultItemComponent } from '../commentary-result-item/commentary-result-item.component';
import { WorkflowService } from '../services/workflow.service'; // Import WorkflowService
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { NavigationService } from '../services/navigation.service';

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

  commentaryResultItemComponent = CommentaryResultItemComponent; // Component type for result-carousel

  // Popular topics for empty state suggestions
  popularTopics: string[] = ['Klimaschutz', 'Mobilität', 'Energie', 'Soziales', 'Digitalisierung', 'Bildung'];

  constructor(
    private workflowService: WorkflowService,
    private router: Router,
    private dialog: MatDialog,
    private navigationService: NavigationService
  ) { } // Inject services

  navigateToContributeView(): void {
    // Use the statement_text from the search response if available, otherwise use searchQuery
    const statementText = this.searchResponse?.statement_text || this.searchQuery;
    this.router.navigate(['/contribute'], { queryParams: { panel: 'commentary' , searchQuery: statementText } });
  }

  /**
 * Performs a search for the selected topic
 */
  searchForTopic(topic: string): void {
    this.navigationService.navigateToResult(topic);
  }
}
