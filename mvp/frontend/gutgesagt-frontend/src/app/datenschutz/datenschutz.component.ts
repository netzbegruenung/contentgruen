import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { RouterModule } from '@angular/router';
import { LEGAL_ENTITY } from '../shared/legal-entity';

@Component({
  selector: 'app-datenschutz',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatDividerModule,
    RouterModule
  ],
  templateUrl: './datenschutz.component.html',
  styleUrls: ['./datenschutz.component.scss']
})
export class DatenschutzComponent {
  readonly VEREIN = LEGAL_ENTITY;
  readonly KONTAKT_MAIL = LEGAL_ENTITY.KONTAKT_MAIL;

  // Der Datenschutzbeauftragte ist ueber die Vereinsadresse erreichbar, nicht privat.
  readonly DSB_KONTAKT = `Sven Seeberg, erreichbar über ${LEGAL_ENTITY.KONTAKT_MAIL}`;

  // Zustaendig ist die Aufsichtsbehoerde am Sitz des Verantwortlichen: der Verein sitzt in
  // Donauwoerth, das Vereinsregister liegt beim Amtsgericht Augsburg -- beides Bayern, und
  // fuer nichtoeffentliche Stellen ist dort das BayLDA zustaendig.
  readonly BEHOERDE_NAME = 'Bayerisches Landesamt für Datenschutzaufsicht (BayLDA)';
  readonly BEHOERDE_ANSCHRIFT = 'Promenade 18, 91522 Ansbach';
  readonly BEHOERDE_TELEFON = '+49 981 180093-0';
  readonly BEHOERDE_URL = 'https://www.lda.bayern.de';
}
