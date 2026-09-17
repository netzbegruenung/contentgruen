import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatRadioModule } from '@angular/material/radio';
import { firstValueFrom, Observable, of, Subject, throwError } from 'rxjs';
import { debounceTime, map, takeUntil, tap } from 'rxjs/operators';

import { SHARED_IMPORTS } from '../shared/shared-imports';
import {
  RawInput,
  RawInputDraft,
  RawInputService,
  SATZ_LIMIT,
} from '../services/raw-input.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { kurzeKennung } from '../shared/kennung';
import { typBeschreibung, typLabel } from '../shared/content-type-registry';
import {
  DestillierUebergabeService,
  ROHINPUT_PARAM,
  SCHRITT_PARAM,
  TAB_PARAM,
} from './destillier-uebergabe.service';
import { FangkorbTab, tabMerken, verworfenEinblenden } from '../raw-input-list/fangkorb-filter';
import { NavigationService } from '../services/navigation.service';
import { FORMULAR_PFAD } from '../shared/formular-adresse';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausEinwurf } from '../beitragskarte/karten-daten';

/** Wie lange nach dem letzten Tastendruck der Satz gespeichert wird. */
export const AUTOSAVE_VERZOEGERUNG_MS = 1000;

type Beitragstyp = 'commentary' | 'generictext';

/** Die Typwahl, mit denselben Saetzen wie auf der Beitragen-Seite (aus der Registry). */
export const TYPEN: ReadonlyArray<{ wert: Beitragstyp; name: string; erlaeuterung: string }> = [
  { wert: 'commentary', name: typLabel('commentary'), erlaeuterung: typBeschreibung('commentary') },
  { wert: 'generictext', name: typLabel('generictext'), erlaeuterung: typBeschreibung('generictext') },
];

/**
 * Destillieren: aus einem Einwurf in einem Satz den Punkt herausarbeiten.
 *
 * Erst der Satz, dann die Typwahl, dann das Beitragsformular. Wer den Satz nicht
 * formulieren kann, verwirft (nur beim eigenen Einwurf) oder stellt zurueck.
 * Saetze anderer zum selben Einwurf stehen lesbar ueber dem eigenen Feld - es
 * gibt keine Sperre, jeder formuliert seinen eigenen.
 *
 * Der Ablauf muss am Handy unterbrechbar sein: Der Satz wird verzoegert beim
 * Tippen, beim Verlassen des Felds, bei jedem Knopf und beim Wegwechseln der App
 * (keepalive) serverseitig gespeichert. Ohne ID in der Adresse oeffnet sich der
 * naechste offene Einwurf ohne eigenen Entwurf, sonst "Alles destilliert".
 */
@Component({
  selector: 'app-destillieren',
  standalone: true,
  imports: [...SHARED_IMPORTS, MatRadioModule, RouterLink, BeitragskarteComponent],
  templateUrl: './destillieren.component.html',
  styleUrls: ['./destillieren.component.css'],
})
export class DestillierenComponent implements OnInit, OnDestroy {
  readonly satzLimit = SATZ_LIMIT;
  readonly typen = TYPEN;
  readonly kurzeKennung = kurzeKennung;

  satz = new FormControl('', {
    nonNullable: true,
    validators: [Validators.maxLength(SATZ_LIMIT)],
  });
  einwurf: RawInput | null = null;
  schritt: 'satz' | 'typwahl' = 'satz';
  typ: Beitragstyp = 'commentary';
  laedt = true;
  arbeitet = false;
  allesDestilliert = false;
  fehler: string | null = null;

