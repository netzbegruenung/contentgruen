import { Component, ElementRef, computed, inject, signal, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NgTemplateOutlet } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ANSICHT_PARAM, VORSCHAU_SCHRITTE, ZIEL_PARAM, vorschauZiel } from './vorschau-schritte';

/**
 * Beschriftung des Hauptknopfs. Er führt zur Login-Auswahl mit dem Ziel, wie der Knopf im
 * Kopf; dort stehen beide Wege, „Mit Netzbegrünung anmelden“ und der für Einladungskonten
 * (Entscheidung 20.11.).
 */
export const ANMELDEN_KNOPF = 'Anmelden';
export const WEITER_SUCHEN = 'Erst mal weiter suchen';
/** Etikett auf jedem Vorschaurahmen; steht auch vor dem Alternativtext. */
export const VORSCHAU_ETIKETT = 'Vorschau';
/** Über den Bildern: Es sind Bilder der angemeldeten Oberfläche, nicht die Seite selbst. */
export const VORSCHAU_SATZ = 'Eine Vorschau: So sieht Gut gesagt aus, wenn du angemeldet bist.';

/**
 * „Das erwartet dich mit Konto“ (Entscheidung Sebastian 17.11.): Besucher sehen, was ein
 * Konto bringt, bevor sie sich anmelden. Zwei Ansichten aus denselben drei Schritten
 * (VORSCHAU_SCHRITTE):
 *
 * - Übersicht (Variante A): Ziel des AuthGuard an Einwerfen, Beitragen und Fangkorb; alle
 *   drei Schritte untereinander.
 * - Rundgang (Variante B, `?ansicht=rundgang`): „Selbst beitragen“ ohne Konto aus Hilfe und
 *   Menü, ein Bild nach dem anderen.
 *
 * Beide enden mit der Anmeldung; danach geht es auf `?ziel=`. Angemeldete sehen die Seite
 * nie (mitKontoVorschauGuard).
 */
@Component({
  selector: 'app-mit-konto',
  standalone: true,
  imports: [RouterLink, MatIconModule, NgTemplateOutlet],
  templateUrl: './mit-konto.component.html',
  styleUrls: ['./mit-konto.component.css'],
})
export class MitKontoComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly schritte = VORSCHAU_SCHRITTE;
  readonly weiterSuchen = WEITER_SUCHEN;
  readonly etikett = VORSCHAU_ETIKETT;
  readonly vorschauSatz = VORSCHAU_SATZ;

  private readonly params = toSignal(this.route.queryParamMap, { initialValue: this.route.snapshot.queryParamMap });
  readonly ziel = computed(() => vorschauZiel(this.params().get(ZIEL_PARAM)));
  readonly rundgang = computed(() => this.params().get(ANSICHT_PARAM) === 'rundgang');

  /** Im Rundgang: das Bild, das gerade dran ist. */
  readonly index = signal(0);
  readonly schritt = computed(() => this.schritte[this.index()]);
  readonly letzter = computed(() => this.index() === this.schritte.length - 1);

  readonly anmeldenText = ANMELDEN_KNOPF;

  private readonly schrittTitel = viewChild<ElementRef<HTMLElement>>('schrittTitel');

  /** Zur Login-Auswahl mit beiden Wegen; nach der Anmeldung geht es auf das Ziel. */
  anmelden(): void {
    void this.router.navigate(['/login'], { queryParams: { returnUrl: this.ziel() } });
  }

  weiter(): void {
    if (!this.letzter()) this.zuSchritt(this.index() + 1);
  }

  zurueck(): void {
    if (this.index() > 0) this.zuSchritt(this.index() - 1);
  }

  /** Der Fokus geht auf den neuen Titel: Screenreader lesen das neue Bild vor, der Knopf verschwindet evtl. */
  private zuSchritt(index: number): void {
    this.index.set(index);
    queueMicrotask(() => this.schrittTitel()?.nativeElement.focus());
  }
}
