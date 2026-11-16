import { ApplicationConfig, provideZoneChangeDetection, ErrorHandler, provideAppInitializer, inject } from '@angular/core';
import { provideRouter, withInMemoryScrolling, withNavigationErrorHandler } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { routes } from './app.routes';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { AuthInterceptor } from './auth/auth.interceptor';
import { cacheInterceptor } from './auth/cache.interceptor';
import { GlobalErrorHandler } from './services/error-handler.service';
import { alteSitzungskennungEntfernen } from './services/alte-sitzungskennung';
import { NeueVersionService } from './shared/neue-version';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes, withInMemoryScrolling({
      scrollPositionRestoration: 'top',
      anchorScrolling: 'enabled'
    }),
    // Nach einem Deploy fehlen die alten Chunks: hart auf das Ziel, das holt die neue Version.
    withNavigationErrorHandler((fehler) => inject(NeueVersionService).beiNavigationsfehler(fehler))),
    provideAnimations(),
    provideHttpClient(withInterceptors([AuthInterceptor, cacheInterceptor])),
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    // Keine Sitzungskennung im Browser (#446): was fruehere Versionen ablegten, kommt weg.
    provideAppInitializer(() => alteSitzungskennungEntfernen()),
    // Der Merker eines automatischen Neuladens (Schleifensperre) faellt nach zehn Minuten.
    provideAppInitializer(() => inject(NeueVersionService).aufraeumen())
  ]
};
