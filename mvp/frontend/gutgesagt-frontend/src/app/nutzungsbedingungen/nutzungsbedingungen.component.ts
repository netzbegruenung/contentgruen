import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { RouterModule } from '@angular/router';
import { LEGAL_ENTITY } from '../shared/legal-entity';
import { CC0_ERKLAERUNG_URL } from '../shared/consent-hinweis';

@Component({
  selector: 'app-nutzungsbedingungen',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatDividerModule,
    RouterModule
  ],
  templateUrl: './nutzungsbedingungen.component.html',
  styleUrls: ['./nutzungsbedingungen.component.scss']
})
export class NutzungsbedingungenComponent {
  readonly KONTAKT_MAIL = LEGAL_ENTITY.KONTAKT_MAIL;
  /** Dieselbe CC0-Erklaerung, die der CC0-Hinweis verlinkt. */
  readonly cc0Url = CC0_ERKLAERUNG_URL;
}
