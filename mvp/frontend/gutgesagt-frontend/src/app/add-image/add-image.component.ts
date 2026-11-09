import { AfterViewInit, Component, ElementRef, EventEmitter, OnDestroy, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { TextFieldModule } from '@angular/cdk/text-field';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AddImageRequest, ImageService } from '../services/image.service';
import { LoggingService } from '../services/logging.service';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { typFarbe } from '../shared/content-type-registry';
import { Cc0HinweisComponent } from '../shared/cc0-hinweis/cc0-hinweis.component';
import { SprachhinweisComponent } from '../shared/components/sprachhinweis/sprachhinweis.component';
import { ThemenAuswahlComponent } from '../shared/themen/themen-auswahl.component';
import { einzeilig } from '../beitragsformular/einzeilig';
import { validierungsMeldung } from '../beitragsformular/speicherfehler';
import { FormularHilfeComponent } from '../beitragsformular/formular-hilfe/formular-hilfe.component';
import { GegenlesenComponent } from '../beitragsformular/gegenlesen/gegenlesen.component';
import { FormularLeisteComponent } from '../beitragsformular/formular-leiste/formular-leiste.component';
import {
  AntwortAuf,
  AntwortAufComponent,
  OHNE_AUSSAGE,
  zuKurz,
} from '../beitragsformular/antwort-auf/antwort-auf.component';
import { alsGespeichert, aussageFuerAnfrage } from '../beitragsformular/aussage-fuer-anfrage';
import { ThemenWahl } from '../beitragsformular/themen-wahl';
import type { BeitragGespeichert } from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';

/** Der Bild-Titel beschreibt, er ist keine Behauptung (CODING_STANDARDS.md); bis 200 Zeichen. */
export const TITEL_MAX = 200;
export const TEXT_MAX = 2000;

export const SPEICHERN_FEHLGESCHLAGEN =
  'Speichern hat nicht geklappt. Deine Eingaben sind noch da – versuch es gleich noch einmal.';

/** ``adresse`` so, wie der Browser sie als ``img.src`` fuehrt; unlesbar bleibt sie, wie sie ist. */
function aufgeloest(adresse: string): string {
  try {
    return new URL(adresse, location.href).href;
  } catch {
    return adresse;
  }
}

/**
 * Das Bild-Formular, mit denselben Bausteinen wie Kommentar, Hintergrundinfo und Post
 * (#619): Formularhilfe, "Antwort auf (optional)", Bild-URL, Titel und Unterschrift,
 * daneben (am Handy darunter) Vorschau und Gegenlesen, unten die Formular-Leiste.
 *
 * Gespeichert wird in einem Aufruf, samt Aussage. Danach meldet `success` ID, Aussage
 * und ob verknuepft wurde; wohin es weitergeht, entscheidet der Workflow (die
 * Ergebnisseite wie bei den anderen Typen).
 *
 * Laesst sich das Bild in der Vorschau nicht laden, sagt es ein Hinweis am Feld. Ein
 * fremdes Bild laedt erst auf Klick (#447); der Hinweis kommt dann auch erst danach.
 */
@Component({
  standalone: true,
  selector: 'app-add-image',
  templateUrl: './add-image.component.html',
  styleUrls: ['./add-image.component.scss'],
  imports: [
    ...SHARED_IMPORTS,
    CommonModule,
    ReactiveFormsModule,
    TextFieldModule,
    BeitragskarteComponent,
    FormularHilfeComponent,
    AntwortAufComponent,
    ThemenAuswahlComponent,
    GegenlesenComponent,
    SprachhinweisComponent,
    FormularLeisteComponent,
    Cc0HinweisComponent,
  ],
})
export class AddImageComponent implements AfterViewInit, OnDestroy {
  /** Streifen ueber dem Formular in der Farbe des Kartenbands. */
  readonly typFarbe = typFarbe('image');
  readonly titelMax = TITEL_MAX;
  readonly textMax = TEXT_MAX;

  @Output() success = new EventEmitter<BeitragGespeichert>();

  readonly imageForm: FormGroup;
  /** Die Themen einer neuen Aussage (#455). */
  readonly themenWahl: ThemenWahl;

  /** Was im Antwort-auf-Block gilt. */
  aussage: AntwortAuf = OHNE_AUSSAGE;

  speichert = false;
  fehler: string | null = null;
  /** Die knappe Validierungsmeldung des Backends bei 422; dann nicht "Erneut versuchen". */
  validierung: string | null = null;
  /** Gesetzt, sobald das Bild gespeichert ist. */
  responseId = '';

  /** Die Vorschau; dort laedt das Bild, und dort merkt man, ob es sich laden laesst. */
  @ViewChild('vorschau', { static: true }) private vorschau?: ElementRef<HTMLElement>;

  /**
   * Die Vorschau konnte das Bild unter der eingegebenen URL nicht laden. Dann steht ein
   * Hinweis am Feld, und die Vorschau zeigt kein kaputtes Bild. Speichern bleibt
   * moeglich: lenken, nicht sperren.
   */
  bildLadefehler = false;
  private bildUrl = '';

