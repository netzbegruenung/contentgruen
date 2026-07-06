import { Component, ElementRef, HostListener, Injector, Input, SimpleChanges, Type, ViewChild, OnInit, OnDestroy, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { listAnimation } from '../shared/animations';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { SwipeGestureDirective } from '../shared/directives/swipe-gesture.directive';

@Component({
  selector: 'app-result-carousel',
  standalone: true,
  imports: [
    CommonModule,
    MatTooltipModule,
    MatIconModule,
    SwipeGestureDirective,
  ],
  templateUrl: './result-carousel.component.html',
  styleUrls: ['./result-carousel.component.css'],
  animations: [listAnimation]
})
export class ResultCarouselComponent<T> implements OnInit, OnDestroy {
  @Input() results: T[] = [];
  @Input() itemComponent!: Type<any>; // The dynamic component type to render for each result
  // Optional per-item resolver: when set, the component is chosen per result (e.g. mixed-type
  // carousels), otherwise the single `itemComponent` is used for every result.
  @Input() itemComponentResolver?: (result: T) => Type<any>;
  @Input() contentType: 'commentary' | 'generictext' = 'commentary'; // For vertical navigation

  @Output() verticalSwipe = new EventEmitter<'up' | 'down'>();

  @ViewChild('resultContainer', { static: false }) resultContainerRef!: ElementRef;
  @ViewChild('mobileContainer', { static: false }) mobileContainerRef!: ElementRef;
  private container!: HTMLElement;
  private mobileContainer!: HTMLElement;
  private injectorCache = new Map<any, Injector>();
  private intersectionObserver?: IntersectionObserver;
  private isInViewport = false;
  private viewportCenterDistance = Infinity;
  private destroy$ = new Subject<void>();

  isAtStart = true;
  isAtEnd = false;
  isMobile = false;
  isTablet = false;
  currentIndex = 0;
  totalItems = 0;

  constructor(
    private injector: Injector,
    private breakpointObserver: BreakpointObserver
  ) { }

  ngOnInit(): void {
    // Detect device type
    this.breakpointObserver.observe([
      '(max-width: 599px)',
      '(min-width: 600px) and (max-width: 959px)'
    ]).pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        this.isMobile = result.breakpoints['(max-width: 599px)'];
        this.isTablet = result.breakpoints['(min-width: 600px) and (max-width: 959px)'];

        // Update scroll behavior based on device
        if (this.container) {
          this.updateCarouselMode();
        }
      });
  }

  ngAfterViewInit(): void {
    // Use a small delay to ensure ViewChild is properly initialized
    setTimeout(() => {
      // Initialize desktop container
      if (!this.isMobile && this.resultContainerRef) {
        this.container = this.resultContainerRef.nativeElement;
        this.setupDesktopCarousel();
      }

      // Initialize mobile container
      if (this.isMobile && this.mobileContainerRef) {
        this.mobileContainer = this.mobileContainerRef.nativeElement;
        this.setupMobileCarousel();
      }
    }, 0);
  }

  private setupDesktopCarousel(): void {
    const isEdge = navigator.userAgent.includes('Edg');

    // Apply snapping only if it's not Edge
    if (!isEdge) {
      this.container.style.scrollSnapType = 'x mandatory';
    } else {
      this.container.style.scrollSnapType = 'none'; // Disable snapping for Edge
    }

    // Make container focusable for keyboard navigation
    this.container.tabIndex = 0;

    // Add keyboard event listener
    this.container.addEventListener('keydown', this.handleKeydown.bind(this));

    // Set up intersection observer
    this.setupIntersectionObserver();

    // Add scroll event listener
    this.container.addEventListener('scroll', this.onScroll.bind(this));

    // Initialize position
    setTimeout(() => {
      this.updateButtonStates();
    }, 100);
  }

  private setupMobileCarousel(): void {
    // Add scroll event listener for mobile
    this.mobileContainer.addEventListener('scroll', this.onMobileScroll.bind(this));

    // Initialize position - ensure container is ready
    setTimeout(() => {
      if (this.results.length > 0) {
        // Reset to scroll position 0 (first card)
        this.currentIndex = 0;
        this.mobileContainer.scrollTo({ left: 0, behavior: 'auto' });
      }
    }, 200);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['results']) {
      // Clear injector cache when results change
      this.injectorCache.clear();
      this.totalItems = this.results?.length || 0;
      this.currentIndex = 0;

      // Reset scroll position when results change
      setTimeout(() => {
        if (this.isMobile && this.mobileContainer && this.results.length > 0) {
          this.scrollToMobileIndex(0);
        } else if (!this.isMobile && this.container) {
          this.updateButtonStates();
        }
      }, 50);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();

    if (this.container) {
      this.container.removeEventListener('scroll', this.onScroll.bind(this));
      this.container.removeEventListener('keydown', this.handleKeydown.bind(this));
    }
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }
  }

  updateCarouselMode(): void {
    if (this.isMobile) {
      // Mobile: single card view
      this.scrollToIndex(this.currentIndex);
    }
  }

  scrollToIndex(index: number): void {
    if (!this.container || index < 0 || index >= this.totalItems) return;

    this.currentIndex = index;

    if (this.isMobile) {
      // For mobile, each card takes exactly the container width
      const containerWidth = this.container.clientWidth;
      const scrollPosition = index * containerWidth;
      this.container.scrollTo({ left: scrollPosition, behavior: 'smooth' });
    } else {
      // Desktop behavior
      const scrollPosition = index * 474; // card width + gap
      this.container.scrollTo({ left: scrollPosition, behavior: 'smooth' });
    }

    setTimeout(() => this.updateButtonStates(), 300);
  }

  navigateToCard(direction: 'prev' | 'next'): void {
    const newIndex = direction === 'next'
      ? Math.min(this.currentIndex + 1, this.totalItems - 1)
      : Math.max(this.currentIndex - 1, 0);

    this.scrollToIndex(newIndex);
  }

  onScroll(): void {
    this.updateButtonStates();

    // Update current index based on scroll position for mobile
    if (this.isMobile && this.container) {
      const containerWidth = this.container.clientWidth;
      const scrollLeft = this.container.scrollLeft;
      const newIndex = Math.round(scrollLeft / containerWidth);

      if (newIndex !== this.currentIndex && newIndex >= 0 && newIndex < this.totalItems) {
        this.currentIndex = newIndex;
      }
    }
  }

  updateButtonStates(): void {
    if (this.container) {
      const maxScrollLeft = this.container.scrollWidth - this.container.clientWidth;
      this.isAtStart = this.container.scrollLeft === 0;
      this.isAtEnd = this.container.scrollLeft >= maxScrollLeft;
    }
  }

  scrollLeft(): void {
    if (this.container && !this.isAtStart) {
      // Scroll by card width (450px) + gap (24px)
      this.container.scrollBy({ left: -474, behavior: 'smooth' });
      setTimeout(() => this.updateButtonStates(), 300);
    }
  }

  scrollRight(): void {
    if (this.container && !this.isAtEnd) {
      // Scroll by card width (450px) + gap (24px)
      this.container.scrollBy({ left: 474, behavior: 'smooth' });
      setTimeout(() => this.updateButtonStates(), 300);
    }
  }

  private handleKeydown(event: KeyboardEvent): void {
    // Handle arrow keys for navigation
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault(); // Prevent default scrolling behavior

      if (event.key === 'ArrowLeft') {
        this.scrollLeft();
      } else if (event.key === 'ArrowRight') {
        this.scrollRight();
      }
    }
  }

  @HostListener('document:keydown', ['$event'])
  onDocumentKeydown(event: KeyboardEvent): void {
    // Only handle if no input/textarea is focused
    const activeElement = document.activeElement;
    const isInputFocused = activeElement instanceof HTMLInputElement ||
                           activeElement instanceof HTMLTextAreaElement;

    if (!isInputFocused && this.container && this.isClosestToViewportCenter()) {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        this.scrollLeft();
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        this.scrollRight();
      }
    }
  }

  private setupIntersectionObserver(): void {
    // Create observer to track when carousel is in viewport and its distance from center
    this.intersectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          this.isInViewport = entry.isIntersecting;

          if (entry.isIntersecting) {
            // Calculate distance from viewport center
            const rect = entry.boundingClientRect;
            const viewportCenter = window.innerHeight / 2;
            const elementCenter = rect.top + rect.height / 2;
            this.viewportCenterDistance = Math.abs(viewportCenter - elementCenter);
          } else {
            this.viewportCenterDistance = Infinity;
          }
        });
      },
      {
        root: null,
        rootMargin: '0px',
        threshold: [0, 0.25, 0.5, 0.75, 1.0] // Multiple thresholds for better tracking
      }
    );

    this.intersectionObserver.observe(this.container);
  }

  private isClosestToViewportCenter(): boolean {
    if (!this.isInViewport) return false;

    // Check all result-list components on the page
    const allCarousels = document.querySelectorAll('.result-container');
    let minDistance = this.viewportCenterDistance;
    let closestElement = this.container;

    allCarousels.forEach(carousel => {
      if (carousel !== this.container) {
        const rect = carousel.getBoundingClientRect();
        const viewportCenter = window.innerHeight / 2;
        const elementCenter = rect.top + rect.height / 2;
        const distance = Math.abs(viewportCenter - elementCenter);

        if (distance < minDistance) {
          minDistance = distance;
          closestElement = carousel as HTMLElement;
        }
      }
    });

    return closestElement === this.container;
  }

  // Resolve which component to render for a given result (per-item resolver wins).
  componentFor(result: T): Type<any> {
    return this.itemComponentResolver ? this.itemComponentResolver(result) : this.itemComponent;
  }

  createInjector(result: T): Injector {
    // Cache injectors to prevent recreation on every change detection
    if (!this.injectorCache.has(result)) {
      const injector = Injector.create({
        providers: [
          { provide: 'RESULT', useValue: result }
        ]
      });
      this.injectorCache.set(result, injector);
    }
    return this.injectorCache.get(result)!;
  }

  // TrackBy function for ngFor to prevent DOM recreation
  trackByFn(index: number, item: any): any {
    // Try to use an id property if available, otherwise use index
    if (item && typeof item === 'object') {
      if ('id' in item) return item.id;
      if ('commentary_result' in item && item.commentary_result?.id) {
        return item.commentary_result.id;
      }
      if ('generictext_result' in item && item.generictext_result?.id) {
        return item.generictext_result.id;
      }
    }
    return index;
  }

  // Mobile-specific methods
  scrollToMobileIndex(index: number): void {
    if (!this.mobileContainer || index < 0 || index >= this.totalItems) return;

    this.currentIndex = index;
    // Use viewport width for consistent mobile card positioning
    const viewportWidth = window.innerWidth;
    const scrollPosition = index * viewportWidth;

    this.mobileContainer.scrollTo({ left: scrollPosition, behavior: 'smooth' });
  }

  navigateMobileCard(direction: 'prev' | 'next'): void {
    const newIndex = direction === 'next'
      ? Math.min(this.currentIndex + 1, this.totalItems - 1)
      : Math.max(this.currentIndex - 1, 0);
    this.scrollToMobileIndex(newIndex);
  }

  onMobileScroll(): void {
    if (this.mobileContainer) {
      const viewportWidth = window.innerWidth;
      const scrollLeft = this.mobileContainer.scrollLeft;
      const newIndex = Math.round(scrollLeft / viewportWidth);

      if (newIndex !== this.currentIndex && newIndex >= 0 && newIndex < this.totalItems) {
        this.currentIndex = newIndex;
      }
    }
  }

  // Swipe gesture handlers
  onSwipeLeft(): void {
    if (this.isMobile) {
      this.navigateMobileCard('next');
    }
  }

  onSwipeRight(): void {
    if (this.isMobile) {
      this.navigateMobileCard('prev');
    }
  }

  onSwipeUp(): void {
    if (this.isMobile) {
      this.verticalSwipe.emit('up');
    }
  }

  onSwipeDown(): void {
    if (this.isMobile) {
      this.verticalSwipe.emit('down');
    }
  }

}
