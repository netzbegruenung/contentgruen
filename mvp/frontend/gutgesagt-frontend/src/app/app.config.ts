import { ApplicationConfig, provideZoneChangeDetection, ErrorHandler } from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { routes } from './app.routes';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { AuthInterceptor } from './auth/auth.interceptor';
import { cacheInterceptor } from './auth/cache.interceptor';
import { GlobalErrorHandler } from './services/error-handler.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes, withInMemoryScrolling({
      scrollPositionRestoration: 'top',
      anchorScrolling: 'enabled'
    })),
    provideAnimations(),
    provideHttpClient(withInterceptors([AuthInterceptor, cacheInterceptor])),
    { provide: ErrorHandler, useClass: GlobalErrorHandler }
  ]
};
