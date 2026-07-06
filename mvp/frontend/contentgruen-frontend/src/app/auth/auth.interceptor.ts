// src/app/auth/auth.interceptor.ts
import { HttpRequest, HttpHandlerFn, HttpEvent, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { PublicEndpoints } from '../shared/public-endpoints';

export const AuthInterceptor: HttpInterceptorFn = (req: HttpRequest<any>, next: HttpHandlerFn): Observable<HttpEvent<any>> => {
  const router = inject(Router);  // Inject Router for navigation

  const modifiedRequest = req.clone({
    withCredentials: true,  // Ensures cookies are included also cross-origin
  });

  return next(modifiedRequest).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        // Check if the request is for a public endpoint
        if (!PublicEndpoints.isPublicEndpoint(req.url)) {
          // Redirect to login with current URL as return URL for protected endpoints
          const currentUrl = window.location.pathname + window.location.search;
          router.navigate(['/login'], { queryParams: { returnUrl: currentUrl } });
        }
      }
      return throwError(() => error);  // Pass error along to be handled if needed
    })
  );
};
