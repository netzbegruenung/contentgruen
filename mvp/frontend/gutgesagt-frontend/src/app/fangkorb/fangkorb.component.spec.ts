import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { Clipboard } from '@angular/cdk/clipboard';
import { BreakpointObserver, BreakpointState } from '@angular/cdk/layout';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BehaviorSubject, NEVER, Subject, of, throwError } from 'rxjs';
import { map } from 'rxjs/operators';

import { LADE_GROESSE, FangkorbComponent, SEITENLEISTE_MEDIEN } from './fangkorb.component';
import { LADE_TIMEOUT_MS, WIEDERHOLUNG_MS } from '../shared/lade-wiederholung';
import { FILTER_SCHLUESSEL } from './fangkorb-filter';
import { EinwurfBeitragSheetComponent } from './einwurf-beitrag-sheet.component';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { PLATTFORMEN } from '../shared/plattform';
import {
  EinwurfSeite,
  Einwurf,
  Satz,
  AusformuliertIn,
  EinwurfService,
} from '../services/einwurf.service';
import { AuthService, UserInfo } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';

function einwurf(overrides: Partial<Einwurf> = {}): Einwurf {
  return {
    id: 'id-1',
    content: null,
    url: 'https://example.org/post',
    image_url: null,
    // Wie der Server ihn Nicht-Admins liefert: ohne Kennung, mit Kennzeichen (#385).
    submitted_by: null,
    ist_eigener_einwurf: true,
    source_channel: 'web',
    status: 'open',
    created_at: '2026-09-13T12:00:00Z',
    destilled_by: null,
    own_draft: null,
    drafts: [],
    links: [],
    ...overrides,
  };
}

function satz(id: string, user_id: string, sentence: string): Satz {
  return { id, user_id, sentence, updated_at: '2026-09-13T12:00:00Z' };
}

function link(draft_id: string | null, content_type: string | null = 'commentary', content_id = `c-${draft_id}`): AusformuliertIn {
  return {
    content_id,
    content_type,
    draft_id,
    processed_by: 'carol',
    processed_at: '2026-09-13T13:00:00Z',
  };
}

/** Ein Einwurf je Tab, damit jeder Tab etwas zu zeigen hat. */
function jeTab(): Einwurf[] {
  return [
    einwurf({ id: 'roh' }),
    einwurf({ id: 'satz', status: 'in_progress', drafts: [satz('s-1', 'bob', 'Ein Satz')] }),
    einwurf({
      id: 'fertig',
      status: 'processed',
      drafts: [satz('s-2', 'bob', 'Genommen')],
      links: [link('s-2')],
    }),
    einwurf({ id: 'weg', status: 'discarded' }),
  ];
}

function antwort(results: Einwurf[], gesamt = results.length): EinwurfSeite {
  return { results_count: results.length, results, total_records_count: gesamt };
}

