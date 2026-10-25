import { Component, Input } from '@angular/core';

import { KartenDaten, KartenVariante } from './karten-daten';

/**
 * Ersatz fuer app-beitragskarte in Specs, die nur pruefen, ob und womit eine Karte
 * gerendert wird. Die echte Karte zieht Abstimmen, Kopieren und Melden samt Diensten
 * mit; die sind in beitragskarte.component.spec.ts abgedeckt.
 */
@Component({
  selector: 'app-beitragskarte',
  standalone: true,
  template: '<article class="karte-stub">{{ daten?.titel }}</article>',
})
export class BeitragskarteStubComponent {
  @Input() daten?: KartenDaten;
  @Input() variante: KartenVariante = 'voll';
  @Input() vorschau = false;
  @Input() abstimmenSichtbar = true;
}
