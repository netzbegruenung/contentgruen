import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { BehaviorSubject, Subject } from 'rxjs';
import { DestroyRef } from '@angular/core';
import { DefaultUrlSerializer, NavigationEnd, Router, provideRouter } from '@angular/router';
import { AuthService, UserInfo } from '../auth/auth.service';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { RundgangService } from '../rundgang/rundgang.service';
import { KEINE_GENERATIVE_KI, SUCHE_MIT_SPRACHMODELLEN } from '../shared/ki-saetze';
import { FeedbackDialogComponent } from '../shared/feedback/feedback-dialog.component';

import { HILFE_PARAM, HelpDialogComponent, hilfeNachAnmeldung, hilfeOeffnen } from './help-dialog.component';
import { EINLADUNG_AB } from '../shared/einladung-ab';

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
        // Router fuer die Links auf die Über-Seite (href plus zuUeber)
        provideRouter([]),
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

  // Rundgang wieder aufrufen (#389): gelber Kasten mit Wegweiser ganz oben
  describe('Rundgang', () => {
    it('steht als Kasten mit Wegweiser am Anfang des Inhalts', () => {
      const kasten = fixture.nativeElement.querySelector('mat-dialog-content > .rundgang-kasten') as HTMLElement;
      expect(kasten).not.toBeNull();
      expect(kasten.querySelector('img')!.getAttribute('src')).toBe('marke/wegweiser.svg');
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

    it('bietet Besuchern Selbst beitragen als Bildergeschichte an, ohne Sperre (17.11.)', () => {
      const knopf = fixture.nativeElement.querySelector('.rundgang-mitmachen') as HTMLButtonElement;
      expect(knopf.textContent!.trim()).toBe('Selbst beitragen (3 Bilder)');
      expect(knopf.hasAttribute('aria-disabled')).toBeFalse();
      knopf.click();

      expect(TestBed.inject(MatDialogRef).close).toHaveBeenCalled();
      // Wohin es geht, entscheidet der Rundgang: ohne Konto auf /mit-konto
      expect(rundgang.starten).toHaveBeenCalledWith('mitmachen');
      expect(fixture.nativeElement.querySelector('.rundgang-mitmachen-hinweis')).toBeNull();
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

  // UX-Review B10: die Kette, Begriffe nach GLOSSARY, kein Jargon, organisationsneutral
  it('erklärt die Kette Einwerfen, Destillieren, Ausformulieren in drei Zeilen', () => {
    const schritte = Array.from(fixture.nativeElement.querySelectorAll('.hilfe-kette li')) as HTMLElement[];
    expect(schritte.map((s) => s.querySelector('strong')!.textContent)).toEqual([
      'Einwerfen:',
      'Destillieren:',
      'Ausformulieren:',
    ]);
    expect(schritte[0].textContent).toContain('Fangkorb');
  });

  it('nennt Begriffe nach GLOSSARY, ohne Jargon und ohne Widerspruch zu den eigenen Modellen', () => {
    const inhalt: string = fixture.nativeElement.querySelector('mat-dialog-content').textContent;
    expect(inhalt).not.toContain('fertige Kommentare');
    expect(inhalt).not.toContain('grünen Mitglied');
    expect(inhalt).not.toContain('Vektordatenbank');
    expect(inhalt).not.toContain('semantisch');
    expect(inhalt).not.toContain('selbst aber keine KI');
    const technik = Array.from(fixture.nativeElement.querySelectorAll('.hilfe-technik'))
      .map((p) => (p as HTMLElement).textContent)
      .join(' ');
    expect(technik).toContain('auf unseren eigenen Servern');
    expect(technik).not.toContain('keine KI.');
  });

  // Designrunde 17.11.: die Hilfe sagt, wie man es jetzt nutzt; warum und wer steht auf der Über-Seite
  it('ordnet die Hilfe nach dem, was man zuerst braucht', () => {
    const ueberschriften = Array.from(fixture.nativeElement.querySelectorAll('mat-dialog-content h3'))
      .map((h) => (h as HTMLElement).textContent!.trim());
    expect(ueberschriften).toEqual([
      'Lieber zeigen lassen?',
      'Suchen und Kopieren',
      'Bewerten und Siegel',
      'Beitragen',
      'Konto und Anmeldung',
      'Nutzt Gut gesagt KI?',
      'Feedback',
      'Häufige Fragen',
    ]);
  });

  it('nennt die Fassungen Kurz, Mittel, Lang und den Hinweis „passt auf X/Bluesky“', () => {
    const text = (fixture.nativeElement.querySelector('.hilfe-fassungen') as HTMLElement).textContent!;
    expect(text).toContain('Kurz, Mittel und Lang');
    expect(text).toContain('„passt auf X/Bluesky“');
  });

  // Persona-Test Gerd: die Antwort auf „Nutzt Gut gesagt KI?“ bleibt, kurz, mit den Sätzen der Über-Seite
  it('beantwortet „Nutzt Gut gesagt KI?“ kurz mit den Sätzen der Über-Seite und verlinkt die Technik', () => {
    const ki = fixture.nativeElement.querySelector('.hilfe-ki') as HTMLElement;
    expect(ki.textContent).toContain(KEINE_GENERATIVE_KI);
    expect(ki.textContent).toContain(SUCHE_MIT_SPRACHMODELLEN);
    expect(ki.querySelector('a')!.getAttribute('href')).toBe('/about#technik');
    // Wie die Suche technisch arbeitet, steht jetzt unter /about#technik
    expect(fixture.nativeElement.textContent).not.toContain('Je mehr Mitwirkende beitragen und bewerten');
  });

  describe('Links auf die Über-Seite', () => {
    function link(selektor: string): HTMLAnchorElement {
      return fixture.nativeElement.querySelector(selektor) as HTMLAnchorElement;
    }

    it('verlinkt „Was bedeutet das Siegel?“ auf /about#siegel, schliesst die Hilfe und navigiert danach', () => {
      const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
      const siegel = link('.hilfe-siegel-link');
      expect(siegel.textContent!.trim()).toBe('Was bedeutet das Siegel?');
      expect(siegel.getAttribute('href')).toBe('/about#siegel');
      siegel.click();

      expect(TestBed.inject(MatDialogRef).close).toHaveBeenCalled();
      expect(navigate).toHaveBeenCalledWith(['/about'], { fragment: 'siegel' });
    });

    it('macht dasselbe bei „Mehr zur Technik“ und „Über Gut gesagt“', () => {
      const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
      const technik = link('.hilfe-technik-link');
      expect(technik.getAttribute('href')).toBe('/about#technik');
      technik.click();
      expect(navigate).toHaveBeenCalledWith(['/about'], { fragment: 'technik' });

      const ueber = link('.about-link-section a');
      expect(ueber.getAttribute('href')).toBe('/about');
      ueber.click();
      expect(navigate).toHaveBeenCalledWith(['/about'], { fragment: undefined });
      expect(TestBed.inject(MatDialogRef).close).toHaveBeenCalledTimes(2);
    });

    it('lässt Strg-Klick dem Browser (neuer Tab), ohne die Hilfe zu schliessen', () => {
      const navigate = spyOn(TestBed.inject(Router), 'navigate');
      const ziel = link('.hilfe-siegel-link');
      // Nach dem Handler der Komponente pruefen, ob sie den Klick dem Browser liess, und ihn
      // dann selbst abfangen: Sonst oeffnet Chrome wirklich einen Tab, der Testtab liegt
      // im Hintergrund, und Tests mit Sichtbarkeit, Fokus und requestAnimationFrame scheitern.
      let vonKomponenteVerhindert: boolean | undefined;
      ziel.addEventListener('click', (e) => {
        vonKomponenteVerhindert = e.defaultPrevented;
        e.preventDefault();
      }, { once: true });
      ziel.dispatchEvent(new MouseEvent('click', { ctrlKey: true, cancelable: true }));
      expect(vonKomponenteVerhindert).toBeFalse();
      expect(navigate).not.toHaveBeenCalled();
      expect(TestBed.inject(MatDialogRef).close).not.toHaveBeenCalled();
    });
  });

  it('sagt, wie man zu einem Konto kommt: Netzbegrünung-Konto, Einladung ab 4. Dezember, Warteliste', () => {
    const text = (fixture.nativeElement.querySelector('.hilfe-konto') as HTMLElement).textContent!;
    expect(text).toContain('Netzbegrünung-Konto');
    expect(text).toContain(`Ab ${EINLADUNG_AB}`);
    expect(text).toContain('Warteliste');
    expect(text).toContain('„Feedback“');
  });

  it('öffnet Feedback aus der Hilfe heraus', () => {
    // MatDialogModule im Komponenten-Import stellt einen eigenen MatDialog bereit
    const open = spyOn(fixture.debugElement.injector.get(MatDialog), 'open');
    (fixture.nativeElement.querySelector('.hilfe-feedback-knopf') as HTMLButtonElement).click();

    expect(open).toHaveBeenCalledWith(FeedbackDialogComponent, jasmine.anything());
  });

  it('hält die häufigen Fragen kurz: höchstens vier', () => {
    const fragen = fixture.nativeElement.querySelectorAll('.hilfe-fragen dt');
    expect(fragen.length).toBeGreaterThan(0);
    expect(fragen.length).toBeLessThanOrEqual(4);
    expect(fixture.nativeElement.querySelectorAll('.hilfe-fragen dd').length).toBe(fragen.length);
  });

  it('erklärt die Kette nur einmal, unter „Beitragen“', () => {
    expect(fixture.nativeElement.querySelectorAll('.hilfe-kette').length).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('.nicht-jede-aussage').length).toBe(1);
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

// Nach der Anmeldung aus Hilfe oder Menü (Parameter HILFE_PARAM) öffnet die App die Hilfe wieder
describe('hilfeNachAnmeldung', () => {
  let events: Subject<unknown>;
  let userInfo: BehaviorSubject<UserInfo | null>;
  let geklaert: BehaviorSubject<string | null>;
  let navigate: jasmine.Spy;
  let dialog: { open: jasmine.Spy; openDialogs: MatDialogRef<unknown>[] };
  let hooks: Array<() => void>;

  const angemeldet: UserInfo = { isAuthenticated: true, userId: 'u1', userName: 'Test', claims: null };
  const besucher: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };

  beforeEach(() => {
    events = new Subject();
    userInfo = new BehaviorSubject<UserInfo | null>(null);
    geklaert = new BehaviorSubject<string | null>(null);
    dialog = { open: jasmine.createSpy('open'), openDialogs: [] };
    dialog.open.and.callFake(() => {
      const ref = { componentInstance: Object.create(HelpDialogComponent.prototype) } as MatDialogRef<unknown>;
      dialog.openDialogs.push(ref);
      return ref;
    });
    navigate = jasmine.createSpy('navigate').and.resolveTo(true);
    const serializer = new DefaultUrlSerializer();
    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: { events, navigate, parseUrl: (u: string) => serializer.parse(u) } },
        { provide: MatDialog, useValue: dialog },
        { provide: AuthService, useValue: { userInfo$: userInfo } },
        { provide: Art9EinwilligungService, useValue: { geklaert$: geklaert } },
      ],
    });
    hooks = [];
    const destroyRef = { onDestroy: (h: () => void) => hooks.push(h) } as unknown as DestroyRef;
    TestBed.runInInjectionContext(() => hilfeNachAnmeldung(destroyRef));
  });

  afterEach(() => hooks.forEach((h) => h()));

  function navigiert(url: string): void {
    events.next(new NavigationEnd(1, url, url));
  }

  it('öffnet nicht vor der Einwilligung, danach schon, und nimmt den Parameter aus der Adresse', () => {
    navigiert(`/search?${HILFE_PARAM}=1`);
    userInfo.next(angemeldet);
    expect(dialog.open).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();

    geklaert.next('u1');
    expect(dialog.open).toHaveBeenCalledTimes(1);
    expect(navigate).toHaveBeenCalledWith([], {
      queryParams: { [HILFE_PARAM]: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  });

  it('öffnet keinen zweiten Dialog, wenn erneut etwas kommt', () => {
    navigiert(`/search?${HILFE_PARAM}=1`);
    userInfo.next(angemeldet);
    geklaert.next('u1');
    userInfo.next({ ...angemeldet });
    expect(dialog.open).toHaveBeenCalledTimes(1);
  });

  it('öffnet ohne Parameter nicht', () => {
    navigiert('/search');
    userInfo.next(angemeldet);
    geklaert.next('u1');
    expect(dialog.open).not.toHaveBeenCalled();
  });

  it('öffnet für Besucher, sobald feststeht, dass niemand angemeldet ist', () => {
    navigiert(`/search?${HILFE_PARAM}=1`);
    expect(dialog.open).not.toHaveBeenCalled();
    userInfo.next(besucher);
    expect(dialog.open).toHaveBeenCalledTimes(1);
  });

  it('ohne Einwilligung weiter: Die Einwilligungsseite streicht den Parameter, die Hilfe bleibt zu', () => {
    // Ohne Einwilligung ist geklaert$ null; einwilligung.component nimmt HILFE_PARAM aus dem
    // Rückkehrziel (eigener Test dort), danach kommt die Seite ohne Parameter an
    userInfo.next(angemeldet);
    navigiert(`/einwilligung?returnUrl=%2Fsearch%3F${HILFE_PARAM}%3D1`);
    navigiert('/search');
    expect(dialog.open).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });
});