describe('FangkorbComponent', () => {
  let fixture: ComponentFixture<FangkorbComponent>;
  let component: FangkorbComponent;
  let einwurfService: jasmine.SpyObj<EinwurfService>;
  let router: Router;
  let bottomSheet: MatBottomSheet;
  let clipboard: jasmine.SpyObj<Clipboard>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let nutzer: UserInfo;
  /** Ob SEITENLEISTE_MEDIEN passt; standardmaessig nicht (Handy-Layout). */
  let breit$: BehaviorSubject<boolean>;
  let beobachteteMedien: string[];

  function erstellen(results: Einwurf[], gesamt?: number): void {
    einwurfService.fangkorbLaden.and.returnValue(of(antwort(results, gesamt)));
    fixture = TestBed.createComponent(FangkorbComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function karten(): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('article.karte--einwurf'));
  }

  function kartenKomponenten(): BeitragskarteComponent[] {
    return fixture.debugElement
      .queryAll(By.directive(BeitragskarteComponent))
      .map((eintrag) => eintrag.componentInstance as BeitragskarteComponent);
  }

  function tabKnopf(name: string): HTMLButtonElement {
    const knoepfe: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('button.tab'));
    return knoepfe.find((knopf) => knopf.querySelector('.tab-wort')!.textContent!.trim() === name)!;
  }

  function zaehler(name: string): string {
    return tabKnopf(name).querySelector('.tab-zahl')!.textContent!.trim();
  }

  function filterKnopf(beschriftung: string): HTMLButtonElement {
    const knoepfe: HTMLButtonElement[] = Array.from(
      fixture.nativeElement.querySelectorAll('button.filter-chip'),
    );
    return knoepfe.find((knopf) => knopf.textContent!.trim() === beschriftung)!;
  }

  function klicken(knopf: HTMLElement): void {
    knopf.click();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    sessionStorage.removeItem(FILTER_SCHLUESSEL);
    nutzer = { isAuthenticated: true, userId: 'alice', userName: null, claims: null };
    einwurfService = jasmine.createSpyObj('EinwurfService', ['fangkorbLaden', 'updateStatus']);
    clipboard = jasmine.createSpyObj('Clipboard', ['copy']);
    clipboard.copy.and.returnValue(true);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    breit$ = new BehaviorSubject(false);
    beobachteteMedien = [];

    await TestBed.configureTestingModule({
      imports: [FangkorbComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: EinwurfService, useValue: einwurfService },
        { provide: Clipboard, useValue: clipboard },
        { provide: MatSnackBar, useValue: snackBar },
        {
          provide: BreakpointObserver,
          useValue: {
            observe: (medien: string) => {
              beobachteteMedien.push(medien);
              return breit$.pipe(map((matches): BreakpointState => ({ matches, breakpoints: { [medien]: matches } })));
            },
          },
        },
        {
          provide: AuthService,
          useValue: {
            getCurrentUserId: () => nutzer.userId,
            getUserInfo: () => nutzer,
            userInfo$: of(nutzer),
            fetchUserInfo: () => of(nutzer),
          },
        },
        {
          provide: LoggingService,
          useValue: jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']),
        },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    bottomSheet = TestBed.inject(MatBottomSheet);
    spyOn(bottomSheet, 'open');
  });

  afterEach(() => sessionStorage.removeItem(FILTER_SCHLUESSEL));

  describe('Kopf', () => {
    it('zeigt die beiden Arbeitslisten als Tabs mit Zaehlern, ohne Einwerfen', () => {
      erstellen(jeTab());
      const woerter = Array.from(fixture.nativeElement.querySelectorAll('.tab-wort') as NodeListOf<HTMLElement>).map(
        (wort) => wort.textContent!.trim(),
      );

      expect(woerter).toEqual(['Destillieren', 'Ausformulieren']);
      expect(fixture.nativeElement.textContent).not.toContain('Einwerfen →');
      expect(zaehler('Destillieren')).toBe('1');
      expect(zaehler('Ausformulieren')).toBe('1');
    });

    it('beginnt beim Destillieren und wechselt auf Tipp', () => {
      erstellen(jeTab());

      expect(tabKnopf('Destillieren').getAttribute('aria-selected')).toBe('true');
      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['roh']);

      klicken(tabKnopf('Ausformulieren'));

      expect(tabKnopf('Ausformulieren').getAttribute('aria-selected')).toBe('true');
      expect(tabKnopf('Destillieren').getAttribute('aria-selected')).toBe('false');
      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['satz']);
    });

    it('oeffnet einen in der Sitzung gemerkten frueheren Tab "Ausformuliert" beim Destillieren', () => {
      sessionStorage.setItem(FILTER_SCHLUESSEL, JSON.stringify({ tab: 'ausformuliert', nurMeine: true }));

      erstellen(jeTab());

      expect(tabKnopf('Destillieren').getAttribute('aria-selected')).toBe('true');
      expect(component.filter.nurMeine).toBeTrue();
      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['roh']);
    });

    it('haelt Tab und Filter in der Sitzung', () => {
      erstellen(jeTab());
      klicken(tabKnopf('Ausformulieren'));
      klicken(filterKnopf('nur meine'));
      fixture.destroy();

      erstellen(jeTab());

      expect(component.filter.tab).toBe('ausformulieren');
      expect(component.filter.nurMeine).toBeTrue();
    });

    it('fuehrt mit dem schwebenden Knopf zum Einwerfen und zeigt die Erklaerung erst auf Tipp', () => {
      erstellen([]);
      const fab: HTMLButtonElement = fixture.nativeElement.querySelector('button.einwerfen-fab');
      // Beschriftet, kein zweites "+" neben Beitragen im Kopf (UX-Review B15)
      expect(fab.textContent).toContain('Einwerfen');
      expect(fab.textContent).not.toContain('add');

      expect(fixture.nativeElement.querySelector('.erklaerung')).toBeNull();
      klicken(fixture.nativeElement.querySelector('.erklaerung-umschalter'));
      expect(fixture.nativeElement.querySelector('.erklaerung')).toBeTruthy();

      klicken(fab);

      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen'], {
        queryParams: { von: 'fangkorb' },
      });
    });

    it('zeigt in beiden Tabs "nur meine", "verworfen" und die Plattformen, "nur offene" nicht mehr', () => {
      erstellen([]);
      for (const tab of ['Destillieren', 'Ausformulieren']) {
        klicken(tabKnopf(tab));
        const chips = Array.from(fixture.nativeElement.querySelectorAll('.filter-chip') as NodeListOf<HTMLElement>).map(
          (chip) => chip.textContent!.trim(),
        );

        expect(chips).toEqual(['nur meine', 'verworfen', ...PLATTFORMEN.map((eintrag) => eintrag.name)]);
      }
    });
  });

  describe('Tab-Muster', () => {
    function tabs(): HTMLButtonElement[] {
      return Array.from(fixture.nativeElement.querySelectorAll('[role="tab"]'));
    }

    function taste(key: string): void {
      tabs()[0].parentElement!.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
      fixture.detectChanges();
    }

    // Design-Audit B3 (#512): Ansichts-Umschalter sind sekundaer, gefuelltes Gruen
    // bleibt Aktionen vorbehalten.
    it('zeichnet den gewaehlten Tab als Tanne-Hauch mit Tanne-Text, nicht gefuellt', () => {
      erstellen(jeTab());
      const [gewaehlt, anderer] = tabs().map((tab) => getComputedStyle(tab));

      expect(gewaehlt.color).toBe('rgb(0, 84, 55)');
      expect(gewaehlt.backgroundColor).toBe('rgba(0, 84, 55, 0.07)');
      expect(gewaehlt.boxShadow).toContain('inset');
      expect(anderer.backgroundColor).toBe('rgba(0, 0, 0, 0)');
    });

    it('gibt jedem Tab seinen Bereich, zeigt nur den gewaehlten und hat nur einen Tab-Stopp', () => {
      erstellen(jeTab());
      const bereich = (tab: HTMLButtonElement): HTMLElement =>
        fixture.nativeElement.querySelector(`#${tab.getAttribute('aria-controls')}`);

      for (const tab of tabs()) {
        expect(bereich(tab).getAttribute('role')).toBe('tabpanel');
        expect(bereich(tab).getAttribute('aria-labelledby')).toBe(tab.id);
      }
      expect(new Set(tabs().map(bereich)).size).toBe(2);
      expect(tabs().map((tab) => bereich(tab).hidden)).toEqual([false, true]);
      expect(bereich(tabs()[0]).querySelectorAll('article.karte--einwurf').length).toBe(1);
      expect(bereich(tabs()[1]).children.length).toBe(0);
      expect(tabs().map((tab) => tab.getAttribute('tabindex'))).toEqual(['0', '-1']);

      klicken(tabs()[1]);

      expect(tabs().map((tab) => bereich(tab).hidden)).toEqual([true, false]);
      expect(bereich(tabs()[1]).querySelectorAll('article.karte--einwurf').length).toBe(1);
      expect(tabs().map((tab) => tab.getAttribute('tabindex'))).toEqual(['-1', '0']);
    });

    it('wechselt mit Pfeiltasten, Pos1 und Ende und nimmt den Fokus mit', () => {
      erstellen(jeTab());

      taste('ArrowRight');
      expect(component.filter.tab).toBe('ausformulieren');
      expect(document.activeElement).toBe(tabs()[1]);

      taste('ArrowRight');
      expect(component.filter.tab).toBe('destillieren');
      expect(document.activeElement).toBe(tabs()[0]);

      taste('ArrowLeft');
      expect(component.filter.tab).toBe('ausformulieren');

      taste('Home');
      expect(component.filter.tab).toBe('destillieren');

      taste('End');
      expect(component.filter.tab).toBe('ausformulieren');
      expect(document.activeElement).toBe(tabs()[1]);
    });

    it('laesst andere Tasten durch', () => {
      erstellen(jeTab());
      const ereignis = new KeyboardEvent('keydown', { key: 'a', bubbles: true, cancelable: true });

      tabs()[0].parentElement!.dispatchEvent(ereignis);

      expect(ereignis.defaultPrevented).toBeFalse();
      expect(component.filter.tab).toBe('destillieren');
    });

    it('sagt nebeneinander aria-orientation horizontal und laesst Pfeil runter durch', () => {
      erstellen(jeTab());
      const ereignis = new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true });

      tabs()[0].parentElement!.dispatchEvent(ereignis);

      expect(tabs()[0].parentElement!.getAttribute('aria-orientation')).toBe('horizontal');
      expect(ereignis.defaultPrevented).toBeFalse();
      expect(component.filter.tab).toBe('destillieren');
    });

    describe('in der Seitenleiste', () => {
      beforeEach(() => breit$.next(true));

      it('steht senkrecht und sagt das mit aria-orientation', () => {
        erstellen(jeTab());

        expect(tabs()[0].parentElement!.getAttribute('aria-orientation')).toBe('vertical');
      });

      it('wechselt mit Pfeil runter und hoch, Pos1 und Ende und nimmt den Fokus mit', () => {
        erstellen(jeTab());

        taste('ArrowDown');
        expect(component.filter.tab).toBe('ausformulieren');
        expect(document.activeElement).toBe(tabs()[1]);

        taste('ArrowDown');
        expect(component.filter.tab).toBe('destillieren');
        expect(document.activeElement).toBe(tabs()[0]);

        taste('ArrowUp');
        expect(component.filter.tab).toBe('ausformulieren');

        taste('Home');
        expect(component.filter.tab).toBe('destillieren');

        taste('End');
        expect(component.filter.tab).toBe('ausformulieren');
        expect(document.activeElement).toBe(tabs()[1]);
      });

      it('laesst Pfeil rechts und links durch', () => {
        erstellen(jeTab());
        for (const key of ['ArrowRight', 'ArrowLeft']) {
          const ereignis = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true });

          tabs()[0].parentElement!.dispatchEvent(ereignis);

          expect(ereignis.defaultPrevented).withContext(key).toBeFalse();
          expect(component.filter.tab).withContext(key).toBe('destillieren');
        }
      });

      it('richtet sich nach der Breite, wenn sie sich aendert', () => {
        erstellen(jeTab());
        breit$.next(false);
        fixture.detectChanges();

        expect(tabs()[0].parentElement!.getAttribute('aria-orientation')).toBe('horizontal');
        taste('ArrowRight');
        expect(component.filter.tab).toBe('ausformulieren');
      });
    });

    it('kuerzt bei 320 px keinen Tab-Namen', async () => {
      erstellen(jeTab());
      // TestBed haengt die Komponente ins Dokument; gemessen wird mit ihrem CSS, den
      // globalen Stilen (Seitenrand) und der Hausschrift, sobald sie geladen ist.
      const host: HTMLElement = fixture.nativeElement;
      host.style.display = 'block';
      host.style.width = '320px';
      const woerter = Array.from(host.querySelectorAll('.tab-wort') as NodeListOf<HTMLElement>);
      // Gemessen wird mit der Schrift, die die Tabs tatsaechlich nutzen; ohne Laden misst
      // der Test je nach Reihenfolge der Suite die Ersatzschrift (#552).
      await Promise.all(
        woerter.map((wort) => {
          const stil = getComputedStyle(wort);
          return document.fonts.load(`${stil.fontWeight} ${stil.fontSize} ${stil.fontFamily}`);
        }),
      );

      expect(host.isConnected).toBeTrue();
      expect(woerter.length).toBe(2);
      for (const wort of woerter) {
        expect(wort.clientWidth).withContext(wort.textContent!).toBeGreaterThan(0);
        expect(wort.scrollWidth).withContext(wort.textContent!).toBeLessThanOrEqual(wort.clientWidth);
      }
    });
  });

  describe('Layout', () => {
    function rechteck(selektor: string): DOMRect {
      return (fixture.nativeElement.querySelector(selektor) as HTMLElement).getBoundingClientRect();
    }

    function breiteSetzen(px: number): void {
      const host: HTMLElement = fixture.nativeElement;
      host.style.display = 'block';
      host.style.width = `${px}px`;
    }

    it('beobachtet die Breite ab 1024 px', () => {
      erstellen(jeTab());

      expect(SEITENLEISTE_MEDIEN).toBe('(min-width: 1024px)');
      expect(beobachteteMedien).toContain(SEITENLEISTE_MEDIEN);
    });

    it('stellt am Handy die Steuerung ueber die Liste, mit schwebendem Knopf und hochkanten Karten', () => {
      erstellen(jeTab());
      breiteSetzen(390);

      expect(fixture.nativeElement.querySelector('.fangkorb--seitenleiste')).toBeNull();
      expect(rechteck('.steuerung').bottom).toBeLessThanOrEqual(rechteck('.liste').top);
      expect(fixture.nativeElement.querySelector('button.einwerfen-fab')).toBeTruthy();
      expect(fixture.nativeElement.querySelector('button.einwerfen-knopf')).toBeNull();
      expect(kartenKomponenten().map((karte) => karte.quer)).toEqual([false]);
    });

    it('stellt ab 1024 px die Seitenleiste links neben die Liste, mit queren Karten', () => {
      breit$.next(true);
      erstellen(jeTab());
      breiteSetzen(1280);

      expect(fixture.nativeElement.querySelector('.fangkorb--seitenleiste')).toBeTruthy();
      const leiste = rechteck('.steuerung');
      const liste = rechteck('.liste');
      expect(leiste.right).toBeLessThanOrEqual(liste.left);
      expect(leiste.width).toBeGreaterThan(200);
      expect(leiste.width).toBeLessThanOrEqual(240);
      expect(liste.top).toBeLessThan(leiste.bottom);
      // Die Tabs untereinander, die Filter darunter
      const [erster, zweiter] = Array.from(fixture.nativeElement.querySelectorAll('[role="tab"]') as NodeListOf<HTMLElement>).map(
        (tab) => tab.getBoundingClientRect(),
      );
      expect(zweiter.top).toBeGreaterThanOrEqual(erster.bottom);
      expect(rechteck('.filterleiste').top).toBeGreaterThanOrEqual(zweiter.bottom);
      expect(kartenKomponenten().map((karte) => karte.quer)).toEqual([true]);
      expect(karten()[0].classList).toContain('karte--quer');
    });

    it('legt Einwerfen am Desktop als Knopf in die Seitenleiste statt schwebend', () => {
      breit$.next(true);
      erstellen([]);
      const knopf: HTMLButtonElement = fixture.nativeElement.querySelector('.steuerung button.einwerfen-knopf');

      expect(fixture.nativeElement.querySelector('button.einwerfen-fab')).toBeNull();
      expect(knopf.textContent).toContain('Etwas einwerfen');

      klicken(knopf);

      expect(router.navigate).toHaveBeenCalledWith(['/einwerfen'], {
        queryParams: { von: 'fangkorb' },
      });
    });
  });

  describe('Tab-Zuordnung', () => {
    it('legt einen Einwurf ohne Satz unter Destillieren', () => {
      erstellen(jeTab());

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['roh']);
      expect(karten().length).toBe(1);
    });

    it('legt Saetze ohne Beitrag unter Ausformulieren', () => {
      erstellen(jeTab());

      klicken(tabKnopf('Ausformulieren'));

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['satz']);
    });

    it('zeigt Ausformuliertes in keinem Tab, auch ohne Satz und mit Chip "verworfen"', () => {
      erstellen([
        ...jeTab(),
        einwurf({ id: 'alt', status: 'processed', created_at: '2026-09-01T10:00:00Z', links: [link(null, null)] }),
        einwurf({ id: 'weg-fertig', status: 'discarded', drafts: [satz('s-9', 'bob', 'X')], links: [link('s-9')] }),
      ]);

      for (const tab of ['Destillieren', 'Ausformulieren']) {
        klicken(tabKnopf(tab));
        expect(component.sichtbar.map((eintrag) => eintrag.id)).not.toContain('fertig');
        expect(component.sichtbar.map((eintrag) => eintrag.id)).not.toContain('alt');
      }
      klicken(filterKnopf('verworfen'));
      for (const tab of ['Destillieren', 'Ausformulieren']) {
        klicken(tabKnopf(tab));
        expect(component.sichtbar.map((eintrag) => eintrag.id)).not.toContain('weg-fertig');
      }
    });

    it('zeigt Verworfenes erst mit dem Chip, im Tab seiner naechsten Arbeit', () => {
      erstellen([
        ...jeTab(),
        einwurf({ id: 'weg-satz', status: 'discarded', drafts: [satz('s-3', 'bob', 'Doch ein Satz')] }),
      ]);
      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['roh']);

      klicken(filterKnopf('verworfen'));

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['roh', 'weg']);
      expect(zaehler('Destillieren')).toBe('2');
      expect(zaehler('Ausformulieren')).toBe('2');

      klicken(tabKnopf('Ausformulieren'));

      expect(filterKnopf('verworfen').getAttribute('aria-pressed')).toBe('true');
      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['satz', 'weg-satz']);
    });

    it('sortiert neueste zuerst, nicht eigene zuerst', () => {
      erstellen([
        einwurf({ id: 'alt', created_at: '2026-09-01T10:00:00Z' }),
        einwurf({ id: 'neu', created_at: '2026-09-14T10:00:00Z' }),
        einwurf({ id: 'mittel', created_at: '2026-09-10T10:00:00Z' }),
      ]);

      expect(component.sichtbar.map((eintrag) => eintrag.id)).toEqual(['neu', 'mittel', 'alt']);
    });

    it('sagt im leeren Tab "Ausformulieren" in einer Zeile, dass dort nichts liegt', () => {
      erstellen([einwurf({ id: 'roh' })]);
      klicken(tabKnopf('Ausformulieren'));

      expect(fixture.nativeElement.querySelector('.fangkorb-leer').textContent!.trim()).toBe(
        'Nichts auszuformulieren.',
      );
    });

    it('sagt im leeren Tab "Destillieren" in einer Zeile, dass dort nichts liegt', () => {
      erstellen([einwurf({ id: 'satz', status: 'in_progress', drafts: [satz('s-1', 'bob', 'Ein Satz')] })]);

      expect(fixture.nativeElement.querySelector('.fangkorb-leer').textContent!.trim()).toBe(
        'Nichts zu destillieren.',
      );
    });
  });

  describe('Laden', () => {
    it('laedt die Einwuerfe auf einmal, ohne Tabelle und ohne Paginator', () => {
      erstellen(jeTab());

      expect(einwurfService.fangkorbLaden).toHaveBeenCalledWith(1, LADE_GROESSE);
      expect(fixture.nativeElement.querySelector('table')).toBeNull();
      expect(fixture.nativeElement.querySelector('mat-paginator')).toBeNull();
    });

    it('meldet einen Ladefehler statt still leer zu bleiben', () => {
      einwurfService.fangkorbLaden.and.returnValue(throwError(() => new Error('kaputt')));
      fixture = TestBed.createComponent(FangkorbComponent);
      fixture.detectChanges();

      expect(fixture.componentInstance.ladefehler).toBeTrue();
      expect(fixture.nativeElement.textContent).toContain('konnte gerade nicht geladen werden');
      // Grundsatz: Oberflaechen laden selbst nach, niemand soll die Seite neu laden.
      expect(fixture.nativeElement.textContent).not.toMatch(/neu ?lad/i);
    });

    describe('nach einem Ladefehler', () => {
      function fehlerknopf(): HTMLButtonElement {
        return fixture.nativeElement.querySelector('button.erneut-versuchen');
      }

      function scheitertErstDann(...folge: Array<'fehler' | Einwurf[]>): void {
        einwurfService.fangkorbLaden.and.returnValues(
          ...folge.map((schritt) => (schritt === 'fehler' ? throwError(() => ({ status: 503 })) : of(antwort(schritt)))),
        );
        fixture = TestBed.createComponent(FangkorbComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
      }

      it('versucht es selbst wieder und zeigt danach die Liste', fakeAsync(() => {
        scheitertErstDann('fehler', jeTab());
        expect(component.ladefehler).toBeTrue();
        expect(fehlerknopf().textContent!.trim()).toBe('Erneut versuchen');
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(1);

        tick(WIEDERHOLUNG_MS[0] - 1);
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(1);
        tick(1);
        fixture.detectChanges();

        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);
        expect(component.ladefehler).toBeFalse();
        expect(fehlerknopf()).toBeNull();
        expect(karten().length).toBe(1);
      }));

      it('wartet nach jedem Fehlschlag laenger, hoechstens den letzten Abstand', fakeAsync(() => {
        const fehler = WIEDERHOLUNG_MS.map(() => 'fehler' as const);
        scheitertErstDann(...fehler, 'fehler', jeTab());

        for (const abstand of WIEDERHOLUNG_MS) {
          const vorher = einwurfService.fangkorbLaden.calls.count();
          tick(abstand - 1);
          expect(einwurfService.fangkorbLaden.calls.count()).withContext(`vor ${abstand} ms`).toBe(vorher);
          tick(1);
          expect(einwurfService.fangkorbLaden.calls.count()).withContext(`nach ${abstand} ms`).toBe(vorher + 1);
        }
        // Danach bleibt es beim letzten Abstand.
        tick(WIEDERHOLUNG_MS[WIEDERHOLUNG_MS.length - 1]);
        fixture.detectChanges();
        expect(component.ladefehler).toBeFalse();
        expect(karten().length).toBe(1);
      }));

      it('versucht es auf Knopfdruck sofort und verwirft den geplanten Versuch', fakeAsync(() => {
        scheitertErstDann('fehler', 'fehler', jeTab());

        klicken(fehlerknopf());
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);
        // Zweiter Fehlschlag: die Meldung bleibt, der naechste Versuch kommt nach dem zweiten Abstand.
        expect(component.ladefehler).toBeTrue();
        tick(WIEDERHOLUNG_MS[0]);
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);
        tick(WIEDERHOLUNG_MS[1] - WIEDERHOLUNG_MS[0]);
        fixture.detectChanges();
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(3);
        expect(karten().length).toBe(1);
      }));

      it('hoert auf, wenn die Seite verlassen wird', fakeAsync(() => {
        scheitertErstDann('fehler', jeTab());

        fixture.destroy();
        tick(WIEDERHOLUNG_MS[WIEDERHOLUNG_MS.length - 1]);

        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(1);
      }));

      it('sagt in der Live-Region nur den ersten Fehler und die Rueckkehr an', fakeAsync(() => {
        scheitertErstDann('fehler', 'fehler', jeTab());
        const region = (): HTMLElement => fixture.nativeElement.querySelector('.liste > [role="status"]');
        expect(region().textContent!.trim()).toBe('Der Fangkorb konnte gerade nicht geladen werden.');
        // Die Meldung mit Knopf steht ausserhalb der Region: der Wechseltext je Versuch wird nicht angesagt
        expect(region().contains(fehlerknopf())).toBeFalse();
        expect(fixture.nativeElement.querySelector('.fangkorb-fehler').closest('[role="status"]')).toBeNull();

        tick(WIEDERHOLUNG_MS[0]);
        fixture.detectChanges();
        expect(region().textContent!.trim()).toBe('Der Fangkorb konnte gerade nicht geladen werden.');

        tick(WIEDERHOLUNG_MS[1]);
        fixture.detectChanges();
        expect(region().textContent!.trim()).toBe('Fangkorb wieder geladen.');
      }));

      it('steht mit der Live-Region schon ohne Fehler im DOM, leer', () => {
        erstellen(jeTab());
        const region: HTMLElement = fixture.nativeElement.querySelector('.liste > [role="status"]');

        expect(region).toBeTruthy();
        expect(region.textContent!.trim()).toBe('');
      });

      it('zeigt waehrend eines Versuchs "Neuer Versuch läuft", der Knopf bleibt fokussierbar und tut nichts', () => {
        const zweiter = new Subject<ReturnType<typeof antwort>>();
        einwurfService.fangkorbLaden.and.returnValues(throwError(() => ({ status: 503 })), zweiter.asObservable());
        fixture = TestBed.createComponent(FangkorbComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector('.fangkorb-fehler p').textContent).toContain('Die Seite versucht es weiter.');

        fehlerknopf().focus();
        klicken(fehlerknopf());

        expect(component.erneutLaedt).toBeTrue();
        expect(fixture.nativeElement.querySelector('.fangkorb-fehler p').textContent).toContain('Neuer Versuch läuft …');
        expect(fehlerknopf().disabled).toBeFalse();
        expect(fehlerknopf().getAttribute('aria-disabled')).toBe('true');
        expect(document.activeElement).toBe(fehlerknopf());
        klicken(fehlerknopf());
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);

        zweiter.next(antwort(jeTab()));
        fixture.detectChanges();

        expect(component.erneutLaedt).toBeFalse();
        expect(fehlerknopf()).toBeNull();
        // Der Knopf ist weg; der Fokus steht im Bereich des Tabs
        expect(document.activeElement).toBe(fixture.nativeElement.querySelector('#fangkorb-bereich-destillieren'));
      });

      it('wiederholt bei 400 nicht von selbst, bietet aber den Knopf', fakeAsync(() => {
        einwurfService.fangkorbLaden.and.returnValues(throwError(() => ({ status: 400 })), of(antwort(jeTab())));
        fixture = TestBed.createComponent(FangkorbComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();

        tick(WIEDERHOLUNG_MS[WIEDERHOLUNG_MS.length - 1] * 2);
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(1);
        expect(fixture.nativeElement.querySelector('.fangkorb-fehler p').textContent).not.toContain('versucht es weiter');

        klicken(fehlerknopf());
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);
        expect(karten().length).toBe(1);
      }));

      for (const [anlass, ausloesen] of [
        ['das Netz zurueckkommt', () => window.dispatchEvent(new Event('online'))],
        ['der Tab wieder sichtbar wird', () => document.dispatchEvent(new Event('visibilitychange'))],
      ] as const) {
        it(`versucht es sofort, wenn ${anlass}`, fakeAsync(() => {
          scheitertErstDann('fehler', jeTab());

          ausloesen();
          fixture.detectChanges();

          expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);
          expect(karten().length).toBe(1);
          // Der geplante Versuch faellt weg
          tick(WIEDERHOLUNG_MS[WIEDERHOLUNG_MS.length - 1]);
          expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);
        }));
      }

      it('gibt eine haengende Anfrage nach LADE_TIMEOUT_MS auf und versucht es weiter', fakeAsync(() => {
        einwurfService.fangkorbLaden.and.returnValues(NEVER, of(antwort(jeTab())));
        fixture = TestBed.createComponent(FangkorbComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
        expect(component.isLoading).toBeTrue();

        tick(LADE_TIMEOUT_MS);
        fixture.detectChanges();
        expect(component.ladefehler).toBeTrue();
        expect(component.versuchtWeiter).toBeTrue();

        tick(WIEDERHOLUNG_MS[0]);
        fixture.detectChanges();
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);
        expect(karten().length).toBe(1);
      }));

      it('zeigt nach einem Fehler ohne geladene Einwuerfe einen Strich statt 0', () => {
        scheitertErstDann('fehler');

        expect(zaehler('Destillieren')).toBe('–');
        expect(zaehler('Ausformulieren')).toBe('–');
      });

      it('beachtet nur die neueste Anfrage und plant nach Erfolg nichts mehr', fakeAsync(() => {
        const erster = new Subject<ReturnType<typeof antwort>>();
        const zweiter = new Subject<ReturnType<typeof antwort>>();
        einwurfService.fangkorbLaden.and.returnValues(throwError(() => ({ status: 503 })), erster, zweiter);
        fixture = TestBed.createComponent(FangkorbComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();

        klicken(fehlerknopf()); // Versuch A laeuft
        component.laden(); // z. B. nach dem Verwerfen: Versuch B
        zweiter.next(antwort(jeTab()));
        erster.error({ status: 503 }); // A scheitert spaet: darf nichts mehr planen
        fixture.detectChanges();

        expect(component.ladefehler).toBeFalse();
        tick(WIEDERHOLUNG_MS[WIEDERHOLUNG_MS.length - 1] * 2);
        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(3);
        expect(karten().length).toBe(1);
      }));

      it('laedt bei online ohne offenen Fehler nicht nach', () => {
        erstellen(jeTab());

        window.dispatchEvent(new Event('online'));

        expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(1);
      });
    });

    it('sagt dazu, dass nur die letzten Einwuerfe geladen sind und die Zaehler nur die meinen', () => {
      erstellen([einwurf()], 150);
      const hinweis: string = fixture.nativeElement.querySelector('.fangkorb-mehr').textContent;

      expect(hinweis).toContain('Von 150 Einwürfen sind die letzten 1 geladen');
      expect(hinweis).toContain('ältere fehlen');
      expect(hinweis).toContain('Zähler oben zählen nur die geladenen');
    });

    it('sagt, wenn der Fangkorb leer ist', () => {
      erstellen([]);

      expect(fixture.nativeElement.textContent).toContain('Noch nichts drin');
    });
  });

  describe('Karte', () => {
    it('zeigt Plattform und Link-Icon im Kopf, den Hinweis als Titel, Alter und Knopf im Fuss', () => {
      erstellen([
        einwurf({
          url: 'https://www.instagram.com/reel/ABC/',
          content: 'Gute Antwort in den Kommentaren',
        }),
      ]);
      const [karte] = karten();

      const linkzeile = karte.querySelector<HTMLAnchorElement>('a.einwurf-linkzeile')!;
      expect(linkzeile.getAttribute('href')).toBe('https://www.instagram.com/reel/ABC/');
      expect(linkzeile.getAttribute('target')).toBe('_blank');
      expect(linkzeile.querySelector('.einwurf-herkunft')!.textContent!.trim()).toBe('Instagram');
      expect(linkzeile.querySelector('.einwurf-adresse')!.textContent!.trim()).toBe(
        'instagram.com/reel/ABC',
      );
      expect(linkzeile.textContent).not.toContain('https://');
      expect(karte.querySelector('.einwurf-titel')!.textContent!.trim()).toBe(
        'Gute Antwort in den Kommentaren',
      );
      expect(karte.querySelector('.einwurf-alter')!.textContent!.trim()).toBeTruthy();
      expect(karte.querySelector('.einwurf-primaer .knopf-wort')!.textContent!.trim()).toBe('Destillieren');
    });

    it('zeigt ohne Hinweis keinen Titel - dann traegt die Link-Zeile die Aufschrift', () => {
      erstellen([einwurf({ url: 'https://beispiel-zeitung.de/artikel/1', content: null })]);
      const [karte] = karten();

      expect(karte.querySelector('.einwurf-titel')).toBeNull();
      expect(karte.querySelector('.einwurf-herkunft')!.textContent!.trim()).toBe('beispiel-zeitung.de');
      expect(karte.querySelector('.einwurf-adresse')!.textContent!.trim()).toBe(
        'beispiel-zeitung.de/artikel/1',
      );
    });

    it('zeigt ohne Link keine Link-Zeile', () => {
      erstellen([einwurf({ url: null, content: 'nur ein Hinweis' })]);

      expect(karten()[0].querySelector('.einwurf-linkzeile')).toBeNull();
      expect(karten()[0].querySelector('.einwurf-titel')!.textContent!.trim()).toBe('nur ein Hinweis');
    });

    it('nennt den Einwerfer beim Anzeigenamen, ohne Namen "Mitglied", den eigenen Einwurf "Du"', () => {
      erstellen([
        einwurf({ id: 'fremd', ist_eigener_einwurf: false, submitted_by_name: 'Jürgen Ö.' }),
        einwurf({ id: 'ohne-name', ist_eigener_einwurf: false }),
      ]);
      const einwerfer = karten().map((karte) => karte.querySelector('.einwurf-einwerfer')!);
      expect(einwerfer.map((zeile) => zeile.textContent!.trim())).toEqual(['Von: Jürgen Ö.', 'Von: Mitglied']);
      // Die Kennung steht auch nicht im Tooltip.
      expect(einwerfer.every((zeile) => !zeile.hasAttribute('title'))).toBeTrue();

      fixture.destroy();
      erstellen([einwurf({ ist_eigener_einwurf: true })]);

      expect(karten()[0].querySelector('.einwurf-einwerfer')!.textContent!.trim()).toBe('Von: Du');

      fixture.destroy();
      erstellen([einwurf({ ist_eigener_einwurf: null })]);

      // Niemand Bekanntes hat eingeworfen: keine Zeile, auch kein "Mitglied".
      expect(karten()[0].querySelector('.einwurf-einwerfer')).toBeNull();
    });

    it('beschriftet den Primaerknopf nach Stufe und laesst ihn bei Verworfenem weg', () => {
      erstellen(jeTab());
      expect(karten()[0].querySelector('.einwurf-primaer .knopf-wort')!.textContent!.trim()).toBe('Destillieren');

      klicken(tabKnopf('Ausformulieren'));
      expect(karten()[0].querySelector('.einwurf-primaer .knopf-wort')!.textContent!.trim()).toBe('Ausformulieren');

      klicken(tabKnopf('Destillieren'));
      klicken(filterKnopf('verworfen'));
      const verworfen = karten().find((karte) => karte.classList.contains('stufe-verworfen'))!;
      expect(verworfen.querySelector('.einwurf-primaer')).toBeNull();
      expect(verworfen.querySelector('.einwurf-verworfen')!.textContent!.trim()).toBe('verworfen');
    });
  });

  describe('Saetze in der Karte', () => {
    it('zeigt hoechstens drei Saetze und zaehlt den Rest', () => {
      erstellen([
        einwurf({
          status: 'in_progress',
          drafts: ['a', 'b', 'c', 'd', 'e'].map((kennung, i) => satz(`s-${i}`, kennung, `Satz ${kennung}`)),
        }),
      ]);
      klicken(tabKnopf('Ausformulieren'));
      const [karte] = karten();

      expect(karte.querySelectorAll('.einwurf-satz').length).toBe(3);
      expect(karte.querySelector('.einwurf-mehr')!.textContent!.trim()).toBe('+2 weitere');
    });
  });

  describe('Griffe', () => {
    it('fuehrt Destillieren in die Destillier-Ansicht, an den Anfang', () => {
      erstellen(jeTab());

      klicken(karten()[0].querySelector<HTMLButtonElement>('.einwurf-primaer')!);

      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'roh']);
    });

    it('fuehrt Ausformulieren direkt in die Typwahl', () => {
      erstellen(jeTab());
      klicken(tabKnopf('Ausformulieren'));

      klicken(karten()[0].querySelector<HTMLButtonElement>('.einwurf-primaer')!);

      // Der Satz steht schon - dann beginnt das Ausformulieren bei der Typwahl.
      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'satz'], {
        queryParams: { schritt: 'typwahl' },
      });
    });

    it('bietet Mitwirkenden ohne Adminrechte Verwerfen nur am eigenen Einwurf', () => {
      erstellen([einwurf({ id: 'eigen' }), einwurf({ id: 'fremd', ist_eigener_einwurf: false })]);
      const [eigen, fremd] = kartenKomponenten();

      expect(eigen.menueEintraege.map((eintrag) => eintrag.wort)).toEqual(['Link kopieren', 'Verwerfen']);
      expect(fremd.menueEintraege.map((eintrag) => eintrag.wort)).toEqual(['Link kopieren']);
    });

    it('bietet Admins Verwerfen auch an fremden Einwuerfen', () => {
      nutzer = { ...nutzer, userId: 'admin', isAdmin: true };
      erstellen([
        einwurf({ id: 'fremd', submitted_by: 'bob', ist_eigener_einwurf: false }),
        einwurf({ id: 'verwaist', submitted_by: null, ist_eigener_einwurf: null }),
      ]);

      for (const karte of kartenKomponenten()) {
        expect(karte.menueEintraege.map((eintrag) => eintrag.wort)).toEqual(['Link kopieren', 'Verwerfen']);
      }
    });

    it('verwirft als Admin einen fremden Einwurf', () => {
      nutzer = { ...nutzer, userId: 'admin', isAdmin: true };
      erstellen([einwurf({ id: 'fremd', submitted_by: 'bob', ist_eigener_einwurf: false })]);
      einwurfService.updateStatus.and.returnValue(of(einwurf({ id: 'fremd', status: 'discarded' })));

      component.aktionAusfuehren(component.karten[0], 'verwerfen');

      expect(einwurfService.updateStatus).toHaveBeenCalledWith('fremd', 'discarded');
    });

    it('bietet bei Verworfenem Weiterarbeiten statt Verwerfen', () => {
      erstellen(jeTab());

      klicken(filterKnopf('verworfen'));
      const verworfen = kartenKomponenten().find((karte) => karte.daten.einwurfAngaben!.stufe === 'verworfen')!;

      expect(verworfen.menueEintraege.map((eintrag) => eintrag.wort)).toEqual([
        'Link kopieren',
        'Trotzdem destillieren',
      ]);
    });

    it('kopiert den Link und sagt es', () => {
      erstellen([einwurf({ url: 'https://example.org/post' })]);

      component.aktionAusfuehren(component.karten[0], 'linkKopieren');

      expect(clipboard.copy).toHaveBeenCalledWith('https://example.org/post');
      expect(snackBar.open).toHaveBeenCalledWith('Link kopiert.', undefined, { duration: 3000 });
    });

    it('verwirft und laedt die Liste neu', () => {
      erstellen([einwurf({ id: 'eigen' })]);
      einwurfService.updateStatus.and.returnValue(of(einwurf({ id: 'eigen', status: 'discarded' })));

      component.aktionAusfuehren(component.karten[0], 'verwerfen');

      expect(einwurfService.updateStatus).toHaveBeenCalledWith('eigen', 'discarded');
      expect(einwurfService.fangkorbLaden).toHaveBeenCalledTimes(2);
    });

    it('sagt es, wenn das Verwerfen scheitert', () => {
      erstellen([einwurf({ id: 'eigen' })]);
      einwurfService.updateStatus.and.returnValue(throwError(() => ({ status: 403 })));

      component.aktionAusfuehren(component.karten[0], 'verwerfen');

      expect(snackBar.open).toHaveBeenCalledWith(
        'Verwerfen können nur der Einwerfer und Admins.',
        'OK',
        { duration: 6000 },
      );
    });

    it('nennt bei 409 den wahren Grund statt "versuche es erneut"', () => {
      erstellen([einwurf({ id: 'eigen' })]);
      einwurfService.updateStatus.and.returnValue(throwError(() => ({ status: 409 })));

      component.aktionAusfuehren(component.karten[0], 'verwerfen');

      expect(snackBar.open).toHaveBeenCalledWith(
        'Zu diesem Einwurf gibt es schon einen Beitrag; Verwerfen geht nicht mehr.',
        'OK',
        { duration: 6000 },
      );
    });

    it('laesst Verworfenes ueber den Chip weiter destillieren', () => {
      erstellen(jeTab());
      klicken(filterKnopf('verworfen'));

      const verworfen = component.karten.find((karte) => karte.id === 'weg')!;
      component.aktionAusfuehren(verworfen, 'weiterDestillieren');

      expect(router.navigate).toHaveBeenCalledWith(['/destillieren', 'weg']);
    });
  });
});
