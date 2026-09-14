import { Component, OnDestroy, OnInit } from '@angular/core';
import { AbstractControl, FormBuilder, FormGroup, ValidationErrors, Validators } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { TextFieldModule } from '@angular/cdk/text-field';
import { RawInputService, AddRawInputRequest } from '../services/raw-input.service';
import {
  GeteilterEinwurf,
  SHARE_EINWURF_SCHLUESSEL,
  einwurfAusShareDaten,
} from '../share-target/share-target.guard';
import { trackingParameterEntfernen, urlsInTextBereinigen } from '../shared/url-bereinigen';
import { FANGKORB_BESCHREIBUNG } from '../shared/fangkorb-texte';
import { CONSENT_HINWEIS } from '../shared/consent-hinweis';
import { LoggingService } from '../services/logging.service';
import { NavigationService } from '../services/navigation.service';
import { Router, RouterLink } from '@angular/router';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { Subject } from 'rxjs';

export const HINWEIS_LIMIT = 5000;

/**
 * Womit ein Seitentitel im Hinweis-Feld als Vorbelegung erkennbar bleibt -- im
 * Formular und, falls die Person ihn stehen laesst, auch spaeter im Fangkorb.
 */
export const SEITENTITEL_PRAEFIX = 'Seitentitel: ';

/** Ein Link und nur ein Link. Der Server prueft ihn noch einmal richtig. */
const NUR_EIN_LINK = /^https?:\/\/\S+$/i;

function nurEinLink(control: AbstractControl): ValidationErrors | null {
  const wert = (control.value ?? '').trim();
  return wert && !NUR_EIN_LINK.test(wert) ? { keinLink: true } : null;
}

/** Der Vorschlag fuer das Hinweis-Feld aus einem geteilten Einwurf, oder null. */
export function hinweisVorschlag(geteilt: GeteilterEinwurf): string | null {
  const zeilen = [
    geteilt.titel ? `${SEITENTITEL_PRAEFIX}${geteilt.titel}` : null,
    geteilt.text,
  ].filter((zeile): zeile is string => !!zeile);
  return zeilen.length ? zeilen.join('\n').slice(0, HINWEIS_LIMIT) : null;
}

/**
 * Einwerfen: zwei Felder, Link und Hinweis fuer andere. Eines davon genuegt.
 *
 * Keine Kategorien, keine Labels, keine Schalter -- alles Weitere ist schon
 * Destillieren. Kommt der Einwurf aus dem Teilen-Menue, steht der Link im
 * Link-Feld; Seitentitel und uebriger Text stehen als markierte Vorbelegung im
 * Hinweis-Feld und werden nur gespeichert, wenn die Person sie stehen laesst.
 */
