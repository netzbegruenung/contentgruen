import { ChangeDetectionStrategy, Component, ElementRef, HostListener, Inject } from '@angular/core';
import { MAT_BOTTOM_SHEET_DATA, MatBottomSheetRef } from '@angular/material/bottom-sheet';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenDaten } from './karten-daten';

/** Ab so vielen Pixeln nach unten schliesst ein Wisch das Sheet. */
export const WISCH_SCHWELLE = 80;

/**
 * Ein Beitrag aus dem Album als volle Karte im Bottom Sheet, mit Aktionsleiste und
 * Herkunft. Klick ausserhalb und Escape schliessen ueber MatBottomSheet selbst; den
 * Wisch nach unten bringt Material nicht mit. Er zaehlt nur, solange das Sheet ganz
 * oben steht, sonst gehoert die Geste dem Scrollen im Sheet.
 */
@Component({
  selector: 'app-beitrag-sheet',
  standalone: true,
  imports: [BeitragskarteComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="sheet-griff" aria-hidden="true"></div>
    <app-beitragskarte [daten]="daten" variante="voll"></app-beitragskarte>
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

      app-beitragskarte {
        display: block;
        max-width: 450px;
        margin: 0 auto;
      }
    `,
  ],
})
export class BeitragSheetComponent {
  private wischStart: number | null = null;

  constructor(
    @Inject(MAT_BOTTOM_SHEET_DATA) readonly daten: KartenDaten,
    private sheet: MatBottomSheetRef<BeitragSheetComponent>,
    private element: ElementRef<HTMLElement>,
  ) {}

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