  private eigeneKennung: string | null = null;
  private zuletztGespeichert = '';
  private destroy$ = new Subject<void>();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private rawInputService: RawInputService,
    private authService: AuthService,
    private uebergabe: DestillierUebergabeService,
    private navigation: NavigationService,
    private logger: LoggingService,
  ) {}

  ngOnInit(): void {
    // Der Pfeil im Kopf soll den Satz nicht liegen lassen.
    this.navigation.registerBeforeBack(this.satzSichernVorZurueck);
    this.eigeneKennung = this.authService.getCurrentUserId();
    if (!this.eigeneKennung) {
      this.authService
        .fetchUserInfo()
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (info) => (this.eigeneKennung = info?.userId ?? null),
          error: () => (this.eigeneKennung = null),
        });
    }

    this.route.paramMap
      .pipe(takeUntil(this.destroy$))
      .subscribe((params) => this.laden(params.get('id')));

    this.satz.valueChanges
      .pipe(debounceTime(AUTOSAVE_VERZOEGERUNG_MS), takeUntil(this.destroy$))
      .subscribe(() => this.entwurfSpeichern());
  }

  /** Android friert die Seite beim App-Wechsel ein - vorher noch sichern. */
  @HostListener('document:visibilitychange')
  onVisibilityChange(): void {
    if (document.visibilityState === 'hidden') {
      this.entwurfSichern();
    }
  }

  get istEigenerEinwurf(): boolean {
    return !!this.einwurf?.submitted_by && this.einwurf.submitted_by === this.eigeneKennung;
  }

  get kannWeiter(): boolean {
    const satz = this.satz.value.trim();
    return satz.length > 0 && satz.length <= SATZ_LIMIT && !this.arbeitet;
  }

  /** Die Notiz zum Einwurf, sofern sie mehr ist als der Link selbst. */
  /**
   * Der Einwurf als Kopfband fuer die Typwahl, mit dem gerade formulierten Satz.
   * Zwischengespeichert, solange Einwurf und Satz gleich bleiben.
   */
  get einwurfKopf(): KartenDaten | null {
    const einwurf = this.einwurf;
    if (!einwurf) {
      return null;
    }
    const satz = this.satz.value.trim();
    if (this.kopfCache?.einwurf !== einwurf || this.kopfCache.satz !== satz) {
      const karte = ausEinwurf(einwurf);
      this.kopfCache = {
        einwurf,
        satz,
        karte: karte.rohling ? { ...karte, rohling: { ...karte.rohling, kopfSatz: satz || undefined } } : karte,
      };
    }
    return this.kopfCache.karte;
  }

  private kopfCache?: { einwurf: RawInput; satz: string; karte: KartenDaten };

  get notiz(): string | null {
    const inhalt = this.einwurf?.content;
    return inhalt && inhalt !== this.einwurf?.url ? inhalt : null;
  }

  /**
   * Die Saetze anderer Personen zu diesem Einwurf. Solange die eigene Kennung
   * nicht bekannt ist, lieber keine als den eigenen Satz doppelt.
   */
  get fremdeSaetze(): RawInputDraft[] {
    if (!this.eigeneKennung) {
      return [];
    }
    return (this.einwurf?.drafts ?? []).filter((satz) => satz.user_id !== this.eigeneKennung);
  }

  onBlur(): void {
    this.entwurfSpeichern();
  }

  weiter(): void {
    if (!this.kannWeiter) {
      return;
    }
    this.arbeitet = true;
    this.fehler = null;
    this.speichernWennGeaendert().subscribe({
      next: () => {
        this.arbeitet = false;
        this.schrittSetzen('typwahl');
      },
      error: (error) => this.speicherfehler(error),
    });
  }

  /**
   * Den Schritt wechseln und in der Adresse mitfuehren.
   *
   * Der Schritt steht in der Adresse, damit ein Neustart der PWA an derselben
   * Stelle weitermacht und die Kopfzeile den passenden Titel zeigen kann
   * (RouteConfigService). ``replaceUrl``, weil es kein eigener Halt in der
   * History ist - der Knopf "Zurueck" im Ablauf fuehrt zum Satz.
   */
  private schrittSetzen(schritt: 'satz' | 'typwahl'): void {
    this.schritt = schritt;
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { [SCHRITT_PARAM]: schritt === 'typwahl' ? 'typwahl' : null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  spaeter(): void {
    const einwurf = this.einwurf;
    if (!einwurf) {
      return;
    }
    this.arbeitet = true;
    this.fehler = null;
    this.speichernWennGeaendert().subscribe({
      next: () => {
        // Nicht gleich wieder anbieten - sonst springt "Spaeter" ohne Satz
        // zwischen zwei offenen Einwuerfen endlos hin und her.
        this.rawInputService.zurueckstellen(einwurf.id);
        // Ist keiner mehr offen, geht es in den Tab, in dem der Einwurf jetzt
        // liegt: mit einem Satz (eigenem oder fremdem) unter "Ausformulieren",
        // ohne unter "Destillieren".
        const mitSatz = !!this.zuletztGespeichert.trim() || this.fremdeSaetze.length > 0;
        this.uebergabe.zumNaechsten(einwurf.id, mitSatz ? 'ausformulieren' : 'destillieren');
      },
      error: (error) => this.speicherfehler(error),
    });
  }

  verwerfen(): void {
    const einwurf = this.einwurf;
    if (!einwurf || !this.istEigenerEinwurf) {
      return;
    }
    this.arbeitet = true;
    this.fehler = null;
    this.rawInputService.updateStatus(einwurf.id, 'discarded').subscribe({
      next: () => {
        // Verworfenes liegt unter "Erledigt" hinter einem Chip, der normalerweise
        // aus ist - fuer diese Sitzung wird er eingeschaltet, sonst ist der
        // Einwurf nach dem Verwerfen scheinbar spurlos weg.
        verworfenEinblenden();
        this.uebergabe.zumNaechsten(einwurf.id, 'erledigt');
      },
      error: (error) => {
        this.logger.error('Verwerfen fehlgeschlagen', error);
        this.arbeitet = false;
        this.fehler =
          error?.status === 409
            ? 'Aus diesem Einwurf ist schon ein Beitrag entstanden; verwerfen geht nicht mehr.'
            : 'Verwerfen hat nicht geklappt. Bitte versuche es erneut.';
      },
    });
  }

  formularOeffnen(): void {
    if (!this.einwurf) {
      return;
    }
    this.router.navigate([FORMULAR_PFAD[this.typ]], {
      queryParams: { [ROHINPUT_PARAM]: this.einwurf.id },
    });
  }

  zurueckZumSatz(): void {
    this.schrittSetzen('satz');
  }

  /**
   * Was vor dem Pfeil im Kopf passieren muss: den Satz speichern.
   *
   * Wie bei "Spaeter" wird das Speichern abgewartet - der Fangkorb laedt seine
   * Liste sofort, und den gecachten Stand verwirft erst die Antwort darauf.
   * Scheitert es, bleibt die Ansicht stehen und zeigt den Fehler; der Dienst
   * navigiert dann nicht.
   */
  private readonly satzSichernVorZurueck = async (): Promise<void> => {
    this.arbeitet = true;
    this.fehler = null;
    try {
      await firstValueFrom(this.speichernWennGeaendert());
      this.arbeitet = false;
    } catch (error) {
      this.speicherfehler(error as Error);
      throw error;
    }
  };

  ngOnDestroy(): void {
    this.navigation.unregisterBeforeBack(this.satzSichernVorZurueck);
    // Wer innerhalb der App wegnavigiert, verliert den Satz nicht.
    this.entwurfSpeichern();
    this.destroy$.next();
    this.destroy$.complete();
  }

  private laden(id: string | null): void {
    this.einwurf = null;
    this.schritt = 'satz';
    this.typ = 'commentary';
    this.arbeitet = false;
    this.allesDestilliert = false;
    this.fehler = null;
    this.laedt = true;

    if (!id) {
      this.naechstenOeffnen();
      return;
    }

    const gewuenschterSchritt = this.route.snapshot?.queryParamMap?.get(SCHRITT_PARAM) ?? null;

    this.rawInputService.getRawInput(id).subscribe({
      next: (einwurf) => {
        this.einwurf = einwurf;
        this.zuletztGespeichert = einwurf.own_draft ?? '';
        this.satz.setValue(this.zuletztGespeichert, { emitEvent: false });
        // Die Typwahl eines schon verarbeiteten Einwurfs ist ein Rueckweg nach dem
        // Speichern (System-Zurueck von der Ergebnisseite), kein neuer Anlauf: Dann
        // in den Fangkorb, wo der Einwurf unter Erledigt liegt. Einen weiteren
        // Beitrag gibt es ueber "Weiter destillieren", das beim Satz beginnt.
        if (gewuenschterSchritt === 'typwahl' && einwurf.status === 'processed') {
          tabMerken('erledigt');
          this.router.navigate(['/fangkorb'], { replaceUrl: true });
          return;
        }
        // Aus dem Fangkorb kommt "Ausformulieren" direkt in die Typwahl - aber nur
        // mit eigenem Satz. Ohne ihn gibt es nichts auszuformulieren, dann steht
        // wie sonst das Satzfeld da.
        if (gewuenschterSchritt === 'typwahl' && this.zuletztGespeichert.trim()) {
          this.schritt = 'typwahl';
        }
        this.laedt = false;
      },
      error: (error) => {
        this.logger.error('Einwurf konnte nicht geladen werden', error);
        this.laedt = false;
        this.fehler =
          error?.status === 404
            ? 'Diesen Einwurf gibt es nicht.'
            : 'Der Einwurf konnte nicht geladen werden.';
      },
    });
  }

  private naechstenOeffnen(): void {
    const nach = this.route.snapshot?.queryParamMap?.get('nach') ?? null;
    const tab = this.route.snapshot?.queryParamMap?.get(TAB_PARAM) as FangkorbTab | null;
    // Ohne "nach" beginnt eine neue Runde: Zurueckgestelltes kommt wieder dran.
    if (!nach) {
      this.rawInputService.rundeBeginnen();
    }
    this.rawInputService.naechsterOffenerEinwurf(nach).subscribe({
      next: (naechster) => {
        if (naechster) {
          this.router.navigate(['/destillieren', naechster.id], { replaceUrl: true });
          return;
        }
        // Mit "nach" kommt man aus dem Ablauf und hat gerade etwas fertig
        // gemacht: zurueck in den Fangkorb, in den Tab mit dem Ergebnis - welcher
        // das ist, sagt die Handlung ueber "tab". Ohne "nach" hat jemand die
        // Ansicht direkt geoeffnet; dann bleibt es bei der Ansage, dass nichts
        // offen ist.
        //
        // replaceUrl wie im Zweig darueber: Sonst bliebe /destillieren?nach=... in
        // der History stehen, und das System-Zurueck liefe von hier aus wieder in
        // dieselbe Weiterleitung.
        if (nach) {
          this.rawInputService.rundeBeginnen();
          tabMerken(tab ?? 'erledigt');
          this.router.navigate(['/fangkorb'], { replaceUrl: true });
          return;
        }
        this.laedt = false;
        this.allesDestilliert = true;
      },
      error: (error) => {
        this.logger.error('Fangkorb konnte nicht geladen werden', error);
        this.laedt = false;
        this.fehler = 'Der Fangkorb konnte nicht geladen werden.';
      },
    });
  }

  /** Speichert nur, wenn sich der Satz seit dem letzten Speichern geaendert hat. */
  private speichernWennGeaendert(): Observable<void> {
    const satz = this.satz.value.trim();
    // Zu lang heisst: nicht speicherbar. Frueher lief das still als "nichts zu
    // tun" durch - dann verliess der Pfeil die Ansicht und der Satz war weg.
    if (satz.length > SATZ_LIMIT) {
      return throwError(() => new Error(`Satz ueber ${SATZ_LIMIT} Zeichen`));
    }
    if (!this.einwurf || satz === this.zuletztGespeichert) {
      return of(undefined);
    }
    return this.rawInputService.saveDraft(this.einwurf.id, satz).pipe(
      tap(() => (this.zuletztGespeichert = satz)),
      map(() => undefined),
    );
  }

  private entwurfSpeichern(): void {
    this.speichernWennGeaendert().subscribe({
      error: (error) => this.logger.warn('Entwurf konnte nicht gespeichert werden', error),
    });
  }

  private entwurfSichern(): void {
    const satz = this.satz.value.trim();
    if (!this.einwurf || satz === this.zuletztGespeichert || satz.length > SATZ_LIMIT) {
      return;
    }
    this.rawInputService.saveDraftKeepalive(this.einwurf.id, satz);
    this.zuletztGespeichert = satz;
  }

  private speicherfehler(error: Error): void {
    this.logger.error('Satz konnte nicht gespeichert werden', error);
    this.arbeitet = false;
    // Ein zu langer Satz ist kein Netzfehler - "versuche es erneut" waere hier
    // der falsche Rat, kuerzen hilft.
    this.fehler =
      this.satz.value.trim().length > SATZ_LIMIT
        ? `Der Satz ist zu lang: höchstens ${SATZ_LIMIT} Zeichen.`
        : 'Der Satz konnte nicht gespeichert werden. Bitte versuche es erneut.';
  }
}
