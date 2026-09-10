import { Component, OnInit } from '@angular/core';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { einwurfZerlegen } from '../add-raw-input/add-raw-input.component';
import { AddRawInputRequest } from '../services/raw-input.service';

/**
 * Diagnose-Ansicht fuer das Android-Teilen-Menue -- Schritt 0.
 *
 * Sie speichert nichts und ruft keine API. Ihr einziger Zweck ist, sichtbar zu
 * machen, was Instagram (und andere Apps) beim Teilen tatsaechlich schicken:
 * welche Parameter ankommen, in welchem davon der Link steckt, und ob ueberhaupt
 * einer ankommt. Alles Weitere haengt an dieser Antwort -- die Aufteilung auf
 * ``url`` und ``content`` im Fangkorb ebenso wie die Frage, ob GET reicht oder es
 * doch POST mit multipart braucht.
 *
 * Das ist bewusst Wegwerf-Code: In Schritt 2 ersetzt die echte Uebernahme in den
 * Fangkorb diese Komponente unter derselben Route ``/teilen``, damit das
 * share_target im Manifest sich nicht aendern muss und einmal installierte
 * Geraete nichts neu installieren muessen.
 */

/** Ein Parameter, wie er in der Tabelle steht. */
interface ParameterZeile {
  name: string;
  wert: string;
  /** True, wenn der Parameter im Manifest deklariert ist (title/text/url). */
  erwartet: boolean;
}

/** Die drei Felder, die das Manifest als share_target-Parameter anmeldet. */
const ERWARTETE_PARAMETER = ['title', 'text', 'url'];

@Component({
  selector: 'app-share-target-debug',
  standalone: true,
  imports: [...SHARED_IMPORTS],
  templateUrl: './share-target-debug.component.html',
  styleUrls: ['./share-target-debug.component.css'],
})
export class ShareTargetDebugComponent implements OnInit {
  /** Die vollstaendige aufgerufene Adresse, ungekuerzt und unveraendert. */
  volleUrl = '';

  /** Alle Query-Parameter -- auch nicht angemeldete, falls der Browser mehr schickt. */
  parameter: ParameterZeile[] = [];

  /** True, wenn ueberhaupt kein Parameter ankam. Dann lief der Aufruf ohne Teilen. */
  ohneParameter = false;

  title: string | null = null;
  text: string | null = null;
  url: string | null = null;

  /**
   * Was ``einwurfZerlegen`` aus dem text-Parameter machen wuerde -- die Funktion,
   * die das Einwurf-Formular heute schon benutzt. Nur zur Anschauung.
   */
  zerlegung: AddRawInputRequest | null = null;

  /** Anzeigekontext: aus dem installierten Fenster heraus oder aus dem Browser-Tab. */
  anzeigeModus = '';

  /**
   * Wann der Aufruf ankam -- einmal in ngOnInit festgehalten, nicht im Getter
   * erzeugt. Ein ``new Date()`` im Getter liefert bei jedem Change-Detection-Lauf
   * einen anderen Wert; Angular meldet das zu Recht als
   * ExpressionChangedAfterItHasBeenChecked.
   */
  zeitpunkt = '';
  userAgent = '';
  /** Gesetzt, sobald der Bericht in der Zwischenablage liegt. */
  kopiert = false;

  ngOnInit(): void {
    this.zeitpunkt = new Date().toISOString();
    this.volleUrl = window.location.href;
    this.userAgent = window.navigator.userAgent;
    this.anzeigeModus = this.anzeigeModusErmitteln();

    // Bewusst ueber URLSearchParams statt ueber die Route: so tauchen auch
    // Parameter auf, die wir nicht angemeldet haben. Genau die waeren die
    // interessante Ueberraschung.
    // forEach statt entries(): die tsconfig bindet DOM.Iterable nicht ein.
    const suchteil = new URLSearchParams(window.location.search);
    const zeilen: ParameterZeile[] = [];
    suchteil.forEach((wert, name) => {
      zeilen.push({ name, wert, erwartet: ERWARTETE_PARAMETER.includes(name) });
    });
    this.parameter = zeilen;
    this.ohneParameter = this.parameter.length === 0;

    this.title = suchteil.get('title');
    this.text = suchteil.get('text');
    this.url = suchteil.get('url');

    if (this.text) {
      this.zerlegung = einwurfZerlegen(this.text);
    }
  }

  /**
   * Chrome startet ein installiertes Share-Ziel im PWA-Fenster (standalone). Steht
   * hier "browser", lief der Aufruf ueber einen normalen Tab -- dann ist entweder
   * die Installation nicht erfolgt oder die Adresse wurde von Hand aufgerufen.
   */
  private anzeigeModusErmitteln(): string {
    const modi = ['standalone', 'minimal-ui', 'fullscreen', 'window-controls-overlay'];
    const treffer = modi.find((modus) => window.matchMedia(`(display-mode: ${modus})`).matches);
    return treffer ?? 'browser';
  }

  /**
   * Der Bericht als Klartext -- das, was zurueck an die Entwicklung geht.
   *
   * Auch im Template sichtbar, nicht nur in der Zwischenablage: auf dem Telefon
   * ist Markieren und Kopieren muehsam, und schlaegt die Clipboard-API fehl,
   * bleibt der Text wenigstens ablesbar.
   */
  get bericht(): string {
    const zeilen = [
      '--- Share-Target-Diagnose ---',
      `Zeitpunkt:     ${this.zeitpunkt}`,
      `Anzeigemodus:  ${this.anzeigeModus}`,
      `Volle URL:     ${this.volleUrl}`,
      `User-Agent:    ${this.userAgent}`,
      '',
      'Parameter:',
    ];

    if (this.ohneParameter) {
      zeilen.push('  (keine)');
    } else {
      for (const zeile of this.parameter) {
        zeilen.push(`  ${zeile.name}${zeile.erwartet ? '' : ' (nicht angemeldet!)'} = ${zeile.wert}`);
      }
    }

    zeilen.push('', 'Zerlegung des text-Parameters:');
    zeilen.push(this.zerlegung ? `  ${JSON.stringify(this.zerlegung)}` : '  (kein text-Parameter)');

    return zeilen.join('\n');
  }

  async berichtKopieren(): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.bericht);
      this.kopiert = true;
    } catch {
      // Kein Grund fuer eine Fehlermeldung: der Bericht steht ohnehin auf der Seite.
      this.kopiert = false;
    }
  }
}
