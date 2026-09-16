import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, Router } from '@angular/router';

import { ElternZiel } from '../app.routes';

/** Wohin der Pfeil faellt, wenn eine Route kein Elternziel nennt. */
const STANDARD_ZIEL = '/search';

@Injectable({
  providedIn: 'root'
})
export class NavigationService {
  private vorZurueck: (() => Promise<void>) | null = null;

  constructor(
    private router: Router
  ) {}

  navigateToStart(): void {
    this.router.navigate(['/']);
  }

  navigateToSearch(): void {
    this.router.navigate(['/search']);
  }

  navigateToResult(searchQuery: string): void {
    this.router.navigate(['/result'], { queryParams: { searchQuery } });
  }

  navigateToContribute(): void {
    this.router.navigate(['/contribute']);
  }

  navigateToContributeWithPanel(panelType: string): void {
    this.router.navigate(['/contribute'], { queryParams: { panel: panelType } });
  }

  navigateToContributions(): void {
    this.router.navigate(['/contributions']);
  }

  navigateToRawInput(): void {
    this.router.navigate(['/einwerfen']);
  }

  navigateToRawInputList(): void {
    this.router.navigate(['/fangkorb']);
  }

  navigateToLogin(): void {
    this.router.navigate(['/login']);
  }

  /**
   * Eine Ebene hoeher in der Hierarchie - immer dasselbe Ziel je Route, nie der
   * letzte Schritt der History.
   *
   * Das Ziel steht als ``data.parent`` an der Route (siehe app.routes.ts). Frueher
   * stand hier eine if-Kette mit vier Sonderfaellen und ``location.back()`` als
   * Default; das machte den Pfeil vom Weg abhaengig, auf dem jemand kam, und
   * fuehrte bei direkt geoeffneten Adressen aus der App heraus.
   *
   * Das System-Zurueck (Browser-Knopf, Android-Geste) bleibt History-basiert -
   * das ist Plattformverhalten und wird hier nicht angefasst.
   */
  /**
   * Was eine Seite erledigen will, bevor der Pfeil sie verlaesst - die
   * Destillier-Ansicht etwa speichert den Satz. Genau eine Seite ist zugleich
   * sichtbar, deshalb reicht ein Platz.
   */
  registerBeforeBack(fn: () => Promise<void>): void {
    this.vorZurueck = fn;
  }

  /**
   * Beim Verlassen wieder abmelden. Mit Funktion nur, wenn es die eigene ist -
   * sonst raeumt eine Seite beim Zerstoeren die Anmeldung ihrer Nachfolgerin weg
   * (Angular baut die neue Ansicht vor dem Zerstoeren der alten auf).
   */
  unregisterBeforeBack(fn?: () => Promise<void>): void {
    if (!fn || this.vorZurueck === fn) {
      this.vorZurueck = null;
    }
  }

  /**
   * Scheitert das Vorher-Erledigen, bleibt man stehen: Die Seite meldet den
   * Fehler selbst, und ein ungespeicherter Satz geht nicht dabei verloren, dass
   * der Pfeil trotzdem navigiert.
   */
  async goBack(): Promise<void> {
    if (this.vorZurueck) {
      try {
        await this.vorZurueck();
      } catch {
        return;
      }
    }
    const offen = this.offenerUnterScreen();
    if (offen) {
      this.unterScreenSchliessen(offen);
      return;
    }

    const ziel = this.elternZiel();
    if (Array.isArray(ziel)) {
      this.router.navigate(ziel);
      return;
    }
    this.router.navigateByUrl(ziel);
  }

  /**
   * Der erste Query-Parameter aus ``data.schliesst``, der gerade gesetzt ist -
   * also ein offener Unter-Screen auf dieser Seite.
   */
  private offenerUnterScreen(): string | null {
    for (const eintrag of this.ketteAbwaerts().reverse()) {
      const namen = eintrag.data?.['schliesst'] as string[] | undefined;
      const offen = namen?.find((name) => eintrag.queryParamMap.get(name));
      if (offen) {
        return offen;
      }
    }
    return null;
  }

  /**
   * Denselben Ort ohne diesen Parameter aufrufen: Pfad und alle uebrigen
   * Parameter bleiben (``searchQuery`` etwa), und der Schritt landet nicht in der
   * History - sonst fuehrte das System-Zurueck wieder in den Unter-Screen.
   *
   * Gebaut ueber den UrlTree statt ueber ``navigate([], { queryParamsHandling })``:
   * Ein Dienst hat keine ActivatedRoute der aktiven Seite, und ohne ``relativeTo``
   * zielte ein leeres Kommando-Array auf die Wurzel.
   */
  private unterScreenSchliessen(name: string): void {
    const baum = this.router.parseUrl(this.router.url);
    const { [name]: _geschlossen, ...uebrige } = baum.queryParams;
    baum.queryParams = uebrige;
    this.router.navigateByUrl(baum, { replaceUrl: true });
  }

  /**
   * Das Elternziel der aktiven Route: vom tiefsten Snapshot aufwaerts, damit
   * Kindrouten (etwa /admin/dashboard) das Ziel ihres Elternteils erben.
   */
  private elternZiel(): string | unknown[] {
    for (const eintrag of this.ketteAbwaerts().reverse()) {
      const eltern = eintrag.data?.['parent'] as ElternZiel | undefined;
      if (typeof eltern === 'function') {
        return eltern(eintrag);
      }
      if (typeof eltern === 'string') {
        return eltern;
      }
    }
    return STANDARD_ZIEL;
  }

  /** Die aktive Route von der Wurzel bis zum tiefsten Snapshot. */
  private ketteAbwaerts(): ActivatedRouteSnapshot[] {
    const kette: ActivatedRouteSnapshot[] = [];
    let snapshot: ActivatedRouteSnapshot | null = this.router.routerState.snapshot.root;
    while (snapshot) {
      kette.push(snapshot);
      snapshot = snapshot.firstChild;
    }
    return kette;
  }
}
