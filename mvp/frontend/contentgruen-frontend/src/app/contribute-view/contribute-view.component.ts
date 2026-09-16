import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { typLabel } from '../shared/content-type-registry';
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
  readonly fangkorbKurz = FANGKORB_KURZ;
  readonly kettenIcons = KETTEN_ICONS;
  /** Die Route verlangt eine Anmeldung, der Satz braucht deshalb keine eigene Pruefung. */
  readonly erstnutzerSatz = ERSTNUTZER_SATZ;

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
    const params = this.route.snapshot.queryParamMap;
    const typ = [params.get('form'), params.get('panel')].find(istFormularTyp);
    if (typ) {
      this.router.navigate([FORMULAR_PFAD[typ]], {
        queryParams: aussageParameter(null, params.get(SUCHTEXT_PARAM)),
        replaceUrl: true,
      });
    }
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

  formularOeffnen(typ: FormularTyp): void {
    this.router.navigate([FORMULAR_PFAD[typ]]);
  }
}
