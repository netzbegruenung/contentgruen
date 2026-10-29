import { ApplicationConfig, provideZoneChangeDetection, ErrorHandler, provideAppInitializer } from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { routes } from './app.routes';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { AuthInterceptor } from './auth/auth.interceptor';
import { cacheInterceptor } from './auth/cache.interceptor';
import { GlobalErrorHandler } from './services/error-handler.service';
import { alteSitzungskennungEntfernen } from './services/alte-sitzungskennung';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes, withInMemoryScrolling({
      scrollPositionRestoration: 'top',
      anchorScrolling: 'enabled'
    })),
    provideAnimations(),
    provideHttpClient(withInterceptors([AuthInterceptor, cacheInterceptor])),
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    // Keine Kennung im Browser (#446): was fruehere Versionen ablegten, kommt weg.
    provideAppInitializer(() => alteSitzungskennungEntfernen())
  ]
};
