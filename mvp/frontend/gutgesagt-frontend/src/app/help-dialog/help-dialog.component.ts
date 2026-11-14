import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgFor } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { NavigationEnd, Router, RouterModule } from '@angular/router';
import { combineLatest } from 'rxjs';
import { filter, map } from 'rxjs/operators';
import { CONTENT_TYPE_REGISTRY } from '../shared/content-type-registry';
import { ERFUNDENES_MELDEN, NICHT_JEDE_AUSSAGE, SCHREIBREGELN } from '../shared/schreibregeln';
import { KEINE_GENERATIVE_KI, SUCHE_MIT_SPRACHMODELLEN } from '../shared/ki-saetze';
import { AuthService } from '../auth/auth.service';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { RundgangService } from '../rundgang/rundgang.service';
import { RundgangId, rundgangBeschriftung } from '../rundgang/rundgang-daten';

/** Rueckkehrziel-Parameter: Nach der Anmeldung aus der Hilfe oeffnet die App sie wieder. */
export const HILFE_PARAM = 'hilfe';

/** Steht für Besucher unter dem ausgegrauten Rundgang Selbst beitragen. */
export const MITMACHEN_HINWEIS = 'Nach der Anmeldung zeigen wir dir, wie Beitragen geht.';

@Component({
  selector: 'app-help-dialog',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    RouterModule,
    NgFor
  ],
  templateUrl: './help-dialog.component.html',
  styleUrls: ['../rundgang/rundgang-knoepfe.css', './help-dialog.component.css']
})
export class HelpDialogComponent {
  readonly typen = (['commentary', 'generictext', 'image', 'post'] as const).map((key) => ({
    ...CONTENT_TYPE_REGISTRY[key],
    artikel: key === 'generictext' ? 'eine' : 'ein',
  }));

  // Dieselben Saetze wie in der Formularhilfe
  readonly schreibregeln = SCHREIBREGELN;
  readonly nichtJedeAussage = NICHT_JEDE_AUSSAGE;
  readonly erfundenesMelden = ERFUNDENES_MELDEN;
  readonly keineGenerativeKi = KEINE_GENERATIVE_KI;
  readonly sucheMitSprachmodellen = SUCHE_MIT_SPRACHMODELLEN;

  readonly antwortFinden = rundgangBeschriftung('antwort-finden');
  readonly selbstBeitragen = rundgangBeschriftung('mitmachen');
  readonly mitmachenHinweis = MITMACHEN_HINWEIS;

  private readonly rundgang = inject(RundgangService);
  readonly angemeldet = !!inject(AuthService).getUserInfo()?.isAuthenticated;

  constructor(
    private dialogRef: MatDialogRef<HelpDialogComponent>,
    private router: Router
  ) {}

  /**
   * Schliesst erst die Hilfe, dann startet der Rundgang: Sonst holte die Hilfe beim
   * Schliessen den Fokus zurueck auf ihren Knopf, weg von der Sprechblase.
   */
  rundgangStarten(id: RundgangId): void {
    this.dialogRef.afterClosed().subscribe(() => void this.rundgang.starten(id));
    this.dialogRef.close();
  }

  /** Zur Anmeldung; danach zurück auf diese Seite mit offener Hilfe (hilfeNachAnmeldung). */
  anmelden(): void {
    this.dialogRef.close();
    anmeldenZurHilfe(this.router);
  }

  navigateToAbout(): void {
    this.dialogRef.close();
    this.router.navigate(['/about']);
  }
}

/**
 * Oeffnet die Hilfe als Seitenleiste rechts in voller Hoehe, 560 px breit; schmaler
 * als 560 px wird daraus ein Vollbild (#512). Fokus auf dem Dialog selbst: Sonst
 * fokussierte Material den ersten Link und scrollte ans Ende.
 */
export function hilfeOeffnen(dialog: MatDialog): MatDialogRef<HelpDialogComponent> {
  return dialog.open(HelpDialogComponent, {
    autoFocus: 'dialog',
    position: { top: '0', right: '0' },
    width: '560px',
    maxWidth: '100vw',
    height: '100%',
    maxHeight: '100%',
    panelClass: 'hilfe-seitenleiste',
  });
}

/**
 * Zur Anmeldung mit der jetzigen Seite als Rückkehrziel, ergänzt um HILFE_PARAM: Danach
 * öffnet die App die Hilfe (hilfeNachAnmeldung), dort startet Selbst beitragen. Aus der
 * Hilfe und aus dem mobilen Menü.
 */
export function anmeldenZurHilfe(router: Router): void {
  // Schon auf der Anmeldung (Hilfe dort geöffnet): deren Rückkehrziel bleibt, wie bei
  // AppComponent.loginWithReturnUrl
  if (router.url.startsWith('/login')) return;
  const hier = router.parseUrl(router.url);
  hier.queryParams = { ...hier.queryParams, [HILFE_PARAM]: '1' };
  void router.navigate(['/login'], { queryParams: { returnUrl: router.serializeUrl(hier) } });
}

/**
 * Öffnet die Hilfe wieder, wenn die Anmeldung aus ihr kam (Parameter HILFE_PARAM), und
 * nimmt den Parameter aus der Adresse. Erst, wenn feststeht, wer da ist, und bei
 * Angemeldeten nach der Art.-9-Einwilligung: Sonst läge die Hilfe über deren Seite.
 */
export function hilfeNachAnmeldung(destroyRef: DestroyRef): void {
  const router = inject(Router);
  const dialog = inject(MatDialog);
  const auth = inject(AuthService);
  const einwilligung = inject(Art9EinwilligungService);
  const adresse$ = router.events.pipe(
    filter((e): e is NavigationEnd => e instanceof NavigationEnd),
    map((e) => router.parseUrl(e.urlAfterRedirects)),
  );
  combineLatest([adresse$, auth.userInfo$, einwilligung.geklaert$])
    .pipe(
      filter(([adresse, info, geklaert]) =>
        adresse.queryParamMap.has(HILFE_PARAM) && !!info && (!info.isAuthenticated || geklaert === info.userId),
      ),
      takeUntilDestroyed(destroyRef),
    )
    .subscribe(() => {
      void router.navigate([], { queryParams: { [HILFE_PARAM]: null }, queryParamsHandling: 'merge', replaceUrl: true });
      if (!dialog.openDialogs.some((d) => d.componentInstance instanceof HelpDialogComponent)) hilfeOeffnen(dialog);
    });
}
