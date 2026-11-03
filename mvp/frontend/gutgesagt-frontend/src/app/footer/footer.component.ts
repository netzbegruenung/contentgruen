import { Component } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { RouterModule } from '@angular/router';
import { hilfeOeffnen } from '../help-dialog/help-dialog.component';
// Default-Import: Der Karma-Builder (webpack) lehnt benannte Importe aus JSON ab.
import paket from '../../../package.json';
import { environment } from '../../environments/environment';

/**
 * Die Build-Kennung fuer den Footer, etwa "v1.1.0 · 3523b55".
 *
 * Die Version stammt beim Release-Build aus dem Git-Tag (Build-Arg APP_VERSION, #327),
 * sonst aus package.json; der Commit aus GIT_SHA. CI reicht beide als Build-Arg ins Image,
 * replace-env.sh setzt sie beim Containerstart ein. Fehlt der Commit oder steht noch der
 * Platzhalter da (ng serve, Build ohne Container), heisst er "dev".
 */
export function buildKennung(paketVersion: string, gitSha: string | undefined, appVersion?: string): string {
  const sha = gesetzt(gitSha) ? gitSha.slice(0, 7) : 'dev';
  const version = gesetzt(appVersion) ? appVersion.replace(/^v/, '') : paketVersion;
  return `v${version} · ${sha}`;
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
  // Ein lokales environment.ts ist nicht eingecheckt und kennt gitSha und appVersion womoeglich nicht.
  private readonly buildUmgebung = environment as { gitSha?: string; appVersion?: string };
  readonly buildKennung = buildKennung(paket.version, this.buildUmgebung.gitSha, this.buildUmgebung.appVersion);

  constructor(
    private dialog: MatDialog) {
  }
    openHelpDialog() {
      hilfeOeffnen(this.dialog);
    }
}
