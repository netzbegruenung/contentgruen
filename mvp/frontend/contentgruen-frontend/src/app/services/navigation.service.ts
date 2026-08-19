import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Location } from '@angular/common';

@Injectable({
  providedIn: 'root'
})
export class NavigationService {
  constructor(
    private router: Router,
    private location: Location
  ) {}

  navigateToStart(): void {
    this.router.navigate(['/']);
  }

  navigateToSearch(): void {
    this.router.navigate(['/search']);
  }

  navigateToResult(searchQuery: string): void {
    this.router.navigate(['/result'], { queryParams: { searchQuery } });
  }

  navigateToContribute(): void {
    this.router.navigate(['/contribute']);
  }

  navigateToContributeWithPanel(panelType: string): void {
    this.router.navigate(['/contribute'], { queryParams: { panel: panelType } });
  }

  navigateToContributions(): void {
    this.router.navigate(['/contributions']);
  }

  navigateToRawInput(): void {
    this.router.navigate(['/einwerfen']);
  }

  navigateToRawInputList(): void {
    this.router.navigate(['/fangkorb']);
  }

  navigateToLogin(): void {
    this.router.navigate(['/login']);
  }

  goBack(): void {
    // Smart back navigation based on current route
    const currentUrl = this.router.url;

    // If on contribute form pages, go back to contribute selection
    if (currentUrl.includes('/contribute') && currentUrl.includes('form=')) {
      this.router.navigate(['/contribute']);
    }
    // If on main contribute page, go to start
    else if (currentUrl === '/contribute') {
      this.navigateToStart();
    }
    // If on results page, go to start
    else if (currentUrl.includes('/result')) {
      this.navigateToStart();
    }
    // If on contributions page, go to start
    else if (currentUrl === '/contributions') {
      this.navigateToStart();
    }
    // Default: use Angular Location service or fallback to start
    else {
      // Try to go back using Location service
      this.location.back();

      // Set a timeout to check if we're still on the same page
      setTimeout(() => {
        if (this.router.url === currentUrl) {
          // If still on same page, navigate to start
          this.navigateToStart();
        }
      }, 100);
    }
  }
}
