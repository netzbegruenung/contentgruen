import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Observable } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';

import { SHARED_IMPORTS } from '../../shared/shared-imports';
import { BeitragskarteComponent } from '../../beitragskarte/beitragskarte.component';
import { KartenDaten, ausAussage, ausSuchergebnis } from '../../beitragskarte/karten-daten';
import { CommentaryService } from '../../services/commentary.service';
import { GenericTextService } from '../../services/generic-text.service';
import { LoggingService } from '../../services/logging.service';
import { NavigationService } from '../../services/navigation.service';
import { VERKNUEPFUNG_FEHLGESCHLAGEN } from '../../services/statement.service';
import { DestillierUebergabeService } from '../../destillieren/destillier-uebergabe.service';
import { tabMerken } from '../../raw-input-list/fangkorb-filter';
import { FORMULAR_PFAD, FormularTyp } from '../../shared/formular-adresse';
import {
  GespeichertZustand,
  Herkunft,
  ROHINPUT_ADRESSE_PARAM,
  SUCHE_PARAM,
  herkunftAus,
} from './gespeichert-adresse';

/** Beitragstypen, fuer die es die Ergebnisseite gibt. */
export type GespeichertTyp = Extract<FormularTyp, 'commentary' | 'generictext'>;

/** Die Saetze der Seite je Typ - der Kommentar, die Hintergrundinfo. */
const TEXTE: Record<GespeichertTyp, { gespeichert: string; nochEiner: string; nichtLadbar: string }> = {
  commentary: {
    gespeichert: 'Dein Kommentar ist gespeichert.',
    nochEiner: 'Noch einen Kommentar',
    nichtLadbar: 'Er lässt sich gerade nicht anzeigen – unter „Meine Beiträge“ findest du ihn.',
  },
  generictext: {
    gespeichert: 'Deine Hintergrundinfo ist gespeichert.',
    nochEiner: 'Noch eine Hintergrundinfo',
    nichtLadbar: 'Sie lässt sich gerade nicht anzeigen – unter „Meine Beiträge“ findest du sie.',
  },
};

export const NICHT_MARKIERT =
  'Der Einwurf konnte nicht als verarbeitet markiert werden – er steht im Fangkorb weiter unter „Ausformulieren“.';

/**
 * Die Seite nach dem Speichern eines Beitrags (<Formularpfad>/gespeichert/<id>),
 * fuer alle Wege ins Formular.
 *
 * Zeigt den gespeicherten Beitrag, worauf er antwortet, und den naechsten Schritt
 * passend zur Herkunft: aus dem Fangkorb der naechste Einwurf, aus der Suche
 * zurueck zur Anfrage, sonst noch einer. Typ aus den Routendaten, ID und Herkunft
 * aus der Adresse, der Rest aus dem Router-State (nach dem Neuladen weg - dann
 * eben ohne "Antwort auf").
 */
@Component({
  standalone: true,
  selector: 'app-beitrag-gespeichert',
  imports: [...SHARED_IMPORTS, CommonModule, RouterLink, BeitragskarteComponent],
  templateUrl: './beitrag-gespeichert.component.html',
  styleUrls: ['./beitrag-gespeichert.component.css'],
})
export class BeitragGespeichertComponent implements OnInit {
  private destroyRef = inject(DestroyRef);

  readonly nichtMarkiert = NICHT_MARKIERT;

  typ: GespeichertTyp = 'commentary';
  herkunft: Herkunft = 'frei';
  karte: KartenDaten | null = null;
  laedt = true;
  nichtLadbar = false;
  readonly zustand: GespeichertZustand;
  readonly aussageKopf: KartenDaten | null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private commentaryService: CommentaryService,
    private genericTextService: GenericTextService,
    private navigationService: NavigationService,
    private uebergabe: DestillierUebergabeService,
    private logger: LoggingService,
  ) {
    // Der State haengt an der laufenden Navigation; nach dem Neuladen gibt es keinen.
    this.zustand = (this.router.getCurrentNavigation()?.extras.state as GespeichertZustand | undefined) ?? {};
    const aussage = this.zustand.aussage;
    // Nicht verknuepft: keine "Antwort auf"-Karte - der Hinweis nennt die Aussage.
    this.aussageKopf =
      aussage?.text && this.zustand.verknuepft !== false ? ausAussage(aussage.id, aussage.text) : null;
  }

  /** Hinweis, wenn nicht verknuepft werden konnte - mit der Aussage im Text, sofern bekannt. */
  get verknuepfungFehlgeschlagen(): string {
    const text = this.zustand.aussage?.text;
    return text
      ? `Dein Beitrag ist gespeichert, konnte aber nicht mit „${text}“ verknüpft werden.`
      : VERKNUEPFUNG_FEHLGESCHLAGEN;
  }

  get texte() {
    return TEXTE[this.typ];
  }

  private get rohinputId(): string | null {
    return this.route.snapshot.queryParamMap.get(ROHINPUT_ADRESSE_PARAM);
  }

  /** Der Tab, in dem der Einwurf jetzt liegt. */
  private get fangkorbTab(): 'erledigt' | 'ausformulieren' {
    return this.zustand.markiert === false ? 'ausformulieren' : 'erledigt';
  }

  ngOnInit(): void {
    this.typ = this.route.snapshot.data['typ'] ?? 'commentary';
    this.herkunft = herkunftAus(this.route.snapshot.queryParamMap);
    this.route.paramMap
      .pipe(
        switchMap((params) => {
          this.laedt = true;
          this.nichtLadbar = false;
          return this.laden(params.get('id') ?? '');
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (karte) => {
          this.karte = karte;
          this.laedt = false;
        },
        error: (error) => {
          this.logger.warn('Gespeicherter Beitrag nicht ladbar', error);
          this.laedt = false;
          this.nichtLadbar = true;
        },
      });
  }

  /** Fangkorb: der naechste offene Einwurf; ist keiner offen, der Fangkorb. */
  naechsterEinwurf(): void {
    this.uebergabe.zumNaechsten(this.rohinputId ?? '', this.fangkorbTab);
  }

  zumFangkorb(): void {
    tabMerken(this.fangkorbTab);
    this.router.navigate(['/fangkorb']);
  }

  zurueckZurSuche(): void {
    const suche = this.route.snapshot.queryParamMap.get(SUCHE_PARAM);
    if (suche) {
      this.navigationService.navigateToResult(suche);
      return;
    }
    this.router.navigate(['/search']);
  }

  nochEiner(): void {
    this.router.navigate([FORMULAR_PFAD[this.typ]]);
  }

  private laden(id: string): Observable<KartenDaten> {
    if (this.typ === 'generictext') {
      return this.genericTextService
        .getGenericTextById(id)
        .pipe(map((inhalt) => ausSuchergebnis({ generictext_result: inhalt, score: 1 } as any)));
    }
    return this.commentaryService
      .getCommentaryById(id)
      .pipe(map((inhalt) => ausSuchergebnis({ commentary_result: inhalt, score: 1 } as any)));
  }
}
