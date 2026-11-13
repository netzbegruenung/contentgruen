import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

/**
 * Aussagekarte: eine unbeantwortete Aussage als Karte im Stil der Beitragskarte
 * (Kopfband, Koerper, Fuss mit "Antworten"). Inhalte erscheinen als Karten; die
 * Beitragskarte gibt es fuer Beitraege und Einwuerfe, diese hier fuer Aussagen.
 * Zusaetzliches im Koerper (etwa die Themen) kommt per Content Projection.
 * Mehrere Karten stehen in einer ul.aussagekarten (aussagekarten.css).
 */
@Component({
  selector: 'app-aussagekarte',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './aussagekarte.component.html',
  styleUrls: ['./aussagekarte.component.css'],
})
export class AussagekarteComponent {
  /** Text der Aussage, steht als Titel im Kopfband. */
  @Input({ required: true }) text = '';
  /** Id des Titels; "Antworten" verweist per aria-describedby darauf. */
  @Input({ required: true }) titelId = '';
  /** Zusaetzliche Klasse am Titel, damit Seiten ihre bisherigen Selektoren behalten. */
  @Input() titelKlasse = '';
  /** Nachfrage, etwa "3 Personen suchten das ohne Treffer"; leer = keine Zeile. */
  @Input() gesucht = '';
  /** Ziel von "Antworten" (Kommentarformular) samt Query-Parametern. */
  @Input({ required: true }) antwortenPfad = '';
  @Input() antwortenParams: Record<string, string> = {};
}
