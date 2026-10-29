import { Component } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AuthService } from '../auth/auth.service';
import { rueckkehrzielLesen, rueckkehrzielLoeschen, rueckkehrzielMerken } from './rueckkehrziel';
import { SHARED_IMPORTS } from '../shared/shared-imports';


@Component({
    selector: 'app-login',
    standalone: true,
    imports: SHARED_IMPORTS,
    templateUrl: './login.component.html',
    styleUrls: ['./login.component.css']
})
export class LoginComponent {
    loginForm: FormGroup;
    errorMessage: string | null = null;
    isLoading = false;
    isManagedLogin = false; // Flag to determine if this is managed login
    returnUrl: string = '/';

    constructor(
        private authService: AuthService,
        private router: Router,
        private route: ActivatedRoute,
        private fb: FormBuilder,
        private snackBar: MatSnackBar
    ) {
        // Get return URL from route parameters or sessionStorage or default to '/'
        const queryReturnUrl = this.route.snapshot.queryParams['returnUrl'];
        if (queryReturnUrl) {
            // Stored only if it is a real target (not '/' and not a login page URL)
            rueckkehrzielMerken(queryReturnUrl);
            this.returnUrl = queryReturnUrl;
        } else {
            // Try to get from sessionStorage if not in query params
            // This ensures the returnUrl persists through failed login attempts
            this.returnUrl = rueckkehrzielLesen() || '/';
        }

        // Clean up any login page URLs that might have slipped through
        if (this.returnUrl.startsWith('/login')) {
            this.returnUrl = '/';
        }

        // Check if this is managed login based on route
        this.isManagedLogin = this.router.url.includes('/managed');

        this.loginForm = this.fb.group({
            username: ['', this.isManagedLogin ? [] : [Validators.required, Validators.minLength(3)]],
            email: ['', this.isManagedLogin ? [Validators.required, Validators.email] : []],
            password: ['', [Validators.required, Validators.minLength(6)]]
        });
    }

    onLogin() {
        if (this.loginForm.invalid) {
            this.loginForm.markAllAsTouched();
            return;
        }

        this.isLoading = true;

        if (this.isManagedLogin) {
            // Gut gesagt managed login
            const { email, password } = this.loginForm.value;

            this.authService.loginWithManagedAuth(email, password).subscribe({
                next: () => {
                    this.isLoading = false;
                    this.snackBar.open('Anmeldung erfolgreich!', 'OK', {
                        duration: 3000,
                        panelClass: ['success-snackbar']
                    });
                    // Clear the stored return URL after successful login
                    rueckkehrzielLoeschen();
                    this.router.navigateByUrl(this.returnUrl);
                },
                error: (err) => {
                    this.isLoading = false;
                    this.errorMessage = 'Ungültige E-Mail-Adresse oder Passwort';
                    this.snackBar.open('Anmeldung fehlgeschlagen. Bitte überprüfe deine Eingaben.', 'OK', {
                        duration: 5000,
                        panelClass: ['error-snackbar']
                    });
                },
            });
        } else {
            // Legacy dummy login
            const { username, password } = this.loginForm.value;

            this.authService.loginWithCredentials(username, password).subscribe({
                next: () => {
                    this.isLoading = false;
                    this.snackBar.open('Anmeldung erfolgreich!', 'OK', {
                        duration: 3000,
                        panelClass: ['success-snackbar']
                    });
                    // Clear the stored return URL after successful login
                    rueckkehrzielLoeschen();
                    this.router.navigateByUrl(this.returnUrl);
                },
                error: (err) => {
                    this.isLoading = false;
                    this.errorMessage = 'Ungültiger Benutzername oder Passwort';
                    this.snackBar.open('Anmeldung fehlgeschlagen. Bitte überprüfe deine Eingaben.', 'OK', {
                        duration: 5000,
                        panelClass: ['error-snackbar']
                    });
                },
            });
        }
    }

    getErrorMessage(field: string): string {
        const control = this.loginForm.get(field);
        if (control?.hasError('required')) {
            if (field === 'username') return 'Benutzername ist erforderlich';
            if (field === 'email') return 'E-Mail-Adresse ist erforderlich';
            if (field === 'password') return 'Passwort ist erforderlich';
        }
        if (control?.hasError('email')) {
            return 'Gültige E-Mail-Adresse erforderlich';
        }
        if (control?.hasError('minlength')) {
            const minLength = control.errors?.['minlength'].requiredLength;
            return `Mindestens ${minLength} Zeichen erforderlich`;
        }
        return '';
    }

    navigateToStart(): void {
        this.router.navigate(['/']);
      }
}
