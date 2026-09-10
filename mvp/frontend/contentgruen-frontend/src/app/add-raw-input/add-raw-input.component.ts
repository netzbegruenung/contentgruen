import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RawInputService, AddRawInputRequest } from '../services/raw-input.service';
import { SHARE_EINWURF_SCHLUESSEL } from '../share-target/share-target.guard';
import { urlsInTextBereinigen } from '../shared/url-bereinigen';
import { LoggingService } from '../services/logging.service';
import { NavigationService } from '../services/navigation.service';
import { Router, RouterLink } from '@angular/router';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { Subject } from 'rxjs';

/**
 * Erkennt die erste http(s)-URL in einem Text.
 * Bewusst schlicht: der Server prueft die URL noch einmal richtig.
 */
const URL_MUSTER = /https?:\/\/[^\s]+/i;

/**
 * Ein Textfeld, zwei Bedeutungen: Wer einen Link einwirft, soll ihn nicht erst
 * als Link deklarieren muessen.
 *
 * - nur eine URL          -> url
 * - URL mit Text drumherum -> url (die erste) und content (alles)
 * - kein Link             -> content
 */
export function einwurfZerlegen(eingabe: string): AddRawInputRequest {
  const text = (eingabe || '').trim();
  const treffer = text.match(URL_MUSTER);

  if (!treffer) {
    return { content: text };
  }

  const url = treffer[0];
  return url === text ? { url } : { url, content: text };
}

@Component({
  selector: 'app-add-raw-input',
  standalone: true,
  imports: [...SHARED_IMPORTS, CommonModule, RouterLink],
  templateUrl: './add-raw-input.component.html',
  styleUrls: ['./add-raw-input.component.css'],
})
export class AddRawInputComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  einwurfForm: FormGroup;

  wirdGespeichert = false;
  fehler: string | null = null;
  /** Anzahl der Einwuerfe in dieser Sitzung - das Formular bleibt ja offen. */
  eingeworfen = 0;
  zeigeBildFeld = false;
  /**
   * Ob der aktuelle Feldinhalt aus dem Teilen-Menue stammt. Steuert nur den
   * Herkunftskanal des naechsten Einwurfs und wird danach zurueckgesetzt: das
   * Formular bleibt offen, und was jemand danach von Hand eintippt, ist wieder
   * ein Web-Einwurf.
   */
  ausShare = false;

  constructor(
    private fb: FormBuilder,
    private rawInputService: RawInputService,
    private logger: LoggingService,
    private navigationService: NavigationService,
    private router: Router,
  ) {
    this.einwurfForm = this.fb.group({
      einwurf: [''],
      imageUrl: [''],
    });
  }

  ngOnInit(): void {
    const geteilt = this.geteiltenEinwurfHolen();
    if (geteilt) {
      this.einwurfForm.patchValue({ einwurf: geteilt });
      this.ausShare = true;
    }
  }

  /**
   * Holt einen ueber das Teilen-Menue hereingereichten Einwurf und raeumt ihn weg.
   *
   * Einmalig mit Absicht: bleibt der Wert liegen, befuellt sich das Formular auch
   * beim naechsten regulaeren Aufruf wieder mit demselben Link. Der Zugriff kann
   * werfen (privater Modus, blockierte Seitendaten) -- dann gibt es eben keine
   * Vorbelegung, aber das Formular funktioniert.
   */
  private geteiltenEinwurfHolen(): string | null {
    try {
      const wert = sessionStorage.getItem(SHARE_EINWURF_SCHLUESSEL);
      if (wert) {
        sessionStorage.removeItem(SHARE_EINWURF_SCHLUESSEL);
      }
      return wert;
    } catch {
      return null;
    }
  }

  /** Leer ist leer - die einzige Pflicht, die der Fangkorb kennt. */
  get istLeer(): boolean {
    const { einwurf, imageUrl } = this.einwurfForm.value;
    return !einwurf?.trim() && !imageUrl?.trim();
  }

  bildFeldUmschalten(): void {
    this.zeigeBildFeld = !this.zeigeBildFeld;
    if (!this.zeigeBildFeld) {
      this.einwurfForm.get('imageUrl')?.setValue('');
    }
  }

  einwerfen(): void {
    if (this.istLeer || this.wirdGespeichert) {
      return;
    }

    const { einwurf, imageUrl } = this.einwurfForm.value;
    // Tracking-Parameter fliegen hier raus und nicht erst im Share-Pfad: dieselbe
    // Adresse von Hand eingefuegt haette sonst dasselbe Problem -- pro Einwurf ein
    // anderer Link, und ein fremdes Token in der Datenbank.
    const anfrage: AddRawInputRequest = einwurf?.trim()
      ? einwurfZerlegen(urlsInTextBereinigen(einwurf))
      : {};

    const bild = imageUrl?.trim();
    if (bild) {
      anfrage.image_url = bild;
    }

    if (this.ausShare) {
      anfrage.source_channel = 'share';
    }

    this.wirdGespeichert = true;
    this.fehler = null;

    this.rawInputService.addRawInput(anfrage).subscribe({
      next: () => {
        this.wirdGespeichert = false;
        this.eingeworfen += 1;
        // Formular bleibt offen und leer: drei Sachen hintereinander einwerfen
        // ist der Normalfall, nicht die Ausnahme.
        this.einwurfForm.reset({ einwurf: '', imageUrl: '' });
        this.zeigeBildFeld = false;
        this.ausShare = false;
      },
      error: (error) => {
        this.logger.error('Einwurf fehlgeschlagen', error);
        this.wirdGespeichert = false;
        this.fehler =
          error?.status === 422
            ? 'Damit kann der Fangkorb nichts anfangen. Bitte pruefe die Adresse.'
            : 'Der Einwurf konnte nicht gespeichert werden. Bitte versuche es erneut.';
      },
    });
  }

  zumFangkorb(): void {
    this.router.navigate(['/fangkorb']);
  }

  zurueckZurStartseite(): void {
    this.navigationService.navigateToStart();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
