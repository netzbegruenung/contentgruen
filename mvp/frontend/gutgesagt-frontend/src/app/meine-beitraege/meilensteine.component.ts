import { ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, Inject, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { Subject, forkJoin } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { AbzeichenSichtbarkeit, Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { gesehenMerken } from './meilenstein-merker';
import { MEILENSTEIN_MERKER } from '../shared/geraetespeicher-schalter';
import { PunkteEinwilligungComponent } from '../shared/punkte-einwilligung/punkte-einwilligung.component';
import { PunkteEinwilligungService } from '../shared/punkte-einwilligung/punkte-einwilligung.service';

/**
 * Die eigenen Meilensteine in „Meine Beiträge“ (#351): je einer mit Medaillon (Motiv
 * aus Fluent Emoji, erreicht tannengrün, offen grau gestrichelt), sprechendem Namen,
 * Untertitel und Beschreibung; offene mit Stand („3/10“). Was hier zu sehen war, gilt
 * dem Hinweis nach dem Einwerfen als gesehen (meilenstein-hinweis.service.ts).
 *
 * Darunter die Zustimmung zur Sichtbarkeit (GLOSSARY.md): Ab dem ersten erreichten
 * Meilenstein, der fürs Abzeichen zählt (keine Wegmarke), fragt die Seite einmal mit zwei gleichwertigen Knöpfen, ob andere
 * Angemeldete das Abzeichen am Namen sehen; nichts ist vorbelegt, die Antwort lässt
 * sich jederzeit ändern (ADR 0004, docs/VISION.md). Ohne die Schalter liefert der
 * Server keine Sichtbarkeit, dann fragt die Seite nicht und die Meilensteine bleiben
 * nur für die Person.
 *
 * Meilensteine gibt es nur mit der eigenen, freiwilligen Einwilligung „Punkte und
 * Meilensteine“ (#351). Fehlt sie, steht hier eine kurze Einladung mit dem Häkchen;
 * nach dem Haken laden die Meilensteine selbst nach. Ohne eingeschaltete Punkte oder
 * für ein Startkonto zeigt die Komponente nichts.
 */
@Component({
  selector: 'app-meilensteine',
  standalone: true,
  imports: [CommonModule, MatButtonModule, RouterLink, PunkteEinwilligungComponent],
  templateUrl: './meilensteine.component.html',
  styleUrls: ['./meilensteine.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MeilensteineComponent implements OnInit, OnDestroy {
  meilensteine: Meilenstein[] = [];
  sichtbarkeit: AbzeichenSichtbarkeit | null = null;
  speichert = false;
  /** Nach einem Nein erneut gefragt ("Anderen zeigen"): Zustimmen nur mit dem Wortlaut vor Augen. */
  frageOffen = false;
  fehler = false;
  /** Nach einer Antwort verschwinden die Knöpfe der Frage; der Fokus geht hierher. */
  @ViewChild('aendernKnopf', { read: ElementRef }) aendernKnopf?: ElementRef<HTMLElement>;
  /** Punkte an, aber (noch) keine Einwilligung „Punkte und Meilensteine“: Einladung zeigen. */
  einladen = false;
  private eingewilligt: boolean | null = null;
  private destroy$ = new Subject<void>();

  constructor(
    private usageTrackingService: UsageTrackingService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef,
    @Inject(MEILENSTEIN_MERKER) private merkerAktiv: boolean,
    private punkteEinwilligung: PunkteEinwilligungService,
  ) {}

  ngOnInit(): void {
    this.laden();
    // Die Einwilligung kann hier oder in den Datenschutz-Einstellungen wechseln: Dann
    // laden die Meilensteine selbst nach, ohne Neuladen der Seite.
    this.punkteEinwilligung.stand$.pipe(takeUntil(this.destroy$)).subscribe((stand) => {
      if (stand === undefined) {
        return;
      }
      const eingewilligt = stand?.eingewilligt ?? null;
      this.einladen = stand !== null && !stand.eingewilligt;
      if (this.eingewilligt !== null && eingewilligt !== this.eingewilligt) {
        this.laden();
      }
      this.eingewilligt = eingewilligt;
      this.cdr.markForCheck();
    });
    this.punkteEinwilligung.laden().pipe(takeUntil(this.destroy$)).subscribe();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  laden(): void {
    forkJoin({
      meilensteine: this.usageTrackingService.getEigeneMeilensteine(),
      sichtbarkeit: this.usageTrackingService.getAbzeichenSichtbarkeit(),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe(({ meilensteine, sichtbarkeit }) => {
        this.meilensteine = meilensteine;
        this.sichtbarkeit = sichtbarkeit;
        // Was hier steht, ist angezeigt: Kein späterer Hinweis nennt es noch einmal.
        if (this.merkerAktiv) {
          gesehenMerken(this.authService.getCurrentUserId(), meilensteine);
        }
        this.cdr.markForCheck();
      });
  }

  get erreichte(): number {
    return this.meilensteine.filter((m) => m.erreicht).length;
  }

  /** Die erreichten und der nächste offene, in der Reihenfolge der Liste. */
  get sichtbare(): Meilenstein[] {
    const naechster = this.meilensteine.find((m) => !m.erreicht);
    return this.meilensteine.filter((m) => m.erreicht || m === naechster);
  }

  /** Die übrigen offenen, aufklappbar unter „Weitere Meilensteine“. */
  get weitere(): Meilenstein[] {
    const sichtbar = new Set(this.sichtbare);
    return this.meilensteine.filter((m) => !sichtbar.has(m));
  }

  /** Die Bildnachweise, je einmal; für ein später ersetztes Bild steht dort ein eigener. */
  get bildnachweise(): string[] {
    return [...new Set(this.meilensteine.map((m) => m.bildnachweis).filter((n) => !!n))];
  }

  /** Erreichte, die das Abzeichen am Namen zählt: Wegmarken (eigenes Tun) nicht. */
  get erreichteFuersAbzeichen(): number {
    return this.meilensteine.filter((m) => m.erreicht && m.art !== 'weg').length;
  }

  /** Einmal fragen, sobald es etwas zu zeigen gäbe. */
  get fragen(): boolean {
    if (!this.sichtbarkeit) {
      return false;
    }
    return this.frageOffen || (!this.sichtbarkeit.gefragt && this.erreichteFuersAbzeichen > 0);
  }

  /** Andere Angemeldete sehen das Abzeichen. */
  get sichtbar(): boolean {
    return this.sichtbarkeit?.zeigen === true;
  }

  /** "Anderen zeigen" fragt noch einmal mit dem Wortlaut; "Nicht mehr zeigen" gilt sofort. */
  aendern(): void {
    if (this.sichtbar) {
      this.antworten(false);
    } else {
      this.frageOffen = true;
    }
  }

  antworten(zeigen: boolean): void {
    const stand = this.sichtbarkeit;
    if (!stand || this.speichert) {
      return;
    }
    this.speichert = true;
    this.fehler = false;
    this.usageTrackingService
      .setAbzeichenSichtbarkeit(zeigen, stand.aktueller_wortlaut.kennung)
      .pipe(takeUntil(this.destroy$))
      .subscribe((ok) => {
        this.speichert = false;
        if (ok) {
          this.sichtbarkeit = { ...stand, gefragt: true, zeigen };
          this.frageOffen = false;
        } else {
          this.fehler = true;
        }
        this.cdr.detectChanges();
        if (ok) {
          this.aendernKnopf?.nativeElement.focus();
        }
      });
  }
}
