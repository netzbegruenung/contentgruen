import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import {
  EINLADUNG_KONTEN_MAX,
  EINLADUNG_NOTIZ_MAX,
  Einladung,
  EinladungService,
  einladungslink,
} from '../../shared/einladung/einladung.service';

/** Heute plus n Tage als JJJJ-MM-TT, im Kalender des Browsers. */
function inTagen(tage: number, heute = new Date()): string {
  const d = new Date(heute.getFullYear(), heute.getMonth(), heute.getDate() + tage);
  const zwei = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${zwei(d.getMonth() + 1)}-${zwei(d.getDate())}`;
}

/**
 * Einladungen verwalten (#429): anlegen, abschalten, Zaehler sehen. Gruppenlink und
 * persoenlicher Link sind dieselbe Einladung, nur mit anderen Zahlen; der Standard ist
 * der persoenliche (ein Konto, zwei Wochen).
 */
@Component({
  selector: 'app-einladungen',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
  ],
  templateUrl: './einladungen.component.html',
  styleUrls: ['./einladungen.component.css'],
})
export class EinladungenComponent implements OnInit {
  readonly NOTIZ_MAX = EINLADUNG_NOTIZ_MAX;
  readonly KONTEN_MAX = EINLADUNG_KONTEN_MAX;

  einladungen: Einladung[] | null = null;
  registrierungEingerichtet = true;
  fehler = false;
  anlegenFehler = false;
  speichert = false;
  kopiert: string | null = null;

  notiz = '';
  erlaubteKonten = 1;
  gueltigBis = inTagen(14);

  constructor(private einladungService: EinladungService) {}

  ngOnInit() {
    this.einladungService.liste().subscribe({
      next: (liste) => {
        this.einladungen = liste.einladungen;
        this.registrierungEingerichtet = liste.registrierung_eingerichtet;
      },
      error: () => (this.fehler = true),
    });
  }

  anlegen() {
    if (!this.notiz.trim() || this.speichert) {
      return;
    }
    this.speichert = true;
    this.anlegenFehler = false;
    this.einladungService.anlegen(this.notiz.trim(), this.erlaubteKonten, this.gueltigBis).subscribe({
      next: (neu) => {
        this.einladungen = [neu, ...(this.einladungen ?? [])];
        this.notiz = '';
        this.speichert = false;
      },
      error: () => {
        this.anlegenFehler = true;
        this.speichert = false;
      },
    });
  }

  schalten(einladung: Einladung) {
    this.einladungService.schalten(einladung.id, !einladung.abgeschaltet).subscribe({
      next: (neu) => {
        this.einladungen = (this.einladungen ?? []).map((e) => (e.id === neu.id ? neu : e));
      },
      error: () => (this.fehler = true),
    });
  }

  link(einladung: Einladung): string {
    return einladungslink(einladung.code);
  }

  kopieren(einladung: Einladung) {
    navigator.clipboard?.writeText(this.link(einladung)).then(() => (this.kopiert = einladung.id));
  }

  /** JJJJ-MM-TT als TT.MM.JJJJ, ohne Umweg ueber Date und Zeitzone. */
  tag(iso: string): string {
    const [jahr, monat, tag] = iso.split('-');
    return `${tag}.${monat}.${jahr}`;
  }
}
