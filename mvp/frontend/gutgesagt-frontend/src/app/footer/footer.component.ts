import { DOCUMENT } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { RouterModule } from '@angular/router';
import { hilfeOeffnen } from '../help-dialog/help-dialog.component';
// Default-Import: Der Karma-Builder (webpack) lehnt benannte Importe aus JSON ab.
import paket from '../../../package.json';

/**
 * Die Build-Kennung fuer den Footer, etwa "v1.1.0 · 3523b55".
 *
 * Die Version stammt beim Release-Build aus dem Git-Tag (Build-Arg APP_VERSION, #327); Builds
 * auf main geben APP_VERSION=main mit und zeigen "main · <sha>" (#542). Ohne APP_VERSION
 * gilt package.json; der Commit aus GIT_SHA. CI reicht beide als Build-Arg ins Image,
 * replace-env.sh setzt sie beim Containerstart in die meta-Tags von index.html ein
 * (buildWerteAusSeite). Fehlt der Commit oder steht noch der Platzhalter da (ng serve,
 * Build ohne Container), heisst er "dev".
 */
export function buildKennung(paketVersion: string, gitSha: string | undefined, appVersion?: string): string {
  const sha = gesetzt(gitSha) ? gitSha.slice(0, 7) : 'dev';
  if (appVersion === 'main') {
    return `main · ${sha}`;
  }
  const version = gesetzt(appVersion) ? appVersion.replace(/^v/, '') : paketVersion;
  return `v${version} · ${sha}`;
}

/**
 * Commit und Version aus den meta-Tags in index.html. Sie stehen dort und nicht in den
 * *.js-Dateien, weil nginx diese ein Jahr cachen laesst und ihr Name vor der Ersetzung
 * entsteht: Der Footer zeigte sonst den Commit eines alten Builds. index.html kommt ohne Cache.
 */
export function buildWerteAusSeite(seite: Document): { gitSha?: string; appVersion?: string } {
  // name kommt nur aus den beiden Konstanten unten, nie von aussen: kein Escaping im Selektor noetig.
  const inhalt = (name: string) => seite.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)?.content;
  return { gitSha: inhalt('gutgesagt-commit'), appVersion: inhalt('gutgesagt-version') };
}

/** Ein Wert aus replace-env.sh, der wirklich ersetzt wurde. */
function gesetzt(wert: string | undefined): wert is string {
  return !!wert && !wert.startsWith('${');
}

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterModule],
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.css']
})
export class FooterComponent {
  private readonly buildWerte = buildWerteAusSeite(inject(DOCUMENT));
  readonly buildKennung = buildKennung(paket.version, this.buildWerte.gitSha, this.buildWerte.appVersion);

  constructor(
    private dialog: MatDialog) {
  }
    openHelpDialog() {
      hilfeOeffnen(this.dialog);
    }
}
