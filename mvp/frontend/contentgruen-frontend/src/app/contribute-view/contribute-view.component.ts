import { Component, ElementRef, ViewChild, OnDestroy } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { NavigationService } from '../services/navigation.service';
import { LoggingService } from '../services/logging.service';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatCardModule } from '@angular/material/card';
import { AddCommentaryWorkflowComponent } from "../add-commentary-workflow/add-commentary-workflow.component";
import { AddGenerictextWorkflowComponent } from "../add-generictext-workflow/add-generictext-workflow.component";
import { AddImageWorkflowComponent } from "../add-image-workflow/add-image-workflow.component";
import { CommonModule } from '@angular/common';
import { BreakpointService } from '../shared/services/breakpoint.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-contribute-view',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatTooltipModule,
    MatExpansionModule,
    MatCardModule,
    AddCommentaryWorkflowComponent,
    AddGenerictextWorkflowComponent,
    AddImageWorkflowComponent,
  ],
  templateUrl: './contribute-view.component.html',
  styleUrls: ['./contribute-view.component.css']
})
export class ContributeViewComponent implements OnDestroy {
  activePanel: string = '';
  searchQuery: string = '';
  isMobile: boolean = false;
  showMobileForm: string = ''; // 'commentary' | 'generictext' | ''
  private destroy$ = new Subject<void>();

  @ViewChild('commentaryPanel') commentaryPanel!: ElementRef;
  @ViewChild('generictextPanel') generictextPanel!: ElementRef;
  @ViewChild('imagePanel') imagePanel!: ElementRef;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private navigationService: NavigationService,
    private logger: LoggingService,
    private breakpointService: BreakpointService
  ) {
    this.logger.debug('ContributeViewComponent created');
    this.logger.debug('route', route);

    // Detect mobile breakpoint using breakpoint service
    this.breakpointService.isMobile$
      .pipe(takeUntil(this.destroy$))
      .subscribe(isMobile => {
        this.isMobile = isMobile;
        this.logger.debug('Mobile breakpoint detected:', this.isMobile);
      });
  }

  ngOnInit(): void {
    this.route.queryParams
      .pipe(takeUntil(this.destroy$))
      .subscribe((params) => {
        this.activePanel = params['panel'] || '';
        this.searchQuery = params['searchQuery'] || '';
        // For mobile, check if we should show a specific form
        if (this.isMobile) {
          // Update showMobileForm based on the presence/absence of form param
          this.showMobileForm = params['form'] || '';
        }
      });
  }

  ngAfterViewInit(): void {
    // Scroll to the specified panel after the view is initialized
    setTimeout(() => {
      this.scrollToActivePanel();
    }, 0); // Allow the DOM to finish rendering
  }

  isPanelActive(panel: string): boolean {
    return this.activePanel === panel;
  }

  navigateToStart(): void {
    this.navigationService.navigateToStart();
  }

  /**
   * Der Fangkorb ist kein vierter Beitragstyp, sondern der Weg daran vorbei:
   * er fuehrt aus dieser Auswahl heraus statt in ein weiteres Formular.
   */
  navigateToRawInput(): void {
    this.router.navigate(['/einwerfen']);
  }

  navigateToAddCommentaryWorkflow() {
    this.router.navigate(['/workflow/add-commentary']);
  }

  navigateToAddReferenceWorkflow() {
    // TODO: Implement when reference workflow is ready
  }

  navigateToAddGenerictextWorkflow() {
    this.router.navigate(['/workflow/add-generictext']);
  }

  // Mobile navigation methods
  selectMobileContentType(type: string): void {
    if (this.isMobile) {
      this.showMobileForm = type;
      this.activePanel = type;
      // Update URL with query params
      this.router.navigate([], {
        relativeTo: this.route,
        queryParams: { form: type, searchQuery: this.searchQuery },
        queryParamsHandling: 'merge'
      });
    }
  }

  closeMobileForm(): void {
    this.showMobileForm = '';
    this.activePanel = '';
    // Clear form param from URL
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { form: null, searchQuery: this.searchQuery },
      queryParamsHandling: 'merge'
    });
  }

  scrollToActivePanel(): void {
    this.logger.debug('Scrolling to active panel:', this.activePanel);
    if (this.activePanel === 'commentary' && this.commentaryPanel?.nativeElement) {
      this.logger.debug('Scrolling to commentary panel');
      this.commentaryPanel.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (this.activePanel === 'generictext' && this.generictextPanel?.nativeElement) {
      this.logger.debug('Scrolling to generic text panel');
      this.generictextPanel.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (this.activePanel === 'image' && this.imagePanel?.nativeElement) {
      this.logger.debug('Scrolling to image panel');
      this.imagePanel.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      this.logger.warn('No matching panel found or panel not initialized.');
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
