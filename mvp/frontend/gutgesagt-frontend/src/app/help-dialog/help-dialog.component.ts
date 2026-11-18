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
import { feedbackDialogOeffnen } from '../shared/feedback/feedback-dialog.component';
import { AuthService } from '../auth/auth.service';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { RundgangService } from '../rundgang/rundgang.service';
import { AppInstallierenService } from '../rundgang/app-installieren.service';
import { RundgangId, rundgangBeschriftung } from '../rundgang/rundgang-daten';
import { EINLADUNG_AB } from '../shared/einladung-ab';
import { SiegelComponent } from '../shared/components/siegel/siegel.component';

/**
 * Rueckkehrziel-Parameter: Nach der Anmeldung aus der Hilfe oeffnet die App sie wieder.
 * Seit Selbst beitragen ohne Konto als Bildergeschichte laeuft (17.11.), setzt die App ihn
 * selbst nicht mehr; Adressen, die ihn noch tragen, wirken weiter.
 */
export const HILFE_PARAM = 'hilfe';

@Component({
  selector: 'app-help-dialog',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    RouterModule,
    NgFor,
    SiegelComponent
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
  readonly angemeldet = !!inject(AuthService).getUserInfo()?.isAuthenticated;
  /** Ohne Konto: „Selbst beitragen (3 Bilder)“, die Bildergeschichte statt der echten Oberfläche. */
  readonly selbstBeitragen = rundgangBeschriftung('mitmachen', this.angemeldet);
  readonly einladungAb = EINLADUNG_AB;

  private readonly rundgang = inject(RundgangService);
  private readonly dialog = inject(MatDialog);
  /** Derselbe Stand wie im Band: Knopf nur mit Angebot des Browsers, sonst die Anleitung. */
  readonly app = inject(AppInstallierenService);

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

  /**
   * Links aus der Hilfe auf die Über-Seite, auch mit Anker (/about#siegel, /about#technik).
   * Wie früher „Über Gut gesagt“: erst schliessen, dann navigieren. Die Navigation wartet, bis
   * die Hilfe zu ist, denn beim Schliessen stellt der Dialog die alte Scrollposition wieder her
   * und hebt sonst den Sprung zum Anker auf. Mit Strg/Cmd/Umschalt öffnet der Browser das href.
   */
  zuUeber(event: MouseEvent, fragment?: string): void {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    this.dialogRef.afterClosed().subscribe(() => void this.router.navigate(['/about'], { fragment }));
    this.dialogRef.close();
  }

  /** Dialog des Browsers; der Abschnitt zeigt danach „schon als App“ oder wieder die Anleitung. */
  installieren(): void {
    void this.app.installieren();
  }

  /** Feedback über der Hilfe; nach dem Absenden oder Abbrechen ist die Hilfe wieder da. */
  feedbackOeffnen(): void {
    feedbackDialogOeffnen(this.dialog);
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
