import { Directive, ElementRef, EventEmitter, HostListener, Output } from '@angular/core';

@Directive({
  selector: '[appSwipeGesture]',
  standalone: true
})
export class SwipeGestureDirective {
  @Output() swipeLeft = new EventEmitter<void>();
  @Output() swipeRight = new EventEmitter<void>();
  @Output() swipeUp = new EventEmitter<void>();
  @Output() swipeDown = new EventEmitter<void>();

  private touchStartX = 0;
  private touchStartY = 0;
  private touchEndX = 0;
  private touchEndY = 0;
  private minSwipeDistance = 50; // Minimum distance for a swipe to register
  private maxSwipeTime = 500; // Maximum time for a swipe gesture
  private touchStartTime = 0;

  constructor(private el: ElementRef) {}

  @HostListener('touchstart', ['$event'])
  onTouchStart(event: TouchEvent): void {
    this.touchStartX = event.changedTouches[0].screenX;
    this.touchStartY = event.changedTouches[0].screenY;
    this.touchStartTime = Date.now();
  }

  @HostListener('touchend', ['$event'])
  onTouchEnd(event: TouchEvent): void {
    this.touchEndX = event.changedTouches[0].screenX;
    this.touchEndY = event.changedTouches[0].screenY;

    const swipeTime = Date.now() - this.touchStartTime;

    // Only process if the gesture was quick enough
    if (swipeTime <= this.maxSwipeTime) {
      this.handleSwipe();
    }
  }

  @HostListener('touchmove', ['$event'])
  onTouchMove(event: TouchEvent): void {
    // Update end position during move for smoother tracking
    this.touchEndX = event.changedTouches[0].screenX;
    this.touchEndY = event.changedTouches[0].screenY;
  }

  private handleSwipe(): void {
    const deltaX = this.touchEndX - this.touchStartX;
    const deltaY = this.touchEndY - this.touchStartY;
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);

    // Determine if this is a horizontal or vertical swipe
    if (absDeltaX > absDeltaY) {
      // Horizontal swipe
      if (absDeltaX >= this.minSwipeDistance) {
        if (deltaX > 0) {
          this.swipeRight.emit();
        } else {
          this.swipeLeft.emit();
        }
      }
    } else {
      // Vertical swipe
      if (absDeltaY >= this.minSwipeDistance) {
        if (deltaY > 0) {
          this.swipeDown.emit();
        } else {
          this.swipeUp.emit();
        }
      }
    }
  }

  // Mouse events for desktop testing
  private mouseStartX = 0;
  private mouseStartY = 0;
  private isMouseDown = false;

  @HostListener('mousedown', ['$event'])
  onMouseDown(event: MouseEvent): void {
    // Only process if it's not a touch device
    if (!('ontouchstart' in window)) {
      this.isMouseDown = true;
      this.mouseStartX = event.screenX;
      this.mouseStartY = event.screenY;
      this.touchStartTime = Date.now();
      event.preventDefault();
    }
  }

  @HostListener('mouseup', ['$event'])
  onMouseUp(event: MouseEvent): void {
    if (this.isMouseDown && !('ontouchstart' in window)) {
      this.isMouseDown = false;
      const deltaX = event.screenX - this.mouseStartX;
      const deltaY = event.screenY - this.mouseStartY;
      const swipeTime = Date.now() - this.touchStartTime;

      if (swipeTime <= this.maxSwipeTime) {
        this.touchStartX = this.mouseStartX;
        this.touchStartY = this.mouseStartY;
        this.touchEndX = event.screenX;
        this.touchEndY = event.screenY;
        this.handleSwipe();
      }
    }
  }

  @HostListener('mouseleave')
  onMouseLeave(): void {
    this.isMouseDown = false;
  }
}
