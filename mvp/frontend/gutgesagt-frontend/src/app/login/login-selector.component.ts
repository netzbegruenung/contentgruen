import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { anmeldegrund, rueckkehrzielLesen, rueckkehrzielMerken } from './rueckkehrziel';
import { keycloakAnmelden } from './keycloak-anmeldung';
import { MatDialog } from '@angular/material/dialog';
import { feedbackDialogOeffnen } from '../shared/feedback/feedback-dialog.component';
import { ORGANISATION } from '../shared/organisation';
import { EINLADUNG_AB } from '../shared/einladung-ab';

/** Vorbelegt im Feedback-Dialog, damit die Warteliste von anderem Feedback zu trennen ist. */
export const WARTELISTE_TEXT = 'Bitte setzt mich auf die Warteliste für eine Einladung.';

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
  /** Wozu die Anmeldung nötig ist, aus dem Ziel; null zeigt keinen Satz (#600). */
  anmeldegrund: string | null = null;
  readonly organisation = ORGANISATION;
  readonly einladungAb = EINLADUNG_AB;

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private http: HttpClient,
    private dialog: MatDialog
  ) {
    // Get return URL from route parameters or sessionStorage or default to '/'
    const queryReturnUrl = this.route.snapshot.queryParams['returnUrl'];
    if (queryReturnUrl && !queryReturnUrl.startsWith('/login')) {
      // Store in sessionStorage to preserve through navigation ('/' is not stored)
      rueckkehrzielMerken(queryReturnUrl);
      this.returnUrl = queryReturnUrl;
    } else {
      // No query parameter, or a login URL to ignore: fall back to the stored target
      this.returnUrl = rueckkehrzielLesen() || '/';
    }
    this.anmeldegrund = anmeldegrund(this.returnUrl);
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

          // No auto-redirect; only the enabled login options are shown (#600)
          // This ensures users always see the registration information
        },
        error: (err) => {
          console.error('Failed to fetch auth modes:', err);
          // Unknown modes: offer both ways instead of hiding the one this environment uses (#600)
          this.authModes = { keycloakEnabled: true, managedAuthEnabled: true };
          this.isLoading = false;
        }
      });
  }

  loginWithKeycloak(): void {
    keycloakAnmelden(this.returnUrl);
  }

  loginWithGutGesagt(): void {
    // Navigate to Gut gesagt managed login with return URL
    this.router.navigate(['/login/managed'], { queryParams: { returnUrl: this.returnUrl } });
  }

  navigateToStart(): void {
    this.router.navigate(['/']);
  }

  /** Warteliste fuer Einladungen ueber den Feedback-Dialog, Text vorbelegt (Designrunde 17.11.). */
  aufWarteliste(): void {
    feedbackDialogOeffnen(this.dialog, WARTELISTE_TEXT);
  }
}
