import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCheckboxChange, MatCheckboxModule } from '@angular/material/checkbox';

import { PunkteEinwilligungService } from './punkte-einwilligung.service';

/**
 * Das Häkchen „Punkte und Meilensteine“ (#351): eigener Wortlaut vom Server, nichts
 * vorausgewählt, Haken setzen willigt ein, Haken entfernen widerruft. Steht in „Meine
 * Beiträge“ und in den Datenschutz-Einstellungen; ohne eingeschaltete Punkte zeigt es
 * nichts.
 */
@Component({
  selector: 'app-punkte-einwilligung',
  standalone: true,
  imports: [CommonModule, MatCheckboxModule],
  templateUrl: './punkte-einwilligung.component.html',
  styleUrls: ['./punkte-einwilligung.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PunkteEinwilligungComponent implements OnInit {
  /** Eine eigene Überschrift, wo das Häkchen nicht schon unter einer steht (Datenschutz-Einstellungen). */
  @Input() ueberschrift: string | null = null;
  readonly stand$ = this.dienst.stand$;
  speichert = false;
  fehler = false;

  constructor(
    private dienst: PunkteEinwilligungService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.dienst.laden().subscribe();
  }

  aendern(ereignis: MatCheckboxChange): void {
    this.speichert = true;
    this.fehler = false;
    this.dienst.setzen(ereignis.checked).subscribe((ok) => {
      this.speichert = false;
      this.fehler = !ok;
      if (!ok) {
        // Der Haken springt zurück auf den gespeicherten Stand.
        ereignis.source.checked = !ereignis.checked;
      }
      this.cdr.markForCheck();
    });
  }
}
