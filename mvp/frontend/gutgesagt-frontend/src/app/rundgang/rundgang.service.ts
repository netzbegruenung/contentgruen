import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService, UserInfo } from '../auth/auth.service';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { StateManagementService } from '../services/state-management.service';
import { SearchResponse } from '../services/dtos/searchDtos';
import { HOME_HINWEIS_MERKER } from '../shared/geraetespeicher-schalter';
import { HOME_BILDSCHIRM_MOEGLICH } from './home-bildschirm';
import { Angebot, HOME_ANGEBOT, MITMACHEN_ANGEBOT, RUNDGAENGE, Rundgang, RundgangId, WILLKOMMEN } from './rundgang-daten';
import { SCHON_DA_SCHLUESSEL, gesehen as imSpeicher, merken as speichern } from './rundgang-merker';

function hatTreffer(antwort: SearchResponse | null): boolean {
  if (!antwort) return false;
  return (
    (antwort.commentary_search_results_count ?? 0) +
      (antwort.generictext_search_results_count ?? 0) +
      (antwort.post_search_results_count ?? 0) +
      (antwort.image_search_results_count ?? 0) >
    0
  );
}

export interface RundgangStand {
  rundgang: Rundgang;
  index: number;
}

/**
 * Steuert Willkommen, Mitmachen-Angebot und den laufenden Rundgang (#389). Die
 * Darstellung machen app-rundgang-band und app-rundgang; hier steht nur, welches
 * Angebot und welcher Schritt dran ist und auf welcher Seite er spielt.
 *
 * Gestaffelt, kein Fenster (#587): Das Willkommen steht als Band über
 * Startseite und Treffern. Nach der Anmeldung kommt nur die Art.-9-Einwilligung;
 * Mitmachen bietet erst das Band auf Beitragen oder Fangkorb an, wenn die Person dort
 * zum ersten Mal ankommt. Bis dahin trägt „Beitragen“ im Kopf einen Neu-Punkt.
 * Ein Band bleibt, bis die Person darauf reagiert; nach einem Rundgang ist es für
 * diesen Besuch weg. Kein Band auf Formularen, Einladung, Anmeldung, Einwilligung
 * oder Rechtstexten. Dasselbe Band trägt auf iPhone und iPad den Hinweis „Gut gesagt
 * als App“ (HOME_ANGEBOT), nachrangig zu Willkommen und Mitmachen.
 */
