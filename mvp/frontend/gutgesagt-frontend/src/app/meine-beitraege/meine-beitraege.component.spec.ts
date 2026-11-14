import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { Observable, of, throwError } from 'rxjs';
import { delay } from 'rxjs/operators';

import { MeineBeitraegeComponent } from './meine-beitraege.component';
import { MeineBeitraegeService } from '../services/meine-beitraege.service';
import { UsageTrackingService, UserUsageStats } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { BeitragSheetComponent, GEAENDERT, GELOESCHT } from '../beitragskarte/beitrag-sheet.component';
import { EinwurfService } from '../services/einwurf.service';
import { SperrnachrichtService } from '../services/sperrnachricht.service';
import { NavigationService } from '../services/navigation.service';
import { StatementService } from '../services/statement.service';

describe('MeineBeitraegeComponent', () => {
  let fixture: ComponentFixture<MeineBeitraegeComponent>;
  let router: Router;
  let bottomSheet: MatBottomSheet;
  let eigeneLaden: jasmine.Spy;
  /** Womit das Bottom Sheet schliesst; Standard: ohne Ergebnis. */
  let sheetErgebnis: Observable<unknown>;
  let kennung: string | null;
  let nutzungsstatistik: UserUsageStats | null;
  /** Was "Hier fehlt eine Antwort" liefert; Standard: keine. */
  let unbeantworteteLaden: jasmine.Spy;

  beforeEach(() => {
    unbeantworteteLaden = jasmine.createSpy('unbeantworteteAussagen').and.returnValue(of([]));
    sheetErgebnis = of(undefined);
    kennung = null;
    nutzungsstatistik = null;
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

  function konfigurieren(meineBeitraege: (seite: number, groesse: number) => Observable<any>, mobil = false): void {
    eigeneLaden = jasmine
      .createSpy('eigeneLaden')
      .and.returnValue(of({ results_count: 0, results: [], total_records_count: 0 }));
    TestBed.configureTestingModule({
      imports: [MeineBeitraegeComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: BreakpointObserver, useValue: { observe: () => of({ matches: mobil, breakpoints: {} }) } },
        { provide: MeineBeitraegeService, useValue: { meineBeitraege } },
        {
          provide: UsageTrackingService,
          useValue: { getEigeneNutzungsstatistik: () => of(nutzungsstatistik), getEigeneMeilensteine: () => of([]), getEigenePunkte: () => of(null), getAbzeichenSichtbarkeit: () => of(null) },
        },
        { provide: EinwurfService, useValue: { eigeneLaden } },
        { provide: SperrnachrichtService, useValue: { meine: () => of([]) } },
        { provide: StatementService, useValue: { unbeantworteteAussagen: unbeantworteteLaden } },
        {
          provide: AuthService,
          // Die Album-Karten fragen nach der eigenen Kennung und abonnieren sie.
          useValue: { getCurrentUserId: () => kennung, getUserInfo: () => null, userInfo$: of(null) },
        },
      ],
    });

    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    bottomSheet = TestBed.inject(MatBottomSheet);
    spyOn(bottomSheet, 'open').and.callFake(() => ({ afterDismissed: () => sheetErgebnis }) as any);
  }

  async function erstellen(results: any[], mobil = false): Promise<void> {
    konfigurieren(
      () => of({ results_count: results.length, total_records_count: results.length, results }),
      mobil,
    );
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
      expect(sichtbar('app-kartenliste')).toBeTrue();
      expect(fixture.nativeElement.querySelector('app-meine-einwuerfe')).toBeNull();
      expect(eigeneLaden).not.toHaveBeenCalled();
    });

    it('zeigt unter "Meine Einwürfe" die eigenen Einwuerfe statt der Beitraege', async () => {
      await erstellen([beitrag()]);

      tabWaehlen('Meine Einwürfe');

      expect(tabs()[1].getAttribute('aria-selected')).toBe('true');
      expect(sichtbar('app-meine-einwuerfe')).toBeTrue();
      expect(sichtbar('app-kartenliste')).toBeFalse();
      expect(eigeneLaden).toHaveBeenCalledTimes(1);
    });

    // #508: Nach dem Ausformulieren geht es hierher, wo der Einwurf als ausformuliert steht.
    it('oeffnet "Meine Einwürfe" auf dem Ruecksprung nach dem Ausformulieren', async () => {
      konfigurieren(() => of({ results_count: 0, total_records_count: 0, results: [] }));
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

  it('beschriftet den Paginator auf Deutsch', async () => {
    await erstellen(Array.from({ length: 25 }, (_, i) => beitrag({ id: `b${i}` })));

    expect(text('.mat-mdc-paginator-page-size-label')).toBe('Einträge pro Seite:');
    expect(text('.mat-mdc-paginator-range-label')).toBe('1 – 24 von 25');
  });

  it('zeigt mobil nur Bereich und Pfeile, ohne Seitengroesse', async () => {
    await erstellen(Array.from({ length: 30 }, (_, i) => beitrag({ id: `b${i}` })), true);

    expect(fixture.nativeElement.querySelector('.mat-mdc-paginator-page-size')).toBeNull();
    expect(text('.mat-mdc-paginator-range-label')).toBe('1 – 24 von 30');
    expect(fixture.nativeElement.querySelector('.mat-mdc-paginator-navigation-next')).not.toBeNull();
  });

  it('laedt nach zweimal "Weiter" Seite 3, auch wenn die Antwort auf sich warten laesst', fakeAsync(() => {
    const geladen: number[][] = [];
    konfigurieren((seite, groesse) => {
      geladen.push([seite, groesse]);
      const results = Array.from({ length: 24 }, (_, i) => beitrag({ id: `s${seite}-${i}` }));
      return of({ results_count: 24, total_records_count: 60, results }).pipe(delay(50));
    });
    fixture = TestBed.createComponent(MeineBeitraegeComponent);

    const laden = () => {
      fixture.detectChanges();
      tick(50);
      fixture.detectChanges();
    };
    const weiter = () => (fixture.nativeElement.querySelector('.mat-mdc-paginator-navigation-next') as HTMLButtonElement).click();

    laden();
    weiter();
    laden();
    weiter();
    laden();

    expect(geladen).toEqual([[1, 24], [2, 24], [3, 24]]);
    expect(text('.mat-mdc-paginator-range-label')).toBe('49 – 60 von 60');
  }));

  it('zeigt bis 24 Beitraege keinen Paginator', async () => {
    await erstellen(Array.from({ length: 24 }, (_, i) => beitrag({ id: `b${i}` })));

    expect(karten().length).toBe(24);
    expect(fixture.nativeElement.querySelector('mat-paginator')).toBeNull();
  });

  it('zeigt Beitraege als Album-Karten mit Typfarbe, Titel, Anriss, Datum und Nutzung', async () => {
    await erstellen([beitrag(), beitrag({ id: 'b2', content_type: 'commentary', title: 'Zweiter' })]);
    const [erste, zweite] = karten();

    expect(karten().length).toBe(2);
    expect(fixture.nativeElement.querySelector('table')).toBeNull();
    expect(fixture.nativeElement.querySelector('.kartenliste--raster')).not.toBeNull();
    expect(erste.classList).toContain('karte--kompakt');
    expect(erste.classList).toContain('typ-generictext');
    expect(zweite.classList).toContain('typ-commentary');
    expect(erste.querySelector('.album-inhalt .karte-titel')!.textContent).toContain('Wärmepumpe lohnt sich auch im Altbau');
    expect(erste.querySelector('.album-anriss')!.textContent).toContain('Text der Hintergrundinfo');
    expect(erste.querySelector('.album-fuss .karte-datum')!.textContent!.trim()).toBe('13.09.2026');
    expect(erste.querySelector('.album-fuss .badge-nutzung')!.textContent!.trim()).toBe('12× genutzt');
    expect(erste.getAttribute('aria-label')).toBe('Hintergrundinfo: Wärmepumpe lohnt sich auch im Altbau');
  });

  it('zeigt die Statistik als eine Textzeile, ohne Hinweisbox und Kacheln', async () => {
    await erstellen([beitrag(), beitrag({ id: 'b2', usage_count: 3 })]);

    expect(text('.album-statistik')).toBe('Deine 2 Beiträge wurden 15-mal genutzt.');
    expect(fixture.nativeElement.querySelector('.info-message')).toBeNull();
    expect(fixture.nativeElement.querySelector('.stat-card')).toBeNull();
  });

  it('schreibt einen Beitrag im Singular und nimmt die Gesamtnutzung, wenn es sie gibt', async () => {
    await erstellen([beitrag()]);

    expect(text('.album-statistik')).toBe('Dein Beitrag wurde 12-mal genutzt.');

    fixture.componentInstance.nutzungsstatistik = {
      user_id: 'person-1',
      unique_contents_contributed: 1,
      total_usage_count: 40,
      top_content: [],
    };
    fixture.componentInstance.totalRecords = 25;
    // Nicht alle Beitraege geladen: keine Zahl fuer die Woche
    expect(fixture.componentInstance.statistik).toBe('Deine 25 Beiträge wurden 40-mal genutzt.');
  });

  describe('Nutzungsstatistik', () => {
    // Die Nutzung ueber alle Seiten kommt vom Suchdienst; die Person ergibt sich aus der
    // Anmeldung, nicht aus der Adresse (#284).
    it('zeigt angemeldet die Nutzung aus der Nutzungsstatistik', async () => {
      kennung = 'person-1';
      nutzungsstatistik = { user_id: 'person-1', unique_contents_contributed: 1, total_usage_count: 40, top_content: [] };

      await erstellen([beitrag()]);

      expect(text('.album-statistik')).toBe('Dein Beitrag wurde 40-mal genutzt.');
    });

    // UX-Review B11: bei 0 Nutzungen erklaeren, was genutzt heisst, und den naechsten Schritt nennen
    it('erklaert bei 0 Nutzungen, was „genutzt“ heisst, und nennt den naechsten Schritt', async () => {
      kennung = 'person-1';
      nutzungsstatistik = { user_id: 'person-1', unique_contents_contributed: 1, total_usage_count: 0, top_content: [] };

      await erstellen([beitrag({ usage_count: 0 })]);

      expect(text('[data-testid=nutzung-leer]')).toContain('Noch hat niemand deine Beiträge genutzt.');
      expect(text('[data-testid=nutzung-leer]')).toContain('teil seinen Link');
    });

    it('zeigt die Erklaerung nicht, sobald etwas genutzt wurde oder die Statistik fehlt', async () => {
      kennung = 'person-1';
      nutzungsstatistik = { user_id: 'person-1', unique_contents_contributed: 1, total_usage_count: 3, top_content: [] };
      await erstellen([beitrag()]);
      expect(fixture.nativeElement.querySelector('[data-testid=nutzung-leer]')).toBeNull();
    });

    it('faellt ohne Nutzungsstatistik auf die Summe der Seite zurueck', async () => {
      kennung = 'person-1';

      await erstellen([beitrag()]);

      expect(text('.album-statistik')).toBe('Dein Beitrag wurde 12-mal genutzt.');
    });
  });

  describe('Wirkung zuerst (Nutzerfuehrung 13.11.)', () => {
    it('nennt die Nutzung dieser Woche und erklaert, was genutzt heisst', async () => {
      await erstellen([
        beitrag({ usage_count: 5, nutzung_letzte_7_tage: 2 }),
        beitrag({ id: 'b2', usage_count: 3, nutzung_letzte_7_tage: 1 }),
      ]);

      expect(text('.album-statistik')).toBe('Deine 2 Beiträge wurden 8-mal genutzt, 3 davon diese Woche.');
      expect(text('.nutzung-erklaerung')).toBe('Genutzt heißt: Jemand hat den Beitrag kopiert oder geteilt.');
    });

    it('zeigt ohne Nutzung keine Erklaerung', async () => {
      await erstellen([beitrag({ usage_count: 0 })]);

      expect(text('.album-statistik')).toBe('Dein Beitrag wurde noch nicht genutzt.');
      expect(fixture.nativeElement.querySelector('.nutzung-erklaerung')).toBeNull();
    });

    it('sortiert die Beitraege nach Nutzung, bei Gleichstand wie der Server', async () => {
      await erstellen([
        beitrag({ id: 'a', title: 'Neu und ungenutzt', usage_count: 0 }),
        beitrag({ id: 'b', title: 'Viel genutzt', usage_count: 9 }),
        beitrag({ id: 'c', title: 'Etwas genutzt', usage_count: 2 }),
        beitrag({ id: 'd', title: 'Auch ungenutzt', usage_count: 0 }),
      ]);

      expect(karten().map((karte) => karte.querySelector('.karte-titel')!.textContent!.trim())).toEqual([
        'Viel genutzt',
        'Etwas genutzt',
        'Neu und ungenutzt',
        'Auch ungenutzt',
      ]);
    });

    it('stellt Satz und Beitraege vor Punkte und Meilensteine', async () => {
      await erstellen([beitrag()]);
      const bereich = fixture.nativeElement.querySelector('#meine-bereich-beitraege') as HTMLElement;
      const reihenfolge = Array.from(bereich.querySelectorAll('.album-statistik, app-kartenliste, app-punkte, app-meilensteine')).map(
        (el) => (el as HTMLElement).tagName.toLowerCase() === 'p' ? 'satz' : (el as HTMLElement).tagName.toLowerCase(),
      );

      expect(reihenfolge).toEqual(['satz', 'app-kartenliste', 'app-punkte', 'app-meilensteine']);
    });
  });

  it('zeigt 24 Beitraege pro Seite', async () => {
    await erstellen([beitrag()]);

    expect(fixture.componentInstance.pageSize).toBe(24);
  });

  it('zeigt im Album keinen Volltext, keine Autorzeile und keine Aktionen', async () => {
    await erstellen([beitrag()]);
    const [karte] = karten();

    expect(karte.querySelector('.karte-text')).toBeNull();
    expect(karte.querySelector('.karte-meta')).toBeNull();
    expect(karte.querySelector('app-karten-aktionen')).toBeNull();
    expect(karte.querySelector('.badge-neu')).toBeNull();
  });

  it('oeffnet beim Tippen den Beitrag im Bottom Sheet und startet keine Suche', async () => {
    await erstellen([beitrag()]);

    karten()[0].click();

    const oeffnen = bottomSheet.open as jasmine.Spy;
    expect(oeffnen).toHaveBeenCalledTimes(1);
    const [komponente, konfiguration] = oeffnen.calls.mostRecent().args;
    expect(komponente).toBe(BeitragSheetComponent);
    expect(konfiguration.data).toEqual(jasmine.objectContaining({ id: 'b1', titel: 'Wärmepumpe lohnt sich auch im Altbau' }));
    expect(konfiguration.ariaLabel).toBe('Wärmepumpe lohnt sich auch im Altbau');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('oeffnet das Bottom Sheet auch mit Enter und ohne Titel', async () => {
    await erstellen([beitrag({ title: null })]);
    const [karte] = karten();

    karte.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));

    expect(karte.querySelector('.karte-titel')!.textContent).toContain('Text der Hintergrundinfo');
    expect(karte.querySelector('.album-anriss')).toBeNull();
    const oeffnen = bottomSheet.open as jasmine.Spy;
    expect(oeffnen).toHaveBeenCalledTimes(1);
    const [komponente, konfiguration] = oeffnen.calls.mostRecent().args;
    expect(komponente).toBe(BeitragSheetComponent);
    expect(konfiguration.ariaLabel).toBe('Text der Hintergrundinfo');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('erlaubt im Bottom Sheet das Löschen des eigenen Beitrags', async () => {
    await erstellen([beitrag()]);

    karten()[0].click();

    const [, konfiguration] = (bottomSheet.open as jasmine.Spy).calls.mostRecent().args;
    expect(konfiguration.data.loeschbar).toBeTrue();
  });

  it('laedt nach dem Löschen die Seite neu, ohne den gelöschten Beitrag', async () => {
    const vorher = [beitrag(), beitrag({ id: 'b2', title: 'Tempolimit spart sofort CO2' })];
    const nachher = [beitrag({ id: 'b2', title: 'Tempolimit spart sofort CO2' })];
    const laden = jasmine
      .createSpy('meineBeitraege')
      .and.returnValues(
        of({ results_count: 2, total_records_count: 2, results: vorher }),
        of({ results_count: 1, total_records_count: 1, results: nachher }),
      );
    konfigurieren(laden);
    sheetErgebnis = of(GELOESCHT);
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(MeineBeitraegeComponent);
    fixture.detectChanges();

    karten()[0].click();
    fixture.detectChanges();

    expect(laden).toHaveBeenCalledTimes(2);
    expect(laden.calls.mostRecent().args).toEqual([1, 24]);
    expect(karten().length).toBe(1);
    expect(text('.album-statistik')).toContain('Dein Beitrag');
  });

  it('springt eine Seite zurück, wenn der letzte Beitrag einer Seite gelöscht ist', async () => {
    const seite = (n: number) =>
      Array.from({ length: n }, (_, i) => beitrag({ id: `b${i}`, title: `Beitrag Nummer ${i}` }));
    const laden = jasmine
      .createSpy('meineBeitraege')
      .and.returnValues(
        of({ results_count: 24, total_records_count: 25, results: seite(24) }),
        of({ results_count: 1, total_records_count: 25, results: seite(1) }),
        of({ results_count: 24, total_records_count: 24, results: seite(24) }),
      );
    konfigurieren(laden);
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(MeineBeitraegeComponent);
    fixture.detectChanges();
    fixture.componentInstance.onPageChange({ pageIndex: 1, pageSize: 24, length: 25 } as any);
    fixture.detectChanges();
    sheetErgebnis = of(GELOESCHT);

    karten()[0].click();

    expect(laden.calls.mostRecent().args).toEqual([1, 24]);
    expect(fixture.componentInstance.pageIndex).toBe(0);
  });

  it('erlaubt im Bottom Sheet das Ändern nur bei Kommentar und Hintergrundinfo', async () => {
    await erstellen([
      beitrag(),
      beitrag({ id: 'b2', content_type: 'commentary', title: 'Tempolimit spart sofort CO2' }),
      beitrag({ id: 'b3', content_type: 'post', title: 'Ein Post zum Tempolimit' }),
    ]);
    const aenderbar = (i: number) => {
      karten()[i].click();
      return (bottomSheet.open as jasmine.Spy).calls.mostRecent().args[1].data.aenderbar;
    };

    expect([aenderbar(0), aenderbar(1), aenderbar(2)]).toEqual([true, true, false]);
  });

  it('laedt nach dem Ändern die aktuelle Seite neu', async () => {
    const laden = jasmine
      .createSpy('meineBeitraege')
      .and.returnValues(
        of({ results_count: 1, total_records_count: 1, results: [beitrag()] }),
        of({ results_count: 1, total_records_count: 1, results: [beitrag({ title: 'Neuer Titel mit Haltung' })] }),
      );
    konfigurieren(laden);
    sheetErgebnis = of(GEAENDERT);
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(MeineBeitraegeComponent);
    fixture.detectChanges();

    karten()[0].click();
    fixture.detectChanges();

    expect(laden).toHaveBeenCalledTimes(2);
    expect(karten()[0].textContent).toContain('Neuer Titel mit Haltung');
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
