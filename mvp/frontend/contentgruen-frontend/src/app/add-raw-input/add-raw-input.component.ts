import { Component, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RawInputService, AddRawInputRequest } from '../services/raw-input.service';
import { LoggingService } from '../services/logging.service';
import { NavigationService } from '../services/navigation.service';
import { Router } from '@angular/router';
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
  imports: [...SHARED_IMPORTS, CommonModule],
  templateUrl: './add-raw-input.component.html',
  styleUrls: ['./add-raw-input.component.css'],
})
export class AddRawInputComponent implements OnDestroy {
  private destroy$ = new Subject<void>();

  einwurfForm: FormGroup;

  wirdGespeichert = false;
  fehler: string | null = null;
  /** Anzahl der Einwuerfe in dieser Sitzung - das Formular bleibt ja offen. */
  eingeworfen = 0;
  zeigeBildFeld = false;

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
    const anfrage: AddRawInputRequest = einwurf?.trim()
      ? einwurfZerlegen(einwurf)
      : {};

    const bild = imageUrl?.trim();
    if (bild) {
      anfrage.image_url = bild;
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