@Injectable({ providedIn: 'root' })
export class RundgangService {
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);
  private readonly einwilligung = inject(Art9EinwilligungService);
  private readonly suchStand = inject(StateManagementService);
  private readonly homeMerkerAktiv = inject(HOME_HINWEIS_MERKER);
  private readonly homeMoeglich = inject(HOME_BILDSCHIRM_MOEGLICH);

  private readonly stand = signal<RundgangStand | null>(null);
  /** Der laufende Rundgang mit dem aktuellen Schritt, sonst null. */
  readonly aktiv = this.stand.asReadonly();

  private readonly angebot = signal<Angebot | null>(null);
  /**
   * Ab dem Start, nicht erst ab dem ersten Schritt (#585): Solange dessen Seite lädt,
   * ist `aktiv()` noch leer. Nach einem Rundgang bleibt das Band für diesen Besuch weg.
   */
  private readonly rundgangGestartet = signal(false);
  /** Das Angebot, das das Band gerade zeigt; ab dem ersten Rundgang des Besuchs keines. */
  readonly band = computed(() => (this.rundgangGestartet() ? null : this.angebot()));
  private readonly mitmachenOffen = signal(false);
  /** Neu-Punkt an „Beitragen“: angemeldet, eingewilligt, Mitmachen noch nicht beantwortet. */
  readonly beitragenNeu = this.mitmachenOffen.asReadonly();
  /** Zaehlt Schrittwechsel; ein ueberholter Wechsel setzt nach dem Laden nichts mehr. */
  private wechsel = 0;
  /** Die letzten Anmeldedaten; null, solange /api/user-info nicht geantwortet hat. */
  private info: UserInfo | null = null;
  /** Vor der ersten Seite steht nicht fest, wo die Person landet. */
  private ersteSeiteDa = false;
  /**
   * In diesem Besuch beantwortete Angebote, auch ohne Speicher im Browser (privates
   * Fenster): „Ausblenden“ wirkt dann wenigstens bis zum nächsten Besuch.
   */
  private readonly beantworteteAngebote = new Set<string>();
  /**
   * Hinweis „Gut gesagt als App“: Gerät passt und der Browser nimmt Merker an. Ohne
   * Speicher kein Hinweis, sonst käme er nach dem Ausblenden bei jedem Besuch wieder.
   */
  private homeSpeicherDa = false;
  /** Beim Start der App stand der Merker schon da: mindestens der zweite Besuch. */
  private schonDaGewesen = false;
  /** In diesem Besuch hat eine Suche Treffer gebracht. */
  private sucheMitTreffern = false;
  /** Willkommen oder Mitmachen stand in diesem Besuch schon da: dann kein zweites Band danach. */
  private anderesBandGezeigt = false;

  /** Einmal beim Start der App. */
  beobachten(destroyRef: DestroyRef): void {
    this.homeVorbereiten();
    this.suchStand.searchResults$.pipe(takeUntilDestroyed(destroyRef)).subscribe((antwort) => {
      if (this.sucheMitTreffern || !hatTreffer(antwort)) return;
      this.sucheMitTreffern = true;
      this.angebotPruefen();
    });

    // Zurück (oder Vor) im Browser beendet den Rundgang: Sonst stuende der Schritt auf
    // der Seite, zu der die Person gerade zurückgeht, etwa „Passende Treffer“ über den
    // neuesten Inhalten der Startseite. Starten lässt er sich jederzeit über die Hilfe neu.
    this.router.events
      .pipe(
        filter((e): e is NavigationStart => e instanceof NavigationStart && e.navigationTrigger === 'popstate'),
        takeUntilDestroyed(destroyRef),
      )
      .subscribe(() => this.beenden()); // ohne laufenden Rundgang ändert das nichts

    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(destroyRef),
      )
      .subscribe(() => {
        this.ersteSeiteDa = true;
        this.angebotPruefen();
      });

    this.auth.userInfo$.pipe(takeUntilDestroyed(destroyRef)).subscribe((info) => {
      this.info = info;
      this.angebotPruefen();
    });
    this.einwilligung.geklaert$.pipe(takeUntilDestroyed(destroyRef)).subscribe(() => this.angebotPruefen());
  }

  starten(id: RundgangId, ab = 0): Promise<void> {
    // Auch über Hilfe oder Menü gestartet ist das offene Angebot beantwortet: das Band
    // oder Mitmachen hinter dem Neu-Punkt
    const angebot = this.angebot();
    if (angebot?.rundgang === id) this.beantwortet(angebot);
    else if (id === MITMACHEN_ANGEBOT.rundgang && this.beitragenNeu()) this.beantwortet(MITMACHEN_ANGEBOT);
    this.rundgangGestartet.set(true);
    return this.zuSchritt(RUNDGAENGE[id], ab);
  }

  /** Ein Knopf im Band: Rundgang starten oder ausblenden. Das Angebot kommt nicht wieder. */
  bandBeantworten(starten: boolean): void {
    const angebot = this.band();
    if (!angebot) return;
    if (starten && angebot.rundgang) {
      void this.starten(angebot.rundgang, angebot.ab);
    } else {
      this.beantwortet(angebot);
    }
  }

  async weiter(): Promise<void> {
    const s = this.stand();
    if (!s) return;
    if (s.index < s.rundgang.schritte.length - 1) {
      await this.zuSchritt(s.rundgang, s.index + 1);
    } else {
      this.beenden();
    }
  }

  async zurueck(): Promise<void> {
    const s = this.stand();
    if (s && s.index > 0) {
      await this.zuSchritt(s.rundgang, s.index - 1);
    }
  }

  beenden(): void {
    this.wechsel++; // ein Schritt, dessen Seite noch laedt, erscheint nicht mehr
    this.stand.set(null);
  }

  /**
   * Erst die Seite, dann der Schritt: Sonst faende der Schritt sein Ziel noch auf der
   * alten Seite (eine Karte unter „Neueste Inhalte“ statt eines Treffers).
   */
  private async zuSchritt(rundgang: Rundgang, index: number): Promise<void> {
    const wechsel = ++this.wechsel;
    const seite = rundgang.schritte[index].seite;
    if (seite) {
      const ziel = this.router.createUrlTree([seite.pfad], { queryParams: seite.query ?? {} });
      if (this.router.serializeUrl(ziel) !== this.router.url) {
        await this.router.navigateByUrl(ziel).catch(() => false);
      }
    }
    if (wechsel !== this.wechsel) return; // inzwischen beendet oder weitergeklickt
    this.stand.set({ rundgang, index });
  }

  /** Welches Angebot jetzt dran ist, falls überhaupt eines. */
  private faelligesAngebot(): Angebot | null {
    if (!this.ersteSeiteDa) return null;
    const url = this.router.url;
    const hier = (a: Angebot): boolean => a.seiten.some((s) => url.startsWith(s));
    const info = this.info;
    // Bis /api/user-info antwortet, ist offen, ob jemand angemeldet ist: Ein Willkommen
    // blitzte sonst vor der Umleitung auf die Einwilligung auf (#587).
    if (!info) return null;
    if (info.isAuthenticated) {
      // Nicht vor der Einwilligung; ohne sie kein Angebot
      if (!this.eingewilligt(info.userId)) return null;
      if (this.mitmachenFaellig(info) && hier(MITMACHEN_ANGEBOT)) return MITMACHEN_ANGEBOT;
    }
    // Wer Mitmachen schon hatte, braucht kein Willkommen mehr
    if (!this.gesehen(WILLKOMMEN) && !this.gesehen(MITMACHEN_ANGEBOT) && hier(WILLKOMMEN)) return WILLKOMMEN;
    // Zuletzt und nie zugleich mit einem anderen: Es gibt nur ein Band
    if (this.homeFaellig() && hier(HOME_ANGEBOT)) return HOME_ANGEBOT;
    return null;
  }

  /**
   * Nur auf iPhone und iPad im Browser und nur mit Speicher: merkt sich, dass die Person
   * schon einmal hier war, und liest vorher, ob sie es schon war. Andere Geräte bekommen
   * keinen Merker.
   */
  private homeVorbereiten(): void {
    if (!this.homeMerkerAktiv || !this.homeMoeglich()) return;
    this.schonDaGewesen = imSpeicher(SCHON_DA_SCHLUESSEL);
    this.homeSpeicherDa = speichern(SCHON_DA_SCHLUESSEL);
  }

  /**
   * Frühestens beim zweiten Besuch oder nach einer Suche mit Treffern; nie nach
   * „Ausblenden“ und nicht im selben Besuch wie Willkommen oder Mitmachen.
   */
  private homeFaellig(): boolean {
    return (
      this.homeSpeicherDa &&
      !this.anderesBandGezeigt &&
      !this.gesehen(HOME_ANGEBOT) &&
      (this.schonDaGewesen || this.sucheMitTreffern)
    );
  }

  /** Ohne Kennung ist nichts geklärt, auch wenn `geklaert()` ebenfalls null ist. */
  private eingewilligt(kennung: string | null): boolean {
    return kennung !== null && this.einwilligung.geklaert() === kennung;
  }

  /** Angemeldet, eingewilligt, Mitmachen noch nicht beantwortet. */
  private mitmachenFaellig(info: UserInfo | null): boolean {
    return !!info?.isAuthenticated && this.eingewilligt(info.userId) && !this.gesehen(MITMACHEN_ANGEBOT);
  }

  private angebotPruefen(): void {
    const angebot = this.faelligesAngebot();
    if (angebot && angebot !== HOME_ANGEBOT) this.anderesBandGezeigt = true;
    this.angebot.set(angebot);
    this.mitmachenOffen.set(this.mitmachenFaellig(this.info));
  }

  private gesehen(angebot: Angebot): boolean {
    return this.beantworteteAngebote.has(angebot.schluessel) || imSpeicher(angebot.schluessel);
  }

  private beantwortet(angebot: Angebot): void {
    this.beantworteteAngebote.add(angebot.schluessel);
    speichern(angebot.schluessel);
    this.angebotPruefen();
  }
}
