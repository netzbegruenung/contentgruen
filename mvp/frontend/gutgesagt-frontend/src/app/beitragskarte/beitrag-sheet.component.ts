import { NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, ElementRef, HostListener, Inject, signal } from '@angular/core';
import { MAT_BOTTOM_SHEET_DATA, MatBottomSheetRef } from '@angular/material/bottom-sheet';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { finalize } from 'rxjs/operators';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenDaten } from './karten-daten';
import { BeitragVerwaltenService } from './beitrag-verwalten.service';

export { loeschenFehlertext } from './beitrag-verwalten.service';

/** Ab so vielen Pixeln nach unten schliesst ein Wisch das Sheet. */
export const WISCH_SCHWELLE = 80;

/**
 * loeschbar und aenderbar nur aus "Meine Beitraege": dort ist es sicher der eigene
 * Beitrag. Aendern geht nur bei Kommentar und Hintergrundinfo (istAenderbar).
 * zurAdresse zeigt "Beitrag öffnen" im Menue (#300); aus, wo das Sheet mitten im
 * Schreiben aufgeht (Dublette, Destillieren) und die Eingabe sonst verloren ginge.
 */
export type BeitragSheetDaten = KartenDaten & { loeschbar?: boolean; aenderbar?: boolean; zurAdresse?: boolean };

/** Ergebnis des Sheets, wenn der Autor den Beitrag geloescht hat; die Liste laedt dann neu. */
export const GELOESCHT = 'geloescht';

/** Ergebnis des Sheets, wenn der Autor den Beitrag geaendert hat (#299); die Liste laedt dann neu. */
export const GEAENDERT = 'geaendert';

/**
 * Ein Beitrag aus dem Album als volle Karte im Bottom Sheet, mit Kopieren, Melden und
 * Herkunft; ohne Abstimmen, weil es der eigene Beitrag ist. Klick ausserhalb und Escape schliessen ueber MatBottomSheet selbst; den
 * Wisch nach unten bringt Material nicht mit. Er zaehlt nur, solange das Sheet ganz
 * oben steht, sonst gehoert die Geste dem Scrollen im Sheet.
 *
 * Mit loeschbar kann der Autor den Beitrag nach einer Rueckfrage loeschen (#250); das
 * Sheet schliesst dann mit GELOESCHT. Mit aenderbar oeffnet "Ändern" den Dialog fuer
 * Titel, Text und Herkunft (#299); gespeichert, schliesst das Sheet mit GEAENDERT.
 */
@Component({
  selector: 'app-beitrag-sheet',
  standalone: true,
  imports: [NgIf, BeitragskarteComponent, MatButtonModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="sheet-griff" aria-hidden="true"></div>
    <!-- Der eigene Beitrag: nicht abstimmen, Kopieren und Melden bleiben -->
    <app-beitragskarte [daten]="daten" variante="voll" [abstimmenSichtbar]="false"
                       [ansichtVerlinkt]="!!daten.zurAdresse"></app-beitragskarte>
    <div class="sheet-fuss" *ngIf="daten.loeschbar || daten.aenderbar">
      <button
        *ngIf="daten.aenderbar"
        mat-button
        type="button"
        class="aendern-knopf"
        [disabled]="aendertGerade()"
        (click)="aendern()"
      >
        <mat-icon>edit</mat-icon>
        Ändern
      </button>
      <button
        *ngIf="daten.loeschbar"
        mat-button
        type="button"
        class="loeschen-knopf"
        [disabled]="loeschtGerade()"
        (click)="loeschen()"
      >
        <mat-icon>delete</mat-icon>
        Beitrag löschen
      </button>
    </div>
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
        background: var(--feldrand);
      }

      app-beitragskarte {
        display: block;
        max-width: 450px;
        margin: 0 auto;
      }

      .sheet-fuss {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        max-width: 450px;
        margin: 8px auto 0;
      }

      .loeschen-knopf {
        color: var(--fehler);
      }
    `,
  ],
})
export class BeitragSheetComponent {
  private wischStart: number | null = null;

  /** Solange Rueckfrage oder Anfrage laufen: ein zweiter Klick oeffnet keine zweite Rueckfrage. */
  readonly loeschtGerade = signal(false);

  /** Solange der Dialog offen ist: ein zweiter Klick oeffnet keinen zweiten. */
  readonly aendertGerade = signal(false);

  constructor(
    @Inject(MAT_BOTTOM_SHEET_DATA) readonly daten: BeitragSheetDaten,
    private sheet: MatBottomSheetRef<BeitragSheetComponent>,
    private element: ElementRef<HTMLElement>,
    private verwalten: BeitragVerwaltenService,
  ) {}

  /** Den Beitrag im Dialog aendern; gespeichert, ist die Karte veraltet und das Sheet schliesst. */
  aendern(): void {
    if (this.aendertGerade()) {
      return;
    }
    this.aendertGerade.set(true);
    this.verwalten
      .aendern(this.daten)
      .pipe(finalize(() => this.aendertGerade.set(false)))
      .subscribe((gespeichert) => {
        if (gespeichert) {
          this.sheet.dismiss(GEAENDERT);
        }
      });
  }

  /** Nach der Rueckfrage loeschen; ist der Beitrag weg (auch schon vorher, 404), schliesst das Sheet. */
  loeschen(): void {
    if (this.loeschtGerade()) {
      return;
    }
    this.loeschtGerade.set(true);
    this.verwalten
      .loeschen(this.daten.id)
      .pipe(finalize(() => this.loeschtGerade.set(false)))
      .subscribe((weg) => {
        if (weg) {
          this.sheet.dismiss(GELOESCHT);
        }
      });
  }

  @HostListener('touchstart', ['$event'])
  wischBeginnen(event: TouchEvent): void {
    const container = this.element.nativeElement.closest('.mat-bottom-sheet-container');
    const obenAngekommen = (container?.scrollTop ?? 0) <= 0;
    this.wischStart = obenAngekommen ? (event.touches[0]?.clientY ?? null) : null;
  }

  @HostListener('touchend', ['$event'])
  wischBeenden(event: TouchEvent): void {
    const ende = event.changedTouches[0]?.clientY;
    if (this.wischStart !== null && ende !== undefined && ende - this.wischStart > WISCH_SCHWELLE) {
      this.sheet.dismiss();
    }
    this.wischStart = null;
  }
}
