import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

import { ContributionsViewComponent } from './contributions-view.component';
import { ContributionsService } from '../services/contributions.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { BeitragSheetComponent } from '../beitragskarte/beitrag-sheet.component';

describe('ContributionsViewComponent', () => {
  let fixture: ComponentFixture<ContributionsViewComponent>;
  let router: Router;
  let bottomSheet: MatBottomSheet;

  function beitrag(felder: Record<string, unknown> = {}): any {
    return {
      id: 'b1',
      created: '2026-09-13T21:05:00',
      last_modified: '2026-09-13T21:05:00',
      original_author: 'person-1',
      last_modified_by: 'person-1',
      edit_history: {},
      text: 'Text der Hintergrundinfo',
      content_type: 'generic_text',
      title: 'Wärmepumpe lohnt sich auch im Altbau',
      usage_count: 12,
      score: 0,
      ...felder,
    };
  }

  function konfigurieren(getContributions: (seite: number, groesse: number) => Observable<any>, mobil = false): void {
    TestBed.configureTestingModule({
      imports: [ContributionsViewComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: BreakpointObserver, useValue: { observe: () => of({ matches: mobil, breakpoints: {} }) } },
        { provide: ContributionsService, useValue: { getContributions } },
        { provide: UsageTrackingService, useValue: { getUserUsageStats: () => of(null) } },
        { provide: AuthService, useValue: { getCurrentUserId: () => null } },
      ],
    });

    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    bottomSheet = TestBed.inject(MatBottomSheet);
    spyOn(bottomSheet, 'open');
  }

  async function erstellen(results: any[], mobil = false): Promise<void> {
    konfigurieren(
      () => of({ results_count: results.length, total_records_count: results.length, results }),
      mobil,
    );
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(ContributionsViewComponent);
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
    fixture = TestBed.createComponent(ContributionsViewComponent);

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
    expect(erste.querySelector('.album-fuss .badge-nutzung')!.textContent!.trim()).toBe('12×');
    expect(erste.getAttribute('aria-label')).toBe('Hintergrundinfo: Wärmepumpe lohnt sich auch im Altbau');
  });

  it('zeigt die Statistik als eine Textzeile, ohne Hinweisbox und Kacheln', async () => {
    await erstellen([beitrag(), beitrag({ id: 'b2', usage_count: 3 })]);

    expect(text('.album-statistik')).toBe('2 Beiträge · 15× genutzt');
    expect(fixture.nativeElement.querySelector('.info-message')).toBeNull();
    expect(fixture.nativeElement.querySelector('.stat-card')).toBeNull();
  });

  it('schreibt einen Beitrag im Singular und nimmt die Gesamtnutzung, wenn es sie gibt', async () => {
    await erstellen([beitrag()]);

    expect(text('.album-statistik')).toBe('1 Beitrag · 12× genutzt');

    fixture.componentInstance.userStats = {
      user_id: 'person-1',
      unique_contents_contributed: 1,
      total_usage_count: 40,
      top_content: [],
    };
    fixture.componentInstance.totalRecords = 25;
    expect(fixture.componentInstance.statistik).toBe('25 Beiträge · 40× genutzt');
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

  it('sagt, wenn es noch keine Beitraege gibt', async () => {
    await erstellen([]);

    expect(text('.beitraege-leer')).toBe('Du hast noch keine Beiträge.');
    expect(karten().length).toBe(0);
  });
});
