import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten } from '../beitragskarte/karten-daten';

/** Kartenbreite (450 px) plus Abstand (24 px). */
const SCROLL_SCHRITT = 474;

/**
 * Horizontales Karussell voller Beitragskarten, nur ab 600 px.
 *
 * Mobil zeigen Startseite und Suche stattdessen eine Liste (app-kartenliste). Die
 * Karten sind unterschiedlich hoch; die Reihe gleicht sie ueber align-items:
 * stretch an, eine feste Hoehe gibt es nicht.
 */
@Component({
  selector: 'app-result-carousel',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatTooltipModule, BeitragskarteComponent],
  templateUrl: './result-carousel.component.html',
  styleUrls: ['./result-carousel.component.css'],
})
export class ResultCarouselComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() daten: KartenDaten[] = [];

  @ViewChild('resultContainer', { static: true }) resultContainerRef!: ElementRef<HTMLElement>;

  isAtStart = true;
  isAtEnd = false;

  private intersectionObserver?: IntersectionObserver;
  private isInViewport = false;
  private viewportCenterDistance = Infinity;
  private readonly scrollListener = () => this.updateButtonStates();
  private readonly keydownListener = (event: KeyboardEvent) => this.handleKeydown(event);

  private get container(): HTMLElement {
    return this.resultContainerRef.nativeElement;
  }

  ngAfterViewInit(): void {
    const isEdge = navigator.userAgent.includes('Edg');
    this.container.style.scrollSnapType = isEdge ? 'none' : 'x mandatory';
    this.container.tabIndex = 0;
    this.container.addEventListener('keydown', this.keydownListener);
    this.container.addEventListener('scroll', this.scrollListener);
    this.setupIntersectionObserver();
    setTimeout(() => this.updateButtonStates(), 100);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['daten']) {
      setTimeout(() => this.updateButtonStates(), 50);
    }
  }

  ngOnDestroy(): void {
    this.container.removeEventListener('scroll', this.scrollListener);
    this.container.removeEventListener('keydown', this.keydownListener);
    this.intersectionObserver?.disconnect();
  }

  nachId(_index: number, karte: KartenDaten): string {
    return karte.id;
  }

  updateButtonStates(): void {
    const maxScrollLeft = this.container.scrollWidth - this.container.clientWidth;
    this.isAtStart = this.container.scrollLeft === 0;
    this.isAtEnd = this.container.scrollLeft >= maxScrollLeft;
  }

  scrollLeft(): void {
    if (!this.isAtStart) {
      this.container.scrollBy({ left: -SCROLL_SCHRITT, behavior: 'smooth' });
      setTimeout(() => this.updateButtonStates(), 300);
    }
  }

  scrollRight(): void {
    if (!this.isAtEnd) {
      this.container.scrollBy({ left: SCROLL_SCHRITT, behavior: 'smooth' });
      setTimeout(() => this.updateButtonStates(), 300);
    }
  }

  @HostListener('document:keydown', ['$event'])
  onDocumentKeydown(event: KeyboardEvent): void {
    const activeElement = document.activeElement;
    const isInputFocused =
      activeElement instanceof HTMLInputElement || activeElement instanceof HTMLTextAreaElement;

    if (!isInputFocused && this.isClosestToViewportCenter()) {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        this.scrollLeft();
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        this.scrollRight();
      }
    }
  }

  private handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      this.scrollLeft();
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      this.scrollRight();
    }
  }

  private setupIntersectionObserver(): void {
    this.intersectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          this.isInViewport = entry.isIntersecting;
          if (entry.isIntersecting) {
            const rect = entry.boundingClientRect;
            this.viewportCenterDistance = Math.abs(window.innerHeight / 2 - (rect.top + rect.height / 2));
          } else {
            this.viewportCenterDistance = Infinity;
          }
        });
      },
      { root: null, rootMargin: '0px', threshold: [0, 0.25, 0.5, 0.75, 1.0] },
    );
    this.intersectionObserver.observe(this.container);
  }

  /** Bei mehreren Karussells auf der Seite reagiert nur das mittigste auf die Pfeiltasten. */
  private isClosestToViewportCenter(): boolean {
    if (!this.isInViewport) {
      return false;
    }
    let minDistance = this.viewportCenterDistance;
    let closestElement: Element = this.container;

    document.querySelectorAll('.result-container').forEach((carousel) => {
      if (carousel !== this.container) {
        const rect = carousel.getBoundingClientRect();
        const distance = Math.abs(window.innerHeight / 2 - (rect.top + rect.height / 2));
        if (distance < minDistance) {
          minDistance = distance;
          closestElement = carousel;
        }
      }
    });

    return closestElement === this.container;
  }
}
