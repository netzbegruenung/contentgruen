import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { BehaviorSubject, Observable, tap } from 'rxjs';

export interface UserInfo {
  isAuthenticated: boolean;
  userId: string | null;
  userName: string | null;
  isAdmin?: boolean;
  claims: { [key: string]: string } | null;
}

export interface LoginResponse {
  userId: string;
  userName: string;
  success: boolean;
  message?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private userInfoSubject = new BehaviorSubject<UserInfo | null>(null);
  userInfo$ = this.userInfoSubject.asObservable()

  constructor(private http: HttpClient, private router: Router) { }

  login() {
    // Always navigate to the login selector page
    // The selector will determine which auth methods are available
    this.router.navigate(['/login']);
  }

  // Dummy login with username and password (backward compatibility)
  loginWithCredentials(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${environment.baseUrl}/login`, { Username: username, Password: password }, {
      withCredentials: true // Ensure cookies are sent/received
    }).pipe(
      tap((response) => {
        // Use the response data if available, then fetch full user info
        if (response?.userId) {
          // Set temporary user info from login response
          const tempUserInfo: UserInfo = {
            isAuthenticated: true,
            userId: response.userId,
            userName: response.userName,
            claims: null
          };
          this.setUserInfo(tempUserInfo);
        }
        // Fetch complete user info after a short delay to ensure cookie is set
        setTimeout(() => {
          this.fetchUserInfo().subscribe();
        }, 100);
      })
    );
  }

  // ContentGrün managed login with email and password
  loginWithManagedAuth(email: string, password: string): Observable<any> {
    return this.http.post<any>(`${environment.baseUrl}/api/auth/login/managed`, { email, password }, {
      withCredentials: true // Ensure cookies are sent/received
    }).pipe(
      tap((response) => {
        // Use the response data if available, then fetch full user info
        if (response?.userId) {
          // Set temporary user info from login response
          const tempUserInfo: UserInfo = {
            isAuthenticated: true,
            userId: response.userId,
            userName: response.userName || response.displayName,
            claims: null
          };
          this.setUserInfo(tempUserInfo);
        }
        // Fetch complete user info after a short delay to ensure cookie is set
        setTimeout(() => {
          this.fetchUserInfo().subscribe();
        }, 100);
      })
    );
  }

  // Check available authentication modes
  getAuthModes(): Observable<any> {
    return this.http.get<any>(`${environment.baseUrl}/api/auth/modes`);
  }

  logout() {
    // Use the API logout endpoint which properly handles both Keycloak and managed users
    this.http.post(`${environment.baseUrl}/api/auth/logout`, {}, {
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        // Clear local user info
        this.setUserInfo({ isAuthenticated: false, userId: null, userName: null, claims: null });

        // Navigate to home or login page
        const redirectUrl = response?.redirectUrl || '/';
        window.location.href = redirectUrl.startsWith('http') ? redirectUrl : `${window.location.origin}${redirectUrl}`;
      },
      error: (err) => {
        console.error('Logout failed:', err);
        // Fallback to clearing user info and redirecting
        this.setUserInfo({ isAuthenticated: false, userId: null, userName: null, claims: null });
        this.router.navigate(['/']);
      }
    });
  }

  fetchUserInfo(): Observable<UserInfo> {
    return this.http.get<UserInfo>(`${environment.baseUrl}/api/user-info`, {
      withCredentials: true // Ensure cookies are sent
    }).pipe(
      tap((userInfo) => this.userInfoSubject.next(userInfo)) // Update user info
    );
  }

  setUserInfo(userInfo: UserInfo) {
    this.userInfoSubject.next(userInfo);
  }

  getUserInfo(): UserInfo | null {
    return this.userInfoSubject.value;
  }

  getCurrentUserId(): string | null {
    const userInfo = this.getUserInfo();
    return userInfo?.userId || null;
  }
}
