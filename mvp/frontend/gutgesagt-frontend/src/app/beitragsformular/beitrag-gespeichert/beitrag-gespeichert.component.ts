import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatSnackBar } from '@angular/material/snack-bar';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Observable, throwError } from 'rxjs';
import { switchMap } from 'rxjs/operators';

import { SHARED_IMPORTS } from '../../shared/shared-imports';
import { BeitragskarteComponent } from '../../beitragskarte/beitragskarte.component';
import { KartenDaten, ausAussage } from '../../beitragskarte/karten-daten';
import { BeitragAnsehenService } from '../beitrag-ansehen.service';
import { LoggingService } from '../../services/logging.service';
import { NavigationService } from '../../services/navigation.service';
import { EinwurfService } from '../../services/einwurf.service';
import { VERKNUEPFUNG_FEHLGESCHLAGEN } from '../../services/statement.service';
import { DestillierUebergabeService } from '../../destillieren/destillier-uebergabe.service';
import { NACH_DEM_AUSFORMULIEREN, tabMerken } from '../../fangkorb/fangkorb-filter';
import { FORMULAR_PFAD, FormularTyp } from '../../shared/formular-adresse';
import {
  GespeichertZustand,
  Herkunft,
  SUCHE_PARAM,
  herkunftAus,
} from './gespeichert-adresse';
import { EINWURF_PARAM } from '../../destillieren/einwurf-adresse';

/** Beitragstypen, fuer die es die Ergebnisseite gibt. */
export type GespeichertTyp = Extract<FormularTyp, 'commentary' | 'generictext' | 'post'>;

/** Die Saetze der Seite je Typ - der Kommentar, die Hintergrundinfo, der Post. */
const TEXTE: Record<GespeichertTyp, { gespeichert: string; nochEiner: string; nichtLadbar: string }> = {
  commentary: {
    gespeichert: 'Dein Kommentar ist gespeichert.',
    nochEiner: 'Noch einen Kommentar',
    nichtLadbar: 'Er lässt sich gerade nicht anzeigen – unter „Meine Beiträge“ findest du ihn.',
  },
  generictext: {
    gespeichert: 'Deine Hintergrundinfo ist gespeichert.',
    nochEiner: 'Noch eine Hintergrundinfo',
    nichtLadbar: 'Sie lässt sich gerade nicht anzeigen – unter „Meine Beiträge“ findest du sie.',
  },
  post: {
    gespeichert: 'Dein Post ist gespeichert.',
    nochEiner: 'Noch einen Post',
    nichtLadbar: 'Er lässt sich gerade nicht anzeigen – unter „Meine Beiträge“ findest du ihn.',
  },
};

/** Die oeffentliche Adresse eines Beitrags (#300). */
export function beitragLink(id: string, origin: string = window.location.origin): string {
  return `${origin}/beitrag/${encodeURIComponent(id)}`;
}

export const EINWURF_NICHT_MIT_NEUEM_VERKNUEPFT =
  'Der Einwurf ließ sich nicht mit dem Beitrag verknüpfen – er steht im Fangkorb weiter unter „Ausformulieren“.';

/**
 * Die Seite nach dem Speichern eines Beitrags (<Formularpfad>/gespeichert/<id>),
 * fuer alle Wege ins Formular.
 *
 * Zeigt den gespeicherten Beitrag, worauf er antwortet, und den naechsten Schritt
 * passend zur Herkunft: aus dem Fangkorb der naechste Einwurf, aus der Suche
 * zurueck zur Anfrage, sonst noch einer. Typ aus den Routendaten, ID und Herkunft
 * aus der Adresse, der Rest aus dem Router-State (nach dem Neuladen weg - dann
 * eben ohne "Antwort auf").
 */
@Component({
  standalone: true,
  selector: 'app-beitrag-gespeichert',
  imports: [...SHARED_IMPORTS, CommonModule, RouterLink, BeitragskarteComponent],
  templateUrl: './beitrag-gespeichert.component.html',
  styleUrls: ['./beitrag-gespeichert.component.css'],
})
export class BeitragGespeichertComponent implements OnInit {
  private destroyRef = inject(DestroyRef);

  readonly einwurfNichtVerknuepft = EINWURF_NICHT_MIT_NEUEM_VERKNUEPFT;

