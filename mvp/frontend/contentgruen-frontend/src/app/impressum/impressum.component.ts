import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { RouterModule } from '@angular/router';

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
  // TODO: Platzhalter durch die tatsaechlichen Angaben ersetzen.
  readonly KONTAKT_MAIL = '[E-Mail-Adresse]';
  readonly MSTV_VERANTWORTLICH = '[Name der verantwortlichen Person, Anschrift wie oben]';
}
