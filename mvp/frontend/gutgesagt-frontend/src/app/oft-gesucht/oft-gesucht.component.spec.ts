import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';

import { OftGesuchtComponent, aussagenAuswaehlen } from './oft-gesucht.component';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { BeitragAnsicht, ContentService } from '../services/content.service';
import { routes } from '../app.routes';
import { ohneWaechter } from '../testing/routen-ohne-waechter';

/** "Oft gesucht" ohne Treffer (#642, R51). */
describe('OftGesuchtComponent', () => {
  let fixture: ComponentFixture<OftGesuchtComponent>;
  let usage: jasmine.SpyObj<UsageTrackingService>;
  let content: jasmine.SpyObj<ContentService>;
  let router: Router;

  /** Beitrag-ID -> Aussage, auf die er antwortet; null = keine. */
  let aussageJeBeitrag: Record<string, { id: string; text: string } | null | 'fehler'>;

  function erstellen(oft: Observable<{ results: any[] }>, neueste: any[] = []): HTMLElement {
    usage.getOftGenutzt.and.returnValue(oft);
    content.getRecentContent.and.returnValue(of({ results_count: neueste.length, results: neueste }));
    content.beitragLaden.and.callFake((id: string) => {
      const aussage = aussageJeBeitrag[id];
      return aussage === 'fehler' ? throwError(() => new Error('404')) : of({ id, aussage } as unknown as BeitragAnsicht);
    });
    fixture = TestBed.createComponent(OftGesuchtComponent);
    fixture.componentRef.setInput('suchtext', 'tempolimit bringt nichts');
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  const aussagen = (seite: HTMLElement) =>
    Array.from(seite.querySelectorAll('.oft-gesucht-aussage')).map((a) => a.textContent!.trim());

  beforeEach(() => {
    usage = jasmine.createSpyObj('UsageTrackingService', ['getOftGenutzt']);
    content = jasmine.createSpyObj('ContentService', ['getRecentContent', 'beitragLaden']);
    aussageJeBeitrag = {
      'k-1': { id: 'a-1', text: 'Windräder töten die Vögel!' },
      'k-2': { id: 'a-1', text: 'Windräder töten die Vögel!' },
      'k-3': { id: 'a-2', text: 'Wärmepumpen sind zu teuer' },
      'k-4': null,
      'k-5': 'fehler',
      'k-6': { id: 'a-3', text: 'Tempolimit bringt nichts' },
      'k-7': { id: 'a-4', text: 'Atomkraft ist günstig' },
      'k-8': { id: 'a-5', text: 'Das Heizungsgesetz enteignet uns' },
    };
    TestBed.configureTestingModule({
      imports: [OftGesuchtComponent],
      providers: [
        provideRouter(ohneWaechter(routes)),
        { provide: UsageTrackingService, useValue: usage },
        { provide: ContentService, useValue: content },
      ],
    });
    router = TestBed.inject(Router);
  });

  it('zeigt bis zu drei Aussagen der oft genutzten Beitraege, jede einmal, ohne die eigene Suche', () => {
    const ids = ['k-1', 'k-2', 'k-4', 'k-5', 'k-6', 'k-3', 'k-7', 'k-8'];
    const seite = erstellen(of({ results: ids.map((id) => ({ id })) }));

    expect(seite.querySelector('.oft-gesucht-titel')?.textContent?.trim()).toBe('Oft gesucht');
    // Nur die ersten sechs Beitraege werden nachgeladen; k-6 ist die eigene Suche.
    expect(aussagen(seite)).toEqual(['„Windräder töten die Vögel!“', '„Wärmepumpen sind zu teuer“']);
    expect(content.beitragLaden).toHaveBeenCalledTimes(6);
    expect(content.getRecentContent).not.toHaveBeenCalled();
  });

  it('nimmt ohne oft Genutztes die neuesten Beitraege, mit passendem Titel', () => {
    const seite = erstellen(of({ results: [] }), [{ id: 'k-3' }, { id: 'k-7' }]);

    expect(seite.querySelector('.oft-gesucht-titel')?.textContent?.trim()).toBe('Zuletzt beantwortet');
    expect(aussagen(seite)).toEqual(['„Wärmepumpen sind zu teuer“', '„Atomkraft ist günstig“']);
  });

  it('zeigt ohne Aussagen nur den Link "Hier fehlt eine Antwort"', () => {
    const seite = erstellen(of({ results: [{ id: 'k-4' }] }), [{ id: 'k-5' }]);

    expect(seite.querySelector('.oft-gesucht-titel')).toBeNull();
    expect(seite.querySelector('.oft-gesucht-liste')).toBeNull();
    expect(seite.querySelector('.hier-fehlt-link')?.textContent?.trim()).toBe('Hier fehlt eine Antwort');
  });

  it('bleibt bei einem Fehler der Liste beim Link', () => {
    const seite = erstellen(throwError(() => new Error('500')));
    expect(seite.querySelector('.hier-fehlt-link')).toBeTruthy();
  });

  it('sucht mit einem Klick nach der Aussage', fakeAsync(() => {
    const seite = erstellen(of({ results: [{ id: 'k-3' }] }));
    seite.querySelector<HTMLAnchorElement>('.oft-gesucht-aussage')!.click();
    tick();
    expect(router.url).toBe('/result?searchQuery=W%C3%A4rmepumpen%20sind%20zu%20teuer');
  }));

  it('fuehrt mit "Hier fehlt eine Antwort" auf die Seite dazu', fakeAsync(() => {
    const seite = erstellen(of({ results: [] }));
    seite.querySelector<HTMLAnchorElement>('.hier-fehlt-link')!.click();
    tick();
    expect(router.url).toBe('/hier-fehlt-eine-antwort');
  }));
});

describe('aussagenAuswaehlen', () => {
  it('nimmt hoechstens drei, ohne Doppelte und ohne die Suche, Schreibweise egal', () => {
    const a = (text: string) => ({ id: text, text });
    expect(
      aussagenAuswaehlen([a('Eins'), null, a(' eins '), a('Suche'), a('Zwei'), a('Drei'), a('Vier')], 'suche'),
    ).toEqual([a('Eins'), a('Zwei'), a('Drei')]);
  });
});
