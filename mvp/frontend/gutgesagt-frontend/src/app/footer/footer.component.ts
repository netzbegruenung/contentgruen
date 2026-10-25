import { Component } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { RouterModule } from '@angular/router';
import { HelpDialogComponent } from '../help-dialog/help-dialog.component';
// Default-Import: Der Karma-Builder (webpack) lehnt benannte Importe aus JSON ab.
import paket from '../../../package.json';
import { environment } from '../../environments/environment';

/**
 * Die Build-Kennung fuer den Footer, etwa "v1.1.0 · 3523b55".
 *
 * Die Version stammt aus package.json, der Commit aus GIT_SHA: CI reicht ihn als
 * Build-Arg ins Image, replace-env.sh setzt ihn beim Containerstart ein. Fehlt er
 * oder steht noch der Platzhalter da (ng serve, Build ohne Container), heisst er "dev".
 */
export function buildKennung(paketVersion: string, gitSha: string | undefined): string {
  const sha = gitSha && !gitSha.startsWith('${') ? gitSha.slice(0, 7) : 'dev';
  return `v${paketVersion} · ${sha}`;
}

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterModule],
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.css']
})
export class FooterComponent {
  // Ein lokales environment.ts ist nicht eingecheckt und kennt gitSha womoeglich nicht.
  readonly buildKennung = buildKennung(paket.version, (environment as { gitSha?: string }).gitSha);

  constructor(
    private dialog: MatDialog) {
  }
    openHelpDialog() {
      this.dialog.open(HelpDialogComponent, {
        width: '80vw',
        maxWidth: '80vw',
        data: {} // Pass any data you need here
      });
    }
}
