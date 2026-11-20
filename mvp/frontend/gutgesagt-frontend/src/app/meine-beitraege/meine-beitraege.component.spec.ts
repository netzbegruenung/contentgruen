import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Observable, of, throwError } from 'rxjs';

import { MeineBeitraegeComponent } from './meine-beitraege.component';
import { AlbumComponent } from './album/album.component';
import { MeineBeitraegeService } from '../services/meine-beitraege.service';
import { Meilenstein, UsageTrackingService } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { BeitragVerwaltenService } from '../beitragskarte/beitrag-verwalten.service';
import { EinwurfService } from '../services/einwurf.service';
import { SperrnachrichtService } from '../services/sperrnachricht.service';
import { NavigationService } from '../services/navigation.service';
import { StatementService } from '../services/statement.service';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatSnackBar } from '@angular/material/snack-bar';
import { VotingService } from '../services/voting.service';
import { LoggingService } from '../services/logging.service';
import { PUNKTE_EINWILLIGUNG_AUS } from '../shared/punkte-einwilligung/punkte-einwilligung.testing';

describe('MeineBeitraegeComponent', () => {
  let fixture: ComponentFixture<MeineBeitraegeComponent>;
  let router: Router;
  let eigeneLaden: jasmine.Spy;
  let alleLaden: jasmine.Spy;
  let meilensteine: Meilenstein[];
  let verwalten: jasmine.SpyObj<BeitragVerwaltenService>;
  /** Was "Hier fehlt eine Antwort" liefert; Standard: keine. */
  let unbeantworteteLaden: jasmine.Spy;

  beforeEach(() => {
    unbeantworteteLaden = jasmine.createSpy('unbeantworteteAussagen').and.returnValue(of([]));
    meilensteine = [];
    verwalten = jasmine.createSpyObj('BeitragVerwaltenService', ['aendern', 'loeschen']);
  });

  function beitrag(felder: Record<string, unknown> = {}): any {
    return {
      id: 'b1',
      created: '2026-09-13T21:05:00',
      // Wie der Server ihn liefert: ohne Kennung, mit Kennzeichen (#385).
      original_author: null,
      ist_eigener_beitrag: true,
      text: 'Text der Hintergrundinfo',
      content_type: 'generic_text',
      title: 'Wärmepumpe lohnt sich auch im Altbau',
      usage_count: 12,
      score: 0,
      ...felder,
    };
  }

  function meilenstein(felder: Partial<Meilenstein>): Meilenstein {
    return {
      kennung: 'm',
      name: 'Meilenstein',
      untertitel: '',
      beschreibung: '',
      bild: 'meilensteine/vogel.svg',
      bildnachweis: '',
      art: 'wirkung',
      schwelle: 1,
      stand: 0,
      erreicht: false,
      ...felder,
    };
  }

  function konfigurieren(laden: () => Observable<any>): void {
    eigeneLaden = jasmine
      .createSpy('eigeneLaden')
      .and.returnValue(of({ results_count: 0, results: [], total_records_count: 0 }));
    alleLaden = jasmine.createSpy('alleMeineBeitraege').and.callFake(laden);
    TestBed.configureTestingModule({
      imports: [MeineBeitraegeComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        PUNKTE_EINWILLIGUNG_AUS,
        { provide: BreakpointObserver, useValue: { observe: () => of({ matches: false, breakpoints: {} }) } },
        { provide: MeineBeitraegeService, useValue: { alleMeineBeitraege: alleLaden } },
        {
          provide: UsageTrackingService,
          useValue: {
            getEigeneMeilensteine: () => of(meilensteine),
            getEigenePunkte: () => of(null),
            getAbzeichenSichtbarkeit: () => of(null),
            trackContentUsage: () => undefined,
            gepostetBekannt: () => false,
          },
        },
        { provide: BeitragVerwaltenService, useValue: verwalten },
        // Die vollen Karten im Album bringen ihre Aktionsleiste mit.
        { provide: VotingService, useValue: jasmine.createSpyObj('VotingService', ['setLike']) },
        { provide: Clipboard, useValue: jasmine.createSpyObj('Clipboard', ['copy']) },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj('MatSnackBar', ['open']) },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error', 'debug', 'info', 'warn']) },
        { provide: EinwurfService, useValue: { eigeneLaden } },
        { provide: SperrnachrichtService, useValue: { meine: () => of([]) } },
        { provide: StatementService, useValue: { unbeantworteteAussagen: unbeantworteteLaden } },
        {
          provide: AuthService,
          useValue: { getCurrentUserId: () => null, getUserInfo: () => null, userInfo$: of(null) },
        },
      ],
    });

    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
  }

  async function erstellen(results: any[]): Promise<void> {
    konfigurieren(() => of({ beitraege: results, gesamt: results.length }));
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(MeineBeitraegeComponent);
    fixture.detectChanges();
  }

  function text(selektor: string): string {
    return (fixture.nativeElement.querySelector(selektor) as HTMLElement).textContent!
      .replace(/\s+/g, ' ')
      .trim();
  }

  function karten(): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('app-beitragskarte article'));
  }

  function album(): AlbumComponent {
    return fixture.debugElement.query((el) => el.componentInstance instanceof AlbumComponent).componentInstance;
  }

  describe('Tabs', () => {
    function tabs(): HTMLButtonElement[] {
      return Array.from(fixture.nativeElement.querySelectorAll('[role="tab"]'));
    }

    function tabWaehlen(name: string): void {
      tabs().find((tab) => tab.textContent!.trim() === name)!.click();
      fixture.detectChanges();
    }

    function sichtbar(selektor: string): boolean {
      const element = fixture.nativeElement.querySelector(selektor) as HTMLElement | null;
      return !!element && !element.closest('[hidden]');
    }

    it('zeigt zuerst die eigenen Beitraege und laedt Einwuerfe noch nicht', async () => {
      await erstellen([beitrag()]);

      expect(tabs().map((tab) => tab.textContent!.trim())).toEqual(['Meine Beiträge', 'Meine Einwürfe']);
      expect(tabs()[0].getAttribute('aria-selected')).toBe('true');
      expect(sichtbar('app-album')).toBeTrue();
      expect(fixture.nativeElement.querySelector('app-meine-einwuerfe')).toBeNull();
      expect(eigeneLaden).not.toHaveBeenCalled();
    });

    it('zeigt unter "Meine Einwürfe" die eigenen Einwuerfe statt der Beitraege', async () => {
      await erstellen([beitrag()]);

      tabWaehlen('Meine Einwürfe');

      expect(tabs()[1].getAttribute('aria-selected')).toBe('true');
      expect(sichtbar('app-meine-einwuerfe')).toBeTrue();
      expect(sichtbar('app-album')).toBeFalse();
      expect(eigeneLaden).toHaveBeenCalledTimes(1);
    });

    // #508: Nach dem Ausformulieren geht es hierher, wo der Einwurf als ausformuliert steht.
    it('oeffnet "Meine Einwürfe" auf dem Ruecksprung nach dem Ausformulieren', async () => {
      konfigurieren(() => of({ beitraege: [], gesamt: 0 }));
      TestBed.inject(Router).resetConfig([{ path: 'contributions', component: MeineBeitraegeComponent }]);
      (router.navigate as jasmine.Spy).and.callThrough();
      const harness = await RouterTestingHarness.create();

      TestBed.inject(NavigationService).navigateToMeineEinwuerfe();
      await harness.fixture.whenStable();
      harness.detectChanges();
      // Die Komponente nimmt den Tab aus der Adresse und raeumt sie danach auf.
      await harness.fixture.whenStable();
      fixture = harness.fixture as unknown as typeof fixture;

      // Der Tab gilt nur fuer den Sprung; ein Neuladen zeigt wieder den ersten.
      expect(router.url).toBe('/contributions');
      expect(tabs()[1].getAttribute('aria-selected')).toBe('true');
      expect(sichtbar('app-meine-einwuerfe')).toBeTrue();
      expect(eigeneLaden).toHaveBeenCalledTimes(1);
    });

    it('laedt beim Hin- und Herwechseln nichts neu', async () => {
      await erstellen([beitrag()]);

      tabWaehlen('Meine Einwürfe');
      tabWaehlen('Meine Beiträge');
      tabWaehlen('Meine Einwürfe');

      expect(eigeneLaden).toHaveBeenCalledTimes(1);
    });

    it('verbindet jeden Tab mit seinem Bereich und hat nur einen Tab-Stopp', async () => {
      await erstellen([beitrag()]);

      for (const tab of tabs()) {
        const bereich = fixture.nativeElement.querySelector(`#${tab.getAttribute('aria-controls')}`);
        expect(bereich.getAttribute('role')).toBe('tabpanel');
        expect(bereich.getAttribute('aria-labelledby')).toBe(tab.id);
      }
      expect(tabs().map((tab) => tab.getAttribute('tabindex'))).toEqual(['0', '-1']);
    });

    it('wechselt mit den Pfeiltasten und nimmt den Fokus mit', async () => {
      await erstellen([beitrag()]);
      const taste = (key: string) => {
        tabs()[0].parentElement!.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
        fixture.detectChanges();
      };

      taste('ArrowRight');
      expect(tabs()[1].getAttribute('aria-selected')).toBe('true');
      expect(document.activeElement).toBe(tabs()[1]);
      expect(sichtbar('app-meine-einwuerfe')).toBeTrue();

      taste('ArrowRight');
      expect(tabs()[0].getAttribute('aria-selected')).toBe('true');

      taste('End');
      expect(tabs()[1].getAttribute('tabindex')).toBe('0');
      taste('Home');
      expect(tabs()[0].getAttribute('tabindex')).toBe('0');
    });
  });

  it('laedt alle eigenen Beitraege und zeigt sie im Album als volle Karten', async () => {
    await erstellen([beitrag({ id: 'b1' }), beitrag({ id: 'b2', title: 'Tempo 30 rettet Leben' })]);

    expect(alleLaden).toHaveBeenCalledTimes(1);
    expect(fixture.nativeElement.querySelector('app-album')).not.toBeNull();
    expect(karten().length).toBe(2);
    expect(fixture.nativeElement.querySelector('mat-paginator')).toBeNull();
  });

  it('gibt dem Album den offenen Meilenstein, dem die Person am naechsten ist', async () => {
    meilensteine = [
      meilenstein({ kennung: 'a', erreicht: true, stand: 1 }),
      meilenstein({ kennung: 'x', art: 'weg' }),
      meilenstein({ kennung: 'b', name: '10-mal genutzt', schwelle: 10, stand: 6 }),
      meilenstein({ kennung: 'c', name: '50-mal genutzt', schwelle: 50, stand: 6 }),
    ];
    await erstellen([beitrag()]);

    expect(album().naechsterMeilenstein?.kennung).toBe('b');
  });

  it('stellt das Album vor Punkte und Meilensteine', async () => {
    await erstellen([beitrag()]);

    const bereich = fixture.nativeElement.querySelector('#meine-bereich-beitraege') as HTMLElement;
    const reihenfolge = Array.from(bereich.querySelectorAll('app-album, app-punkte, app-meilensteine')).map((e) =>
      e.tagName.toLowerCase(),
    );
    expect(reihenfolge).toEqual(['app-album', 'app-punkte', 'app-meilensteine']);
  });

  it('laedt nach dem Ändern still nach und laesst das Album stehen', async () => {
    verwalten.aendern.and.returnValue(of(true));
    await erstellen([beitrag()]);
    const vorher = album();

    album().aendern.emit(album().eintraege[0].karte);
    fixture.detectChanges();

    expect(verwalten.aendern).toHaveBeenCalledWith(jasmine.objectContaining({ id: 'b1' }));
    expect(alleLaden).toHaveBeenCalledTimes(2);
    expect(album()).toBe(vorher);
  });

  it('laedt nach abgebrochenem Ändern nicht nach', async () => {
    verwalten.aendern.and.returnValue(of(false));
    await erstellen([beitrag()]);

    album().aendern.emit(album().eintraege[0].karte);

    expect(alleLaden).toHaveBeenCalledTimes(1);
  });

  it('laedt nach dem Löschen nach, ohne den gelöschten Beitrag', async () => {
    let antwort = [beitrag({ id: 'b1' }), beitrag({ id: 'b2' })];
    verwalten.loeschen.and.returnValue(of(true));
    konfigurieren(() => of({ beitraege: antwort, gesamt: antwort.length }));
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(MeineBeitraegeComponent);
    fixture.detectChanges();

    antwort = [beitrag({ id: 'b2' })];
    album().loeschen.emit(album().eintraege[0].karte);
    fixture.detectChanges();

    expect(verwalten.loeschen).toHaveBeenCalledWith('b1');
    expect(karten().length).toBe(1);
  });

  it('nimmt den gelöschten Beitrag sofort heraus und meldet, wenn das Nachladen scheitert', async () => {
    let scheitern = false;
    const antwort = [beitrag({ id: 'b1' }), beitrag({ id: 'b2' })];
    verwalten.loeschen.and.returnValue(of(true));
    konfigurieren(() => (scheitern ? throwError(() => new Error('weg')) : of({ beitraege: antwort, gesamt: 2 })));
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(MeineBeitraegeComponent);
    fixture.detectChanges();
    const snackBar = TestBed.inject(MatSnackBar) as jasmine.SpyObj<MatSnackBar>;

    scheitern = true;
    album().loeschen.emit(album().eintraege[0].karte);
    fixture.detectChanges();

    expect(karten().length).toBe(1);
    expect(snackBar.open).toHaveBeenCalledWith('Deine Beiträge ließen sich gerade nicht aktualisieren.', 'OK', { duration: 5000 });
    expect(fixture.nativeElement.querySelector('[role="alert"]')).toBeNull();
  });

  it('bietet bei einem Ladefehler einen neuen Versuch an, ohne „neu laden“', async () => {
    konfigurieren(() => throwError(() => new Error('weg')));
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(MeineBeitraegeComponent);
    fixture.detectChanges();

    const meldung = text('[role="alert"]');
    expect(meldung).toContain('ließen sich gerade nicht laden');
    expect(meldung).not.toMatch(/neu laden/i);
    expect(fixture.nativeElement.querySelector('.beitraege-leer')).toBeNull();
  });

  it('sagt, wenn es noch keine Beitraege gibt', async () => {
    await erstellen([]);

    expect(text('.beitraege-leer')).toBe('Du hast noch keine Beiträge.');
    expect(karten().length).toBe(0);
  });

  describe('erster Schritt im leeren Zustand (#645)', () => {
    function unbeantwortete(n: number) {
      return Array.from({ length: n }, (_, i) => ({
        statement_id: `a-${i + 1}`,
        statement_text: `Unbeantwortete Aussage ${i + 1}`,
        personen_ohne_treffer: 0,
        themen: [],
      }));
    }

    function eintraege(): HTMLElement[] {
      return Array.from(fixture.nativeElement.querySelectorAll('[data-testid="unbeantwortete-aussage"]'));
    }

    it('zeigt die ersten drei unbeantworteten Aussagen mit "Antworten" ins Kommentarformular', async () => {
      unbeantworteteLaden.and.returnValue(of(unbeantwortete(5)));
      await erstellen([]);

      expect(text('.erster-schritt h2')).toBe('Fang mit einer unbeantworteten Aussage an');
      expect(eintraege().map((e) => e.querySelector('.aussagekarte-titel')!.textContent!.trim())).toEqual([
        'Unbeantwortete Aussage 1',
        'Unbeantwortete Aussage 2',
        'Unbeantwortete Aussage 3',
      ]);
      const antworten = eintraege()[0].querySelector('a.antworten') as HTMLAnchorElement;
      expect(antworten.textContent!.trim()).toBe('Antworten');
      // Nebenknopf: "Beitragen" bleibt der einzige Hauptknopf der Seite
      expect(antworten.classList).not.toContain('dark-green-button');
      expect(antworten.getAttribute('href')).toBe('/workflow/add-commentary?aussage=a-1&von=hier-fehlt-eine-antwort');
      expect(
        (fixture.nativeElement.querySelector('.alle-unbeantworteten') as HTMLAnchorElement).getAttribute('href'),
      ).toBe('/hier-fehlt-eine-antwort');
      // "Beitragen" bleibt als zweiter Weg.
      expect(fixture.nativeElement.querySelector('.beitraege-leer-knopf')).not.toBeNull();
    });

    it('zeigt ohne unbeantwortete Aussagen oder bei einem Ladefehler nur "Beitragen"', async () => {
      unbeantworteteLaden.and.returnValue(throwError(() => new Error('weg')));
      await erstellen([]);

      expect(fixture.nativeElement.querySelector('.erster-schritt')).toBeNull();
      expect(fixture.nativeElement.querySelector('.beitraege-leer-knopf')).not.toBeNull();
    });

    it('fragt mit eigenen Beiträgen nicht nach unbeantworteten Aussagen', async () => {
      await erstellen([beitrag()]);

      expect(unbeantworteteLaden).not.toHaveBeenCalled();
    });
  });

  // Design-Audit C8 (#512): Der leere Zustand war nur ein Satz, ohne Weg weiter.
  it('fuehrt aus dem leeren Zustand zum Beitragen', async () => {
    await erstellen([]);
    const navigieren = TestBed.inject(Router).navigate as jasmine.Spy;
    navigieren.calls.reset();

    const knopf = fixture.nativeElement.querySelector('.beitraege-leer-knopf') as HTMLButtonElement;
    expect(knopf.textContent!.trim()).toBe('Beitragen');
    knopf.click();

    expect(navigieren).toHaveBeenCalledWith(['/contribute']);
  });
});
