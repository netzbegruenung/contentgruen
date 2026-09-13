import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatRadioModule } from '@angular/material/radio';
import { Observable, of, Subject } from 'rxjs';
import { debounceTime, map, takeUntil, tap } from 'rxjs/operators';

import { SHARED_IMPORTS } from '../shared/shared-imports';
import { RawInput, RawInputService, SATZ_LIMIT } from '../services/raw-input.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { DestillierUebergabeService, ROHINPUT_PARAM } from './destillier-uebergabe.service';

/** Wie lange nach dem letzten Tastendruck der Satz gespeichert wird. */
export const AUTOSAVE_VERZOEGERUNG_MS = 1000;

type Beitragstyp = 'commentary' | 'generictext';

const FORMULAR_PFAD: Record<Beitragstyp, string> = {
  commentary: '/workflow/add-commentary',
  generictext: '/workflow/add-generictext',
};

/**
 * Destillieren: aus einem Einwurf in einem Satz den Punkt herausarbeiten.
 *
 * Erst der Satz, dann die Typwahl, dann das Beitragsformular. Wer den Satz nicht
 * formulieren kann, verwirft (nur beim eigenen Einwurf) oder stellt zurueck.
 *
 * Der Ablauf muss am Handy unterbrechbar sein: Der Satz wird verzoegert beim
 * Tippen, beim Verlassen des Felds, bei jedem Knopf und beim Wegwechseln der App
 * (keepalive) serverseitig gespeichert. Ohne ID in der Adresse oeffnet sich der
 * naechste offene Einwurf ohne eigenen Entwurf, sonst "Alles destilliert".
 */
@Component({
  selector: 'app-destillieren',
  standalone: true,
  imports: [...SHARED_IMPORTS, MatRadioModule, RouterLink],
  templateUrl: './destillieren.component.html',
  styleUrls: ['./destillieren.component.css'],
})
export class DestillierenComponent implements OnInit, OnDestroy {
  readonly satzLimit = SATZ_LIMIT;

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
    private logger: LoggingService,
  ) {}

  ngOnInit(): void {
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
  get notiz(): string | null {
    const inhalt = this.einwurf?.content;
    return inhalt && inhalt !== this.einwurf?.url ? inhalt : null;
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
        this.schritt = 'typwahl';
      },
      error: (error) => this.speicherfehler(error),
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
      next: () => this.uebergabe.zumNaechsten(einwurf.id),
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
      next: () => this.uebergabe.zumNaechsten(einwurf.id),
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
    this.schritt = 'satz';
  }

  ngOnDestroy(): void {
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

    this.rawInputService.getRawInput(id).subscribe({
      next: (einwurf) => {
        this.einwurf = einwurf;
        this.zuletztGespeichert = einwurf.own_draft ?? '';
        this.satz.setValue(this.zuletztGespeichert, { emitEvent: false });
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
    this.rawInputService.naechsterOffenerEinwurf(nach).subscribe({
      next: (naechster) => {
        if (naechster) {
          this.router.navigate(['/destillieren', naechster.id], { replaceUrl: true });
        } else {
          this.laedt = false;
          this.allesDestilliert = true;
        }
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
    if (!this.einwurf || satz === this.zuletztGespeichert || satz.length > SATZ_LIMIT) {
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
    this.fehler = 'Der Satz konnte nicht gespeichert werden. Bitte versuche es erneut.';
  }
}
