import { DestroyRef, Injectable, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { filter, take } from 'rxjs/operators';
import { AuthService } from '../auth/auth.service';
import { angebotOeffnen } from './angebot-dialog.component';
import { Angebot, MITMACHEN_ANGEBOT, RUNDGAENGE, Rundgang, RundgangId, WILLKOMMEN } from './rundgang-daten';
import { gesehen, merken } from './rundgang-merker';

export interface RundgangStand {
  rundgang: Rundgang;
  index: number;
}

/**
 * Seiten, auf denen das Willkommen beim ersten Besuch erscheint: Startseite und
 * Treffer. Nicht auf Einladung, Anmeldung oder Rechtstexten, wo es den Weg verstellte.
 */
const WILLKOMMEN_SEITEN = ['/search', '/result'];

/** Hier legt sich auch das Mitmachen-Angebot nicht darüber; es wartet auf die nächste Seite. */
const OHNE_ANGEBOT = ['/login', '/einladung', '/datenschutz', '/impressum', '/nutzungsbedingungen'];

/**
 * Steuert Willkommen, Mitmachen-Angebot und den laufenden Rundgang (#389). Die
 * Darstellung macht app-rundgang; hier steht nur, welcher Schritt dran ist und
 * auf welcher Seite er spielt.
 */
@Injectable({ providedIn: 'root' })
export class RundgangService {
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);
  private readonly auth = inject(AuthService);

  private readonly stand = signal<RundgangStand | null>(null);
  /** Der laufende Rundgang mit dem aktuellen Schritt, sonst null. */
  readonly aktiv = this.stand.asReadonly();

  private angebotOffen = false;
  /** Zaehlt Schrittwechsel; ein ueberholter Wechsel setzt nach dem Laden nichts mehr. */
  private wechsel = 0;
  private mitmachenAusstehend = false;
  /** Erst nach der ersten Seite steht fest, ob dort das Willkommen erscheint. */
  private ersteSeiteDa = false;

  /**
   * Einmal beim Start der App: Willkommen beim ersten Besuch, Mitmachen nach der
   * ersten Anmeldung.
   */
  beobachten(destroyRef: DestroyRef): void {
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        filter((e) => WILLKOMMEN_SEITEN.some((s) => e.urlAfterRedirects.startsWith(s))),
        take(1),
        takeUntilDestroyed(destroyRef),
      )
      .subscribe(() => {
        if (!gesehen(WILLKOMMEN.schluessel)) {
          this.anbieten(WILLKOMMEN);
        }
      });

    // Mitmachen wartet die erste Seite ab: Ist sie Startseite oder Treffer, kommt dort
    // zuerst das Willkommen; sonst (etwa nach einer Einladung) gleich das Angebot.
    // Ein zurückgestelltes Angebot kommt mit der nächsten Seite.
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(destroyRef),
      )
      .subscribe(() => {
        this.ersteSeiteDa = true;
        // Das Willkommen-Abo oben hat schon reagiert, falls es diese Seite war
        if (!this.angebotOffen) this.naechstesAngebot();
      });

    this.auth.userInfo$.pipe(takeUntilDestroyed(destroyRef)).subscribe((info) => {
      if (info?.isAuthenticated) {
        this.mitmachenPruefen();
      }
    });
  }

  starten(id: RundgangId): Promise<void> {
    this.mitmachenAusstehend = this.mitmachenAusstehend && id !== 'mitmachen';
    return this.zuSchritt(RUNDGAENGE[id], 0);
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
    if (!this.stand()) return;
    this.stand.set(null);
    this.naechstesAngebot();
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

  private mitmachenPruefen(): void {
    if (gesehen(MITMACHEN_ANGEBOT.schluessel)) return;
    // Nicht über ein anderes Angebot oder einen laufenden Rundgang legen; danach.
    const ruhigeSeite = OHNE_ANGEBOT.some((s) => this.router.url.startsWith(s));
    if (this.angebotOffen || this.stand() || !this.ersteSeiteDa || ruhigeSeite) {
      this.mitmachenAusstehend = true;
      return;
    }
    this.anbieten(MITMACHEN_ANGEBOT);
  }

  private naechstesAngebot(): void {
    if (this.mitmachenAusstehend && this.auth.getUserInfo()?.isAuthenticated) {
      this.mitmachenAusstehend = false;
      this.mitmachenPruefen();
    }
  }

  private anbieten(angebot: Angebot): void {
    this.angebotOffen = true;
    angebotOeffnen(this.dialog, angebot)
      .afterClosed()
      .subscribe((wahl) => {
        this.angebotOffen = false;
        // Auch Escape und „Später“ zählen als gesehen: Das Angebot kommt nicht wieder.
        merken(angebot.schluessel);
        if (wahl === 'starten') {
          void this.starten(angebot.rundgang);
        } else {
          this.naechstesAngebot();
        }
      });
  }
}
