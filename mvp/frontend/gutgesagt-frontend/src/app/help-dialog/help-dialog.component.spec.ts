import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { Subject } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { RundgangService } from '../rundgang/rundgang.service';

import { Router } from '@angular/router';
import { HILFE_PARAM, HelpDialogComponent, MITMACHEN_HINWEIS, hilfeOeffnen } from './help-dialog.component';

describe('HelpDialogComponent', () => {
  let component: HelpDialogComponent;
  let fixture: ComponentFixture<HelpDialogComponent>;
  let geschlossen: Subject<void>;
  let rundgang: jasmine.SpyObj<RundgangService>;
  let angemeldet: boolean;

  beforeEach(async () => {
    geschlossen = new Subject<void>();
    rundgang = jasmine.createSpyObj<RundgangService>('RundgangService', ['starten']);
    angemeldet = false;
    await TestBed.configureTestingModule({
      imports: [HelpDialogComponent, HttpClientTestingModule],
      providers: [
        {
          provide: MatDialogRef,
          useValue: {
            close: jasmine.createSpy('close').and.callFake(() => geschlossen.next()),
            afterClosed: () => geschlossen,
          }
        },
        { provide: RundgangService, useValue: rundgang },
        { provide: AuthService, useValue: { getUserInfo: () => ({ isAuthenticated: angemeldet }) } },
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HelpDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Design-Audit A7 und Hilfe-Umbau (#512): mobil oeffnete die Hilfe ans Ende
  // gescrollt (Fokus auf dem ersten Link). Jetzt eine Seitenleiste rechts, volle
  // Hoehe, auf dem Handy Vollbild, Fokus auf dem Dialog selbst.
  describe('als Seitenleiste', () => {
    it('oeffnet rechts, volle Hoehe, 560 px breit, auf dem Handy ganze Breite, oben', () => {
      const dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);

      hilfeOeffnen(dialog);

      expect(dialog.open).toHaveBeenCalledWith(
        HelpDialogComponent,
        jasmine.objectContaining({
          autoFocus: 'dialog',
          position: { top: '0', right: '0' },
          width: '560px',
          maxWidth: '100vw',
          height: '100%',
          maxHeight: '100%',
          panelClass: 'hilfe-seitenleiste',
        }),
      );
    });

    it('hat einen festen Kopf mit Titel und Schliessen, nur der Inhalt scrollt', () => {
      const kopf: HTMLElement = fixture.nativeElement.querySelector('.hilfe-kopf');

      expect(kopf.querySelector('h2')!.textContent!.trim()).toBe('Hilfe zur Nutzung');
      expect(kopf.querySelector('button[mat-dialog-close]')!.textContent!.trim()).toBe('Schließen');
      expect(fixture.nativeElement.querySelector('mat-dialog-actions')).toBeNull();
      const inhalt = fixture.nativeElement.querySelector('mat-dialog-content') as HTMLElement;
      expect(getComputedStyle(inhalt).maxHeight).toBe('none');
      expect(getComputedStyle(inhalt).overflowY).toBe('auto');
    });
  });

  // Rundgang wieder aufrufen (#389): gelber Kasten mit Daumen ganz oben
  describe('Rundgang', () => {
    it('steht als Kasten mit Daumen am Anfang des Inhalts', () => {
      const kasten = fixture.nativeElement.querySelector('mat-dialog-content > .rundgang-kasten') as HTMLElement;
      expect(kasten).not.toBeNull();
      expect(kasten.querySelector('img')!.getAttribute('src')).toBe('marke/daumen.svg');
      expect(kasten.querySelector('img')!.getAttribute('alt')).toBe('');
      expect(kasten.querySelector('h3')!.textContent).toContain('Lieber zeigen lassen?');
    });

    it('schliesst erst die Hilfe und startet dann den Rundgang Antwort finden', () => {
      const ref = TestBed.inject(MatDialogRef);
      const knopf = fixture.nativeElement.querySelector('.rundgang-starten') as HTMLButtonElement;
      expect(knopf.textContent!.trim()).toBe('Antwort finden (5 Schritte)');
      knopf.click();

      expect(ref.close).toHaveBeenCalled();
      expect(rundgang.starten).toHaveBeenCalledWith('antwort-finden');
    });

    it('teasert Besuchern Selbst beitragen an: aria-disabled, ohne Wirkung, mit Hinweis', () => {
      const knopf = fixture.nativeElement.querySelector('.rundgang-mitmachen') as HTMLButtonElement;
      expect(knopf.textContent!.trim()).toBe('Selbst beitragen (4 Schritte)');
      expect(knopf.getAttribute('aria-disabled')).toBe('true');
      expect(knopf.disabled).toBeFalse(); // fokussierbar, der Screenreader liest den Hinweis
      const hinweis = fixture.nativeElement.querySelector('#' + knopf.getAttribute('aria-describedby')) as HTMLElement;
      expect(hinweis.textContent).toContain(MITMACHEN_HINWEIS);
      knopf.click();
      expect(rundgang.starten).not.toHaveBeenCalled();
    });

    it('führt Besucher zur Anmeldung und danach zurück in die Hilfe', () => {
      const router = TestBed.inject(Router);
      spyOnProperty(router, 'url').and.returnValue('/result?searchQuery=x');
      const navigate = spyOn(router, 'navigate').and.resolveTo(true);
      (fixture.nativeElement.querySelector('.rundgang-anmelden') as HTMLButtonElement).click();

      expect(TestBed.inject(MatDialogRef).close).toHaveBeenCalled();
      expect(navigate).toHaveBeenCalledWith(['/login'], {
        queryParams: { returnUrl: `/result?searchQuery=x&${HILFE_PARAM}=1` },
      });
    });

    it('bietet Angemeldeten auch den Rundgang Selbst beitragen an, mit Schrittzahl (#644)', () => {
      angemeldet = true;
      fixture = TestBed.createComponent(HelpDialogComponent);
      fixture.detectChanges();

      const knopf = fixture.nativeElement.querySelector('.rundgang-mitmachen') as HTMLButtonElement;
      expect(knopf.textContent!.trim()).toBe('Selbst beitragen (4 Schritte)');
      knopf.click();

      expect(rundgang.starten).toHaveBeenCalledWith('mitmachen');
      expect(knopf.hasAttribute('aria-disabled')).toBeFalse();
      expect(fixture.nativeElement.querySelector('.rundgang-mitmachen-hinweis')).toBeNull();
    });
  });

  // R60 (#644): Einstieg ohne Versalien und ohne Fachbegriffe wie "Datenbank"
  it('beginnt mit Menschen statt mit "KEIN KI-Generator" und erklaert die Suche ohne Fachbegriffe', () => {
    const inhalt: string = fixture.nativeElement.querySelector('mat-dialog-content').textContent;
    expect(fixture.nativeElement.querySelector('.hilfe-einstieg').textContent).toContain(
      'Alles hier haben Menschen geschrieben und erprobt.',
    );
    expect(fixture.nativeElement.querySelector('.hilfe-suche').textContent).toContain(
      'Gib ein, was du gelesen hast – du bekommst Antworten darauf, keine ähnlichen Texte',
    );
    expect(inhalt).not.toContain('KEIN');
    expect(inhalt).not.toContain('Aussage-Antwort Zuordnung');
    expect(inhalt).not.toContain('in der Datenbank, indem');
  });

  it('nennt die sechs Schreibregeln', () => {
    const regeln = fixture.nativeElement.querySelectorAll('.schreibregeln li');

    expect(regeln.length).toBe(6);
    expect(regeln[0].textContent).toContain('Unentschiedenen');
    expect(regeln[4].textContent).toContain('Erfinde nichts');
  });

  it('sagt, dass nicht jede Aussage eine Antwort braucht', () => {
    expect(fixture.nativeElement.querySelector('.nicht-jede-aussage').textContent).toContain(
      'Nicht jede Aussage braucht eine Antwort',
    );
  });

  it('nennt erfundene Erlebnisse oder Zahlen als Grund zu melden', () => {
    expect(fixture.nativeElement.querySelector('.erfundenes-melden').textContent).toContain(
      'Erfundene Erlebnisse oder Zahlen',
    );
  });

  it('verweist auf den Meldegrund „Erfunden oder sachlich falsch“', () => {
    expect(fixture.nativeElement.querySelector('.erfundenes-melden').textContent).toContain(
      '„Erfunden oder sachlich falsch“',
    );
  });
});