  typ: GespeichertTyp = 'commentary';
  herkunft: Herkunft = 'frei';
  karte: KartenDaten | null = null;
  laedt = true;
  nichtLadbar = false;
  /**
   * Ob der eben ausformulierte Einwurf der eigene ist; null, solange das nicht
   * feststeht. Nur dann fuehrt der zweite Knopf nach "Meine Einwuerfe" (F1 in #511).
   */
  einwurfEigen: boolean | null = null;
  readonly zustand: GespeichertZustand;
  readonly aussageKopf: KartenDaten | null;
  /** Die ID aus der Adresse, fuer "Link kopieren". */
  private beitragId = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private beitragAnsehen: BeitragAnsehenService,
    private navigationService: NavigationService,
    private uebergabe: DestillierUebergabeService,
    private einwurfService: EinwurfService,
    private logger: LoggingService,
    private clipboard: Clipboard,
    private snackBar: MatSnackBar,
  ) {
    // Der State haengt an der laufenden Navigation; nach dem Neuladen gibt es keinen.
    this.zustand = (this.router.getCurrentNavigation()?.extras.state as GespeichertZustand | undefined) ?? {};
    const aussage = this.zustand.aussage;
    // Nicht verknuepft: keine "Antwort auf"-Karte - der Hinweis nennt die Aussage.
    this.aussageKopf =
      aussage?.text && this.zustand.verknuepft !== false ? ausAussage(aussage.id, aussage.text) : null;
  }

  /** Hinweis, wenn nicht verknuepft werden konnte - mit der Aussage im Text, sofern bekannt. */
  get verknuepfungFehlgeschlagen(): string {
    const text = this.zustand.aussage?.text;
    return text
      ? `Dein Beitrag ist gespeichert, konnte aber nicht mit „${text}“ verknüpft werden.`
      : VERKNUEPFUNG_FEHLGESCHLAGEN;
  }

  get texte() {
    return TEXTE[this.typ];
  }

  private get einwurfId(): string | null {
    return this.route.snapshot.queryParamMap.get(EINWURF_PARAM);
  }

  ngOnInit(): void {
    this.typ = this.route.snapshot.data['typ'] ?? 'commentary';
    this.herkunft = herkunftAus(this.route.snapshot.queryParamMap);
    this.eigenenEinwurfPruefen();
    this.route.paramMap
      .pipe(
        switchMap((params) => {
          this.laedt = true;
          this.nichtLadbar = false;
          this.beitragId = params.get('id') ?? '';
          return this.laden(this.beitragId);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (karte) => {
          this.karte = karte;
          this.laedt = false;
        },
        error: (error) => {
          this.logger.warn('Gespeicherter Beitrag nicht ladbar', error);
          this.laedt = false;
          this.nichtLadbar = true;
        },
      });
  }

  /** Fangkorb: der naechste offene Einwurf; ist keiner offen, der Fangkorb. */
  naechsterEinwurf(): void {
    this.uebergabe.zumNaechsten(this.einwurfId ?? '', NACH_DEM_AUSFORMULIEREN);
  }

  /**
   * Ausformuliertes liegt in keiner Arbeitsliste des Fangkorbs; ein eigener Einwurf
   * steht danach unter "Meine Einwuerfe" (#508). Dorthin fuehrt der Knopf aber nur,
   * wenn der Einwurf sicher der eigene ist: Fremde stehen dort nie (F1 in #511).
   */
  get zuMeinenEinwuerfen(): boolean {
    return this.einwurfEigen === true;
  }

  zuMeinenEinwuerfenGehen(): void {
    this.navigationService.navigateToMeineEinwuerfe();
  }

  /**
   * Bei einem fremden Einwurf, solange unklar ist, wessen er ist, und wenn die
   * Verknuepfung gescheitert ist (dann ist er noch destilliert): in den Fangkorb, in
   * die Arbeitsliste, aus der der Einwurf kam.
   */
  zumFangkorb(): void {
    tabMerken(NACH_DEM_AUSFORMULIEREN);
    this.router.navigate(['/fangkorb']);
  }

  zurueckZurSuche(): void {
    const suche = this.route.snapshot.queryParamMap.get(SUCHE_PARAM);
    if (suche) {
      this.navigationService.navigateToResult(suche);
      return;
    }
    this.router.navigate(['/search']);
  }

  nochEiner(): void {
    this.router.navigate([FORMULAR_PFAD[this.typ]]);
  }

  /**
   * "Zur Aussage" nur mit Aussage, und nicht, wenn "Zurueck zur Suche" schon genau
   * dorthin fuehrt.
   */
  get zurAussageZeigen(): boolean {
    if (!this.aussageKopf) {
      return false;
    }
    const suche = this.route.snapshot.queryParamMap.get(SUCHE_PARAM)?.trim();
    return !(this.herkunft === 'suche' && suche && suche === this.zustand.aussage?.text.trim());
  }

  /** Die Suche nach der Aussage: dort stehen alle Antworten auf sie (#617). */
  zurAussage(): void {
    const text = this.zustand.aussage?.text;
    if (text) {
      this.navigationService.navigateToResult(text);
    }
  }

  /** Die eigene Adresse des Beitrags (/beitrag/:id, oeffentlich) zum Teilen. */
  linkKopieren(): void {
    if (!this.beitragId) {
      return;
    }
    const kopiert = this.clipboard.copy(beitragLink(this.beitragId));
    this.snackBar.open(kopiert ? 'Link kopiert.' : 'Kopieren hat nicht geklappt.', undefined, { duration: 3000 });
  }

  /**
   * Wessen Einwurf es ist, sagt nur der Server (Kennzeichen, #385). Gefragt wird nur,
   * wenn die Verknuepfung geklappt hat; laesst er sich nicht laden, bleibt es beim
   * Fangkorb.
   */
  private eigenenEinwurfPruefen(): void {
    const einwurfId = this.einwurfId;
    if (this.herkunft !== 'fangkorb' || !einwurfId || this.zustand.einwurfVerknuepft === false) {
      return;
    }
    this.einwurfService
      .einwurfLaden(einwurfId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (einwurf) => (this.einwurfEigen = einwurf.ist_eigener_einwurf === true),
        error: (error) => this.logger.warn('Einwurf nach dem Ausformulieren nicht ladbar', error),
      });
  }

  private laden(id: string): Observable<KartenDaten> {
    return this.beitragAnsehen.karteLaden(id, this.typ) ?? throwError(() => new Error(`Typ ${this.typ} nicht ladbar`));
  }
}
