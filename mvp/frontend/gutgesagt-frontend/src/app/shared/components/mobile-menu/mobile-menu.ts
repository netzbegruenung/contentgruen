import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs/operators';
import { UserInfo } from '../../../auth/auth.service';
import { OffeneMeldungenZahlComponent } from '../offene-meldungen-zahl/offene-meldungen-zahl.component';
import { DATENSCHUTZ_EINSTELLUNGEN, EINWERFEN_TITEL, MENUE_ICONS } from '../../fangkorb-texte';
import { ROUTES } from '../../constants/app.constants';
import { RundgangId, rundgangBeschriftung } from '../../../rundgang/rundgang-daten';
import { MITMACHEN_HINWEIS, anmeldenZurHilfe } from '../../../help-dialog/help-dialog.component';

@Component({
  selector: 'app-mobile-menu',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    RouterLink,
    OffeneMeldungenZahlComponent
  ],
  templateUrl: './mobile-menu.html',
  styleUrl: './mobile-menu.css'
})
export class MobileMenuComponent {
  readonly menueIcons = MENUE_ICONS;
  readonly datenschutzEinstellungen = DATENSCHUTZ_EINSTELLUNGEN;
  readonly pfade = ROUTES;
  readonly antwortFinden = rundgangBeschriftung('antwort-finden');
  readonly selbstBeitragen = rundgangBeschriftung('mitmachen');
  readonly mitmachenHinweis = MITMACHEN_HINWEIS;
  readonly hierFehltEineAntwortPfad = ROUTES.HIER_FEHLT_EINE_ANTWORT;
  readonly einwerfenTitel = EINWERFEN_TITEL;
  @Input() userInfo: UserInfo | null = null;
  @Input() selectedProfilePictureUrl: string = '';

  @Output() closeMenu = new EventEmitter<void>();
  @Output() home = new EventEmitter<void>();
  @Output() contribute = new EventEmitter<void>();
  @Output() meineBeitraege = new EventEmitter<void>();
  @Output() einwerfen = new EventEmitter<void>();
  @Output() fangkorb = new EventEmitter<void>();
  @Output() login = new EventEmitter<void>();
  @Output() loginToContribute = new EventEmitter<void>();
  @Output() logout = new EventEmitter<void>();
  @Output() profilbild = new EventEmitter<void>();
  @Output() help = new EventEmitter<void>();
  @Output() feedback = new EventEmitter<void>();
  @Output() rundgang = new EventEmitter<RundgangId>();

  private readonly router = inject(Router);
  /** Pfad der aktuellen Seite ohne Query und Fragment, fuer die Hervorhebung (#644). */
  private pfad = this.ohneQuery(this.router.url);

  constructor() {
    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd), takeUntilDestroyed())
      .subscribe((e) => (this.pfad = this.ohneQuery(e.urlAfterRedirects)));
  }

  /** Ist das die Seite, auf der man gerade ist? Unterseiten zaehlen mit. */
  aktiv(ziel: string): boolean {
    return this.pfad === ziel || this.pfad.startsWith(ziel + '/');
  }

  private ohneQuery(url: string): string {
    return url.split(/[?#]/)[0];
  }

  close(): void {
    this.closeMenu.emit();
  }

  onHomeClick(): void {
    this.home.emit();
    this.close();
  }

  onContributeClick(): void {
    this.contribute.emit();
    this.close();
  }

  onMeineBeitraegeClick(): void {
    this.meineBeitraege.emit();
    this.close();
  }

  onEinwerfenClick(): void {
    this.einwerfen.emit();
    this.close();
  }

  onFangkorbClick(): void {
    this.fangkorb.emit();
    this.close();
  }

  onLoginClick(): void {
    this.login.emit();
    this.close();
  }

  onLoginToContributeClick(): void {
    this.loginToContribute.emit();
    this.close();
  }

  onLogoutClick(): void {
    this.logout.emit();
    this.close();
  }

  onProfilbildClick(): void {
    this.profilbild.emit();
    this.close();
  }

  onHelpClick(): void {
    this.help.emit();
    this.close();
  }

  onRundgangClick(id: RundgangId): void {
    this.rundgang.emit(id);
    this.close();
  }

  /** Besucher: anmelden, danach öffnet die App die Hilfe mit Selbst beitragen. */
  onAnmeldenZurHilfeClick(): void {
    this.close();
    anmeldenZurHilfe(this.router);
  }

  onFeedbackClick(): void {
    this.feedback.emit();
    this.close();
  }
}
