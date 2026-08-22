import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

interface AuthModes {
  keycloakEnabled: boolean;
  managedAuthEnabled: boolean;
}

@Component({
  selector: 'app-login-selector',
  standalone: true,
  imports: SHARED_IMPORTS,
  templateUrl: './login-selector.component.html',
  styleUrls: ['./login-selector.component.css']
})
export class LoginSelectorComponent implements OnInit {
  authModes: AuthModes = {
    keycloakEnabled: false,
    managedAuthEnabled: false
  };
  isLoading = true;
  returnUrl: string = '/';
  isRegistrationInfoExpanded = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private http: HttpClient
  ) {
    // Get return URL from route parameters or sessionStorage or default to '/'
    const queryReturnUrl = this.route.snapshot.queryParams['returnUrl'];
    if (queryReturnUrl && !queryReturnUrl.startsWith('/login')) {
      // Store in sessionStorage to preserve through navigation (but not login URLs)
      sessionStorage.setItem('loginReturnUrl', queryReturnUrl);
      this.returnUrl = queryReturnUrl;
    } else if (!queryReturnUrl) {
      // Try to get from sessionStorage if not in query params
      this.returnUrl = sessionStorage.getItem('loginReturnUrl') || '/';
    } else {
      // queryReturnUrl is a login URL, ignore it
      this.returnUrl = sessionStorage.getItem('loginReturnUrl') || '/';
    }
  }

  ngOnInit(): void {
    this.checkAuthModes();
  }

  checkAuthModes(): void {
    this.http.get<AuthModes>(`${environment.baseUrl}/api/auth/modes`)
      .subscribe({
        next: (modes) => {
          this.authModes = modes;
          this.isLoading = false;

          // Always show both options - no auto-redirect
          // This ensures users always see the registration information
        },
        error: (err) => {
          console.error('Failed to fetch auth modes:', err);
          // Default to Gut gesagt login on error
          this.authModes.managedAuthEnabled = true;
          this.isLoading = false;
        }
      });
  }

  loginWithKeycloak(): void {
    // Store return URL in session storage for Keycloak redirect (use consistent key)
    sessionStorage.setItem('loginReturnUrl', this.returnUrl);
    // Redirect to Keycloak login through the API endpoint
    window.location.href = `${environment.baseUrl}/api/auth/login/keycloak`;
  }

  loginWithGutGesagt(): void {
    // Navigate to Gut gesagt managed login with return URL
    this.router.navigate(['/login/managed'], { queryParams: { returnUrl: this.returnUrl } });
  }

  navigateToStart(): void {
    this.router.navigate(['/']);
  }

  getMailtoLink(): string {
    const email = 'accounts@contentgruen.de';
    const subject = 'Beta-Account Anfrage';
    return `mailto:${email}?subject=${encodeURIComponent(subject)}`;
  }
}