  private vorschauCache?: { werte: unknown; aussage: string; fehler: boolean; karte: KartenDaten };

  constructor(
    fb: FormBuilder,
    private imageService: ImageService,
    private logger: LoggingService,
  ) {
    this.imageForm = fb.group({
      image_url: ['', [Validators.required, Validators.pattern(/^https?:\/\/\S+$/)]],
      title: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(TITEL_MAX)]],
      caption: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(TEXT_MAX)]],
      themen: [[] as string[]],
    });
    this.themenWahl = new ThemenWahl(this.imageForm.get('themen')!);
    // Neue URL, neuer Versuch: der alte Ladefehler gilt nicht mehr.
    this.imageForm
      .get('image_url')!
      .valueChanges.pipe(takeUntilDestroyed())
      .subscribe((url: string | null) => {
        this.bildUrl = url || '';
        this.bildLadefehler = false;
      });
  }

  ngAfterViewInit(): void {
    // Das error-Ereignis eines Bildes steigt nicht auf; in der Capture-Phase kommt es hier an.
    this.vorschau?.nativeElement.addEventListener('error', this.beimLadefehler, true);
  }

  ngOnDestroy(): void {
    this.vorschau?.nativeElement.removeEventListener('error', this.beimLadefehler, true);
  }

  private readonly beimLadefehler = (ereignis: Event): void => {
    const bild = ereignis.target;
    if (!(bild instanceof HTMLImageElement) || !this.bildUrl || this.bildLadefehler) {
      return;
    }
    // Nur der Fehler zur aktuellen URL zaehlt, nicht ein verspaeteter zur vorigen.
    if (bild.src !== aufgeloest(this.bildUrl)) {
      return;
    }
    this.bildLadefehler = true;
  };

  /** Was im Antwort-auf-Block gilt; die Themen passen sich an (ThemenWahl). */
  aussageSetzen(aussage: AntwortAuf): void {
    this.aussage = aussage;
    this.themenWahl.anAussageAnpassen(aussage);
  }

  get zeigtThemen(): boolean {
    return this.themenWahl.zeigtFuer(this.aussage);
  }

  /** Aussage ohne Auswahl mit 1-9 Zeichen: Speichern bleibt gesperrt, leer ist erlaubt. */
  get aussageZuKurz(): boolean {
    return !this.aussage.id && zuKurz(this.aussage.text);
  }

  get titelLaenge(): number {
    return this.imageForm.get('title')?.value?.length ?? 0;
  }

  get textLaenge(): number {
    return this.imageForm.get('caption')?.value?.length ?? 0;
  }

  /**
   * Die Vorschau als KartenDaten, zwischengespeichert, solange sich nichts aendert.
   * Ohne Nutzung und Datum: Ueber einen Entwurf sagen sie nichts. Nach einem Ladefehler
   * ohne Bild statt mit kaputtem Bildsymbol.
   */
  get vorschauKarte(): KartenDaten {
    const werte = this.imageForm.value;
    const cache = this.vorschauCache;
    if (cache && cache.werte === werte && cache.aussage === this.aussage.text && cache.fehler === this.bildLadefehler) {
      return cache.karte;
    }
    const karte = ausSuchergebnis({
      image_result: {
        id: 'vorschau',
        content_type: 'image',
        title: werte.title || 'Titel',
        text: werte.caption || 'Worum es auf dem Bild geht',
        image_url: this.bildLadefehler ? '' : werte.image_url || '',
        original_author: 'Du',
      },
      score: 1,
      statement_text: this.aussage.text,
      statement_similarity_score: 0,
      reply_relevance: 0,
    } as any);
    this.vorschauCache = {
      werte,
      aussage: this.aussage.text,
      fehler: this.bildLadefehler,
      karte: { ...karte, nutzung: null, erstellt: '', autorName: 'Du' },
    };
    return this.vorschauCache.karte;
  }

  speichern(): void {
    if (this.imageForm.invalid || this.aussageZuKurz) {
      this.imageForm.markAllAsTouched();
      return;
    }
    if (this.speichert) {
      return;
    }

    this.speichert = true;
    this.fehler = null;
    this.validierung = null;

    const { image_url, title, caption, themen } = this.imageForm.value;
    const aussage = aussageFuerAnfrage(this.aussage, themen ?? []);
    const request: AddImageRequest = {
      image: {
        // Ein Titel ist eine Zeile: eingefuegte Umbrueche werden zu Leerzeichen.
        title: einzeilig(title),
        image_url: image_url.trim(),
        text: caption,
      },
      ...aussage,
    };

    this.imageService.addImage(request).subscribe({
      next: (antwort) => {
        this.speichert = false;
        this.responseId = antwort.id;
        this.success.emit(alsGespeichert(antwort.id, this.aussage, aussage, antwort));
      },
      error: (error: Error) => {
        // Die Eingaben bleiben stehen; der Knopf speichert dasselbe noch einmal.
        this.logger.error('Error saving image', error);
        this.speichert = false;
        this.validierung = validierungsMeldung(error);
        this.fehler = this.validierung ?? SPEICHERN_FEHLGESCHLAGEN;
      },
    });
  }
}
