import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_BOTTOM_SHEET_DATA } from '@angular/material/bottom-sheet';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Observable } from 'rxjs';

import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, RohlingBeitrag, ausBeitrag } from '../beitragskarte/karten-daten';
import { ContentResult } from '../services/dtos/contributionDtos';
import { CommentaryService } from '../services/commentary.service';
import { GenericTextService } from '../services/generic-text.service';
import { LoggingService } from '../services/logging.service';

/** Was das Sheet braucht: die Beitraege eines Einwurfs, aelteste zuerst. */
export interface EinwurfBeitragSheetDaten {
  beitraege: RohlingBeitrag[];
}

/**
 * Die Beitraege eines Einwurfs im Bottom Sheet, als volle Karte wie im Album.
 *
 * Der Fangkorb kennt nur die IDs; den Beitrag holt das Sheet beim Oeffnen nach.
 * Bei genau einem Beitrag laedt es sofort, bei mehreren steht erst eine kleine
 * Auswahl - beschriftet mit dem Satz, aus dem der Beitrag entstanden ist.
 *
 * Nicht jeder Verweis fuehrt noch zu einem Beitrag: Verknuepfungen aus der Zeit
 * vor Fangkorb v2 tragen keinen Typ, und ein Beitrag kann inzwischen weg sein.
 * Beides endet in derselben Zeile, statt in einem leeren Sheet.
 */
@Component({
  selector: 'app-einwurf-beitrag-sheet',
  standalone: true,
  imports: [
    CommonModule,
    BeitragskarteComponent,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="sheet-griff" aria-hidden="true"></div>

    <ng-container *ngIf="auswahlOffen; else beitrag">
      <p class="sheet-titel">Aus diesem Einwurf sind mehrere Beiträge entstanden.</p>
      <ul class="auswahl">
        <li *ngFor="let eintrag of daten.beitraege; let i = index">
          <button type="button" mat-stroked-button class="auswahl-knopf" (click)="oeffnen(eintrag)">
            {{ eintrag.satz || 'Beitrag ' + (i + 1) }}
          </button>
        </li>
      </ul>
    </ng-container>

    <ng-template #beitrag>
      <button *ngIf="daten.beitraege.length > 1" type="button" mat-button class="zurueck"
              (click)="zurueckZurAuswahl()">
        <mat-icon aria-hidden="true">chevron_left</mat-icon>
        Zur Auswahl
      </button>

      <div *ngIf="laedt" class="sheet-laedt">
        <mat-spinner diameter="32"></mat-spinner>
      </div>

      <p *ngIf="fehler" class="sheet-fehler">Dieser Beitrag ist nicht mehr verfügbar.</p>

      <!-- Wie im Album: kopieren und melden bleiben, abstimmen nicht -->
      <app-beitragskarte *ngIf="karte as karte" [daten]="karte" variante="voll"
                         [abstimmenSichtbar]="false"></app-beitragskarte>
    </ng-template>
  `,
  styles: [
    `
      :host {
        display: block;
        padding-bottom: 16px;
      }

      .sheet-griff {
        width: 40px;
        height: 4px;
        margin: 4px auto 12px;
        border-radius: 2px;
        background: rgba(0, 0, 0, 0.24);
      }

      .sheet-titel {
        margin: 0 0 12px;
        color: var(--text-secondary);
        font-size: 14px;
      }

      .auswahl {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin: 0;
        padding: 0;
        list-style: none;
      }

      .auswahl-knopf {
        width: 100%;
        text-align: left;
      }

      .sheet-laedt {
        display: flex;
        justify-content: center;
        padding: 24px 0;
      }

      .sheet-fehler {
        margin: 0;
        padding: 16px 0;
        color: var(--text-secondary);
      }

      app-beitragskarte {
        display: block;
        max-width: 450px;
        margin: 0 auto;
      }
    `,
  ],
})
export class EinwurfBeitragSheetComponent implements OnInit {
  karte: KartenDaten | null = null;
  laedt = false;
  fehler = false;
  auswahlOffen = false;

  constructor(
    @Inject(MAT_BOTTOM_SHEET_DATA) readonly daten: EinwurfBeitragSheetDaten,
    private commentaryService: CommentaryService,
    private genericTextService: GenericTextService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    const [erster] = this.daten.beitraege;
    if (this.daten.beitraege.length === 1 && erster) {
      this.oeffnen(erster);
      return;
    }
    this.auswahlOffen = this.daten.beitraege.length > 1;
    this.fehler = !this.daten.beitraege.length;
  }

  oeffnen(beitrag: RohlingBeitrag): void {
    this.auswahlOffen = false;
    this.karte = null;
    this.fehler = false;
    const quelle = this.quelle(beitrag);
    if (!quelle) {
      this.fehler = true;
      this.cdr.markForCheck();
      return;
    }
    this.laedt = true;
    quelle.subscribe({
      next: (inhalt) => {
        this.karte = ausBeitrag(inhalt);
        this.laedt = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        this.logger.error('Beitrag aus dem Fangkorb konnte nicht geladen werden', error);
        this.laedt = false;
        this.fehler = true;
        this.cdr.markForCheck();
      },
    });
  }

  zurueckZurAuswahl(): void {
    this.auswahlOffen = true;
    this.karte = null;
    this.fehler = false;
  }

  /**
   * Beide Endpunkte liefern den Beitrag flach - dieselbe Form, die das Album aus
   * /getContributionsOfUser bekommt. Ohne bekannten Typ gibt es keinen Endpunkt.
   */
  private quelle(beitrag: RohlingBeitrag): Observable<ContentResult> | null {
    if (beitrag.typ === 'commentary') {
      return this.commentaryService.getCommentaryById(beitrag.contentId) as unknown as Observable<ContentResult>;
    }
    if (beitrag.typ === 'generictext') {
      return this.genericTextService.getGenericTextById(beitrag.contentId) as unknown as Observable<ContentResult>;
    }
    return null;
  }
}