@Component({
  selector: 'app-add-raw-input',
  standalone: true,
  imports: [...SHARED_IMPORTS, CommonModule, RouterLink, TextFieldModule],
  templateUrl: './add-raw-input.component.html',
  styleUrls: ['./add-raw-input.component.css'],
})
export class AddRawInputComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  readonly hinweisLimit = HINWEIS_LIMIT;
  readonly fangkorbBeschreibung = FANGKORB_BESCHREIBUNG;
  readonly consentHinweis = CONSENT_HINWEIS;

  einwurfForm: FormGroup;

  wirdGespeichert = false;
  fehler: string | null = null;
  /** Anzahl der Einwuerfe in dieser Sitzung - das Formular bleibt ja offen. */
  eingeworfen = 0;
  /**
   * Ob der aktuelle Feldinhalt aus dem Teilen-Menue stammt. Steuert nur den
   * Herkunftskanal des naechsten Einwurfs und wird danach zurueckgesetzt: das
   * Formular bleibt offen, und was jemand danach von Hand eintippt, ist wieder
   * ein Web-Einwurf.
   */
  ausShare = false;
  /** Der Text, mit dem das Hinweis-Feld aus dem Teilen vorbelegt wurde. */
  vorbelegung: string | null = null;

  constructor(
    private fb: FormBuilder,
    private rawInputService: RawInputService,
    private logger: LoggingService,
    private navigationService: NavigationService,
    private router: Router,
  ) {
    this.einwurfForm = this.fb.group({
      link: ['', nurEinLink],
      hinweis: ['', Validators.maxLength(HINWEIS_LIMIT)],
    });
  }

  ngOnInit(): void {
    const geteilt = this.geteiltenEinwurfHolen();
    if (geteilt) {
      this.vorbelegung = hinweisVorschlag(geteilt);
      this.einwurfForm.patchValue({ link: geteilt.url ?? '', hinweis: this.vorbelegung ?? '' });
      this.ausShare = true;
    }
  }

  /**
   * Holt einen ueber das Teilen-Menue hereingereichten Einwurf und raeumt ihn weg.
   *
   * Einmalig mit Absicht: bleibt der Wert liegen, befuellt sich das Formular auch
   * beim naechsten regulaeren Aufruf wieder mit demselben Link. Der Zugriff kann
   * werfen (privater Modus, blockierte Seitendaten) -- dann gibt es eben keine
   * Vorbelegung, aber das Formular funktioniert. Liegt noch Klartext einer
   * aelteren Version dort, wird er wie ein geteilter Text zerlegt.
   */
  private geteiltenEinwurfHolen(): GeteilterEinwurf | null {
    let wert: string | null;
    try {
      wert = sessionStorage.getItem(SHARE_EINWURF_SCHLUESSEL);
      if (wert) {
        sessionStorage.removeItem(SHARE_EINWURF_SCHLUESSEL);
      }
    } catch {
      return null;
    }
    if (!wert) {
      return null;
    }

    try {
      const gelesen = JSON.parse(wert) as Partial<GeteilterEinwurf> | null;
      if (gelesen && typeof gelesen === 'object') {
        return {
          url: typeof gelesen.url === 'string' ? gelesen.url : null,
          titel: typeof gelesen.titel === 'string' ? gelesen.titel : null,
          text: typeof gelesen.text === 'string' ? gelesen.text : null,
        };
      }
    } catch {
      // Kein JSON: Klartext einer aelteren Version, siehe unten.
    }
    return einwurfAusShareDaten({ text: wert });
  }

  get link(): string {
    return (this.einwurfForm.value.link ?? '').trim();
  }

  get hinweis(): string {
    return (this.einwurfForm.value.hinweis ?? '').trim();
  }

  /** Beide Felder leer - die einzige Pflicht, die der Fangkorb kennt. */
  get istLeer(): boolean {
    return !this.link && !this.hinweis;
  }

  get kannEinwerfen(): boolean {
    return !this.istLeer && this.einwurfForm.valid && !this.wirdGespeichert;
  }

  /** Solange der Vorschlag unveraendert dasteht, ist er als Vorbelegung markiert. */
  get istVorbelegt(): boolean {
    return !!this.vorbelegung && this.einwurfForm.value.hinweis === this.vorbelegung;
  }

  vorbelegungEntfernen(): void {
    this.einwurfForm.patchValue({ hinweis: '' });
    this.vorbelegung = null;
  }

  einwerfen(): void {
    if (!this.kannEinwerfen) {
      this.einwurfForm.markAllAsTouched();
      return;
    }

    // Tracking-Parameter fliegen hier raus und nicht erst im Share-Pfad: dieselbe
    // Adresse von Hand eingefuegt haette sonst dasselbe Problem -- pro Einwurf ein
    // anderer Link, und ein fremdes Token in der Datenbank.
    const anfrage: AddRawInputRequest = {};
    if (this.link) {
      anfrage.url = trackingParameterEntfernen(this.link);
    }
    if (this.hinweis) {
      anfrage.content = urlsInTextBereinigen(this.hinweis);
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
        this.einwurfForm.reset({ link: '', hinweis: '' });
        this.vorbelegung = null;
        this.ausShare = false;
      },
      error: (error) => {
        this.logger.error('Einwurf fehlgeschlagen', error);
        this.wirdGespeichert = false;
        this.fehler =
          error?.status === 422
            ? 'Damit kann der Fangkorb nichts anfangen. Bitte prüfe den Link.'
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
