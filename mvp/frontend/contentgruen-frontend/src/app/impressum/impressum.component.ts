import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { RouterModule } from '@angular/router';
import { LEGAL_ENTITY } from '../shared/legal-entity';

@Component({
  selector: 'app-impressum',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatDividerModule,
    RouterModule
  ],
  templateUrl: './impressum.component.html',
  styleUrls: ['./impressum.component.scss']
})
export class ImpressumComponent {
  readonly VEREIN = LEGAL_ENTITY;
  readonly KONTAKT_MAIL = LEGAL_ENTITY.KONTAKT_MAIL;
  readonly MSTV_VERANTWORTLICH = 'Sebastian Banach (Anschrift wie oben)';
}
