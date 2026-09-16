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
  /** Ein Griff im Kopf laeuft gerade; weitere Tipps werden ignoriert. */
  private laeuft = false;

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
   * Was eine Seite erledigen will, bevor ein Griff im Kopf sie verlaesst - die
   * Destillier-Ansicht etwa speichert den Satz. Genau eine Seite ist zugleich
   * sichtbar, deshalb reicht ein Platz.
   */
  registerBeforeBack(fn: () => Promise<void>): void {
    this.vorZurueck = fn;
  }

  /**
   * Beim Verlassen wieder abmelden, und zwar nur die eigene Anmeldung.
   *
   * Angular zerstoert beim Routenwechsel erst die alte Ansicht und baut dann die
   * neue auf (nachgemessen: "A zerstoert", "B erzeugt"). Die Identitaetspruefung
   * schuetzt deshalb nicht gegen diese Reihenfolge, sondern gegen den Fall, dass
   * eine Seite abmeldet, was sie nie angemeldet hat - etwa wenn spaeter zwei
   * Ansichten zugleich sichtbar sind.
   */
  unregisterBeforeBack(fn?: () => Promise<void>): void {
    if (!fn || this.vorZurueck === fn) {
      this.vorZurueck = null;
    }
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
   * Ist ein Unter-Screen offen (``data.schliesst``), schliesst der Pfeil zuerst
   * ihn. Scheitert das Vorher-Erledigen, bleibt man stehen: Die Seite meldet den
   * Fehler selbst, und ein ungespeicherter Satz geht nicht dadurch verloren, dass
   * der Pfeil trotzdem navigiert.
   *
   * Das System-Zurueck (Browser-Knopf, Android-Geste) bleibt History-basiert -
   * das ist Plattformverhalten und wird hier nicht angefasst.
   */
  async goBack(): Promise<void> {
    await this.mitVorherErledigen(() => {
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
    });
  }

  /**
   * Zur Startseite - der Haus-Knopf im Desktop-Kopf.
   *
   * Wartet denselben Hook ab wie der Pfeil: Wer die Destillier-Ansicht ueber das
   * Haus verlaesst, soll seinen Satz genauso wenig verlieren wie ueber den Pfeil.
   */
  async navigateHome(): Promise<void> {
    await this.mitVorherErledigen(() => this.navigateToStart());
  }

  /**
   * Erst erledigen, was die Seite angemeldet hat, dann navigieren - und nur
   * einmal zugleich.
   *
   * Die Sperre faengt den Doppel-Tipp: Am Handy trifft der zweite Tipp den Knopf
   * oft noch, waehrend der Satz gespeichert wird. Ohne sie liefen zwei Speicher-
   * und Navigationsvorgaenge nebeneinander.
   */
  private async mitVorherErledigen(navigieren: () => void): Promise<void> {
    if (this.laeuft) {
      return;
    }
    this.laeuft = true;
    try {
      if (this.vorZurueck) {
        await this.vorZurueck();
      }
      navigieren();
    } catch {
      // Die Seite hat den Fehler bereits gemeldet; hier bleibt alles stehen.
    } finally {
      this.laeuft = false;
    }
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
