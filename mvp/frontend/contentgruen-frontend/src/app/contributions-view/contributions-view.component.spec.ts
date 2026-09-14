import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';

import { ContributionsViewComponent } from './contributions-view.component';
import { ContributionsService } from '../services/contributions.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';

describe('ContributionsViewComponent', () => {
  let fixture: ComponentFixture<ContributionsViewComponent>;
  let router: Router;

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

  async function erstellen(results: any[]): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [ContributionsViewComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        {
          provide: ContributionsService,
          useValue: {
            getContributions: () =>
              of({ results_count: results.length, total_records_count: results.length, results }),
          },
        },
        { provide: UsageTrackingService, useValue: { getUserUsageStats: () => of(null) } },
        { provide: AuthService, useValue: { getCurrentUserId: () => null } },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
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
    await erstellen([beitrag()]);

    expect(text('.mat-mdc-paginator-page-size-label')).toBe('Einträge pro Seite:');
    expect(text('.mat-mdc-paginator-range-label')).toBe('1 – 1 von 1');
  });

  it('zeigt Beitraege als kompakte Karten mit Typfarbe, Titel, Nutzung und Datum', async () => {
    await erstellen([beitrag(), beitrag({ id: 'b2', content_type: 'commentary', title: 'Zweiter' })]);
    const [erste, zweite] = karten();

    expect(karten().length).toBe(2);
    expect(fixture.nativeElement.querySelector('table')).toBeNull();
    expect(erste.classList).toContain('karte--kompakt');
    expect(erste.classList).toContain('typ-generictext');
    expect(zweite.classList).toContain('typ-commentary');
    expect(erste.querySelector('.karte-titel')!.textContent).toContain('Wärmepumpe lohnt sich auch im Altbau');
    expect(erste.querySelector('.badge-nutzung')!.textContent!.trim()).toBe('12x');
    expect(erste.querySelector('.karte-datum')!.textContent!.trim()).toBe('13.09.2026');
    expect(erste.getAttribute('aria-label')).toBe('Hintergrundinfo: Wärmepumpe lohnt sich auch im Altbau');
  });

  it('zeigt kompakt keinen Text, keine Autorzeile und keine Aktionen', async () => {
    await erstellen([beitrag()]);
    const [karte] = karten();

    expect(karte.querySelector('.karte-text')).toBeNull();
    expect(karte.querySelector('.karte-meta')).toBeNull();
    expect(karte.querySelector('app-karten-aktionen')).toBeNull();
    expect(karte.querySelector('.badge-neu')).toBeNull();
  });

  it('oeffnet beim Tippen die Suche mit dem Titel', async () => {
    await erstellen([beitrag()]);

    karten()[0].click();

    expect(router.navigate).toHaveBeenCalledOnceWith(['/result'], {
      queryParams: { searchQuery: 'Wärmepumpe lohnt sich auch im Altbau' },
    });
  });

  it('sucht ohne Titel mit dem Text und oeffnet auch mit Enter', async () => {
    await erstellen([beitrag({ title: null })]);
    const [karte] = karten();

    karte.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));

    expect(karte.querySelector('.karte-titel')!.textContent).toContain('Text der Hintergrundinfo');
    expect(router.navigate).toHaveBeenCalledOnceWith(['/result'], {
      queryParams: { searchQuery: 'Text der Hintergrundinfo' },
    });
  });

  it('sagt, wenn es noch keine Beitraege gibt', async () => {
    await erstellen([]);

    expect(text('.beitraege-leer')).toBe('Du hast noch keine Beiträge.');
    expect(karten().length).toBe(0);
  });
});
