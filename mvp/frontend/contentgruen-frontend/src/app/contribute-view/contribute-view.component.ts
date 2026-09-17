import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { typBeschreibung, typLabel } from '../shared/content-type-registry';
import { ERSTNUTZER_SATZ, FANGKORB_KURZ, KETTEN_ICONS } from '../shared/fangkorb-texte';
import { FORMULAR_PFAD, FormularTyp, SUCHTEXT_PARAM, aussageParameter, istFormularTyp } from '../shared/formular-adresse';

/**
 * Die Beitragen-Seite: nur Uebersicht, auf Desktop und Handy gleich - die Kette
 * Einwerfen, Weiterarbeiten, Verfassen. Die Formulare sind eigene Seiten unter
 * /workflow/add-*; hier wird keins eingebettet.
 */
@Component({
  selector: 'app-contribute-view',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
  ],
  templateUrl: './contribute-view.component.html',
  styleUrls: ['./contribute-view.component.css']
})
export class ContributeViewComponent implements OnInit {
  readonly typLabel = typLabel;
  readonly typBeschreibung = typBeschreibung;
  readonly fangkorbKurz = FANGKORB_KURZ;
  readonly kettenIcons = KETTEN_ICONS;
  /** Die Route verlangt eine Anmeldung, der Satz braucht deshalb keine eigene Pruefung. */
  readonly erstnutzerSatz = ERSTNUTZER_SATZ;
  private destroyRef = inject(DestroyRef);

  constructor(
    private router: Router,
    private route: ActivatedRoute,
  ) {}

  /**
   * Alte Adressen: ``?form=<typ>`` (Formular am Handy) und ``?panel=<typ>``
   * (Akkordeon am Desktop, Ziel der Suche) fuehren jetzt direkt ins Formular.
   * replaceUrl, damit das Zurueck nicht wieder hier landet und weiterleitet.
   */
  ngOnInit(): void {
    // Reaktiv: auch ein spaeterer Aufruf von /contribute?form=... auf der schon
    // offenen Seite wird weitergeleitet, nicht nur der erste.
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const typ = [params.get('form'), params.get('panel')].find(istFormularTyp);
        if (typ) {
          this.router.navigate([FORMULAR_PFAD[typ]], {
            queryParams: aussageParameter(null, params.get(SUCHTEXT_PARAM)),
            replaceUrl: true,
          });
        }
      });
  }

  /**
   * Der Fangkorb ist kein vierter Beitragstyp, sondern der Weg daran vorbei:
   * er fuehrt aus dieser Auswahl heraus statt in ein weiteres Formular.
   */
  navigateToRawInput(): void {
    this.router.navigate(['/einwerfen']);
  }

  /** Weiterarbeiten: zur Liste, in der Einwuerfe destilliert und Saetze ausformuliert werden. */
  navigateToRawInputList(): void {
    this.router.navigate(['/fangkorb']);
  }

  /** Weiterarbeiten: die eigenen Beitraege - frueher das Ordner-Icon in der Kopfzeile. */
  navigateToContributions(): void {
    this.router.navigate(['/contributions']);
  }

  formularOeffnen(typ: FormularTyp): void {
    this.router.navigate([FORMULAR_PFAD[typ]]);
  }
}
