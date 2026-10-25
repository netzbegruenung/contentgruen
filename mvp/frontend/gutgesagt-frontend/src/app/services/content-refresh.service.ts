import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { LoggingService } from './logging.service';

@Injectable({
  providedIn: 'root'
})
export class ContentRefreshService {
  private refreshSubject = new Subject<void>();
  public refresh$ = this.refreshSubject.asObservable();

  constructor(private logger: LoggingService) {
    // Log subscribers count periodically (for debugging)
    this.refresh$.subscribe({
      next: () => {
        this.logger.debug('[ContentRefreshService] Refresh signal emitted to subscribers');
      }
    });
  }

  triggerRefresh(): void {
    const timestamp = new Date().toISOString();
    this.logger.info(`[${timestamp}] === CONTENT REFRESH SERVICE: triggerRefresh() called ===`);
    this.logger.debug('Number of observers:', (this.refreshSubject as any).observers?.length || 0);
    this.refreshSubject.next();
    this.logger.debug('Refresh signal emitted');
  }
}
