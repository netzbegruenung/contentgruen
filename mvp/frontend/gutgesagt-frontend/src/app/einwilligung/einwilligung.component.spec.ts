import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Subject, of } from 'rxjs';
import { EinwilligungComponent, WIDERRUF_FRAGE } from './einwilligung.component';
import { Art9EinwilligungService, Art9EinwilligungStand } from '../services/art9-einwilligung.service';
import { environment } from '../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/art9-einwilligung`;
const WORTLAUT = { kennung: '2026-11-05', text: 'Ich willige ausdrücklich ein, dass …' };

function stand(teil: Partial<Art9EinwilligungStand> = {}): Art9EinwilligungStand {
  return {
    eingewilligt: false,
    wortlaut: null,
    eingewilligt_am: null,
    widerrufen_am: null,
    aktueller_wortlaut: WORTLAUT,
    ...teil,
  };
}

/** Die Art.-9-Einwilligung (#489): eigenes Haekchen, nichts vorbelegt, widerrufbar. */
describe('EinwilligungComponent', () => {
  let fixture: ComponentFixture<EinwilligungComponent>;
  let http: HttpTestingController;
  let router: Router;
  let dialog: jasmine.SpyObj<MatDialog>;
  /** Was die Rueckfrage vor dem Widerruf antwortet (B3). */
  let rueckfrage: boolean | undefined;

  function starten(returnUrl: string | null = '/einwerfen') {
    rueckfrage = true;
    dialog = jasmine.createSpyObj('MatDialog', ['open']);
    dialog.open.and.callFake((() => ({ afterClosed: () => of(rueckfrage) })) as any);
    TestBed.configureTestingModule({
      imports: [EinwilligungComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(returnUrl ? { returnUrl } : {}) } },
        },
      ],
    });
    TestBed.overrideProvider(MatDialog, { useValue: dialog });
    fixture = TestBed.createComponent(EinwilligungComponent);
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigateByUrl').and.resolveTo(true);
    fixture.detectChanges();
  }

  function standLiefern(s: Art9EinwilligungStand) {
    http.expectOne({ method: 'GET', url: URL }).flush(s);
    fixture.detectChanges();
  }

  function el(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function knopf(text: string): HTMLButtonElement {
    const treffer = Array.from(el().querySelectorAll('button')).find((b) => b.textContent?.includes(text));
    if (!treffer) {
      throw new Error(`Kein Knopf "${text}"`);
    }
    return treffer as HTMLButtonElement;
  }

  afterEach(() => {
    // "Ohne Einwilligung weiter" geht als POST an den Server (B2); nur der eigene Test prueft ihn.
    http.match({ method: 'POST', url: `${URL}/ohne` }).forEach((r) => r.flush(null, { status: 204, statusText: 'No Content' }));
    http.verify();
  });

  describe('Frage', () => {
    it('zeigt den Wortlaut vom Backend am Haekchen, nicht angehakt', () => {
      starten();
      standLiefern(stand());

      const haekchen = el().querySelector('mat-checkbox input[type=checkbox]') as HTMLInputElement;
      expect(el().querySelector('mat-checkbox')?.textContent).toContain(WORTLAUT.text);
      expect(haekchen.checked).toBeFalse();
      expect(knopf('Einwilligen und weiter').disabled).toBeTrue();
    });

    // #620: ein Satz am Haekchen, der ganze Wortlaut aufklappbar darunter, Text unveraendert
    it('zeigt am Haekchen den ersten Satz und den ganzen Wortlaut aufklappbar darunter', () => {
      const lang = {
        kennung: '2026-11-05-b',
        text: 'Ich willige ausdrücklich ein (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge. Ich kann widerrufen.',
      };
      starten();
      standLiefern(stand({ aktueller_wortlaut: lang }));

      expect(el().querySelector('mat-checkbox')!.textContent!.trim()).toBe(
        'Ich willige ausdrücklich ein (Art. 9 Abs. 2 lit. a DSGVO).',
      );
      const aufklapp = el().querySelector('details.wortlaut-aufklapp') as HTMLDetailsElement;
      expect(aufklapp.open).toBeFalse();
      expect(aufklapp.querySelector('summary')!.textContent!.trim()).toBe('Ganzen Wortlaut lesen');
      expect(aufklapp.querySelector('.wortlaut-voll')!.textContent!.trim()).toBe(lang.text);
      const eingabe = el().querySelector('mat-checkbox input[type=checkbox]') as HTMLInputElement;
      expect(eingabe.getAttribute('aria-describedby')).toBe('einwilligung-wortlaut-voll');
    });

    it('zeigt einen Wortlaut aus einem Satz ganz am Haekchen, ohne Aufklapper', () => {
      starten();
      standLiefern(stand());

      expect(el().querySelector('details.wortlaut-aufklapp')).toBeNull();
    });

    it('ohne Haekchen geht nichts ans Backend', () => {
      starten();
      standLiefern(stand());

      fixture.componentInstance.einwilligen();

      http.expectNone({ method: 'POST', url: URL });
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it('mit Haekchen schickt die Kennung des gezeigten Wortlauts und fuehrt zurueck', () => {
      starten('/einwerfen?von=fangkorb');
      standLiefern(stand());

      fixture.componentInstance.angehakt = true;
      fixture.detectChanges();
      knopf('Einwilligen und weiter').click();

      const anfrage = http.expectOne({ method: 'POST', url: URL });
      expect(anfrage.request.body).toEqual({ wortlaut: '2026-11-05' });
      anfrage.flush(null, { status: 204, statusText: 'No Content' });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen?von=fangkorb');
    });

    it('laedt bei einem veralteten Wortlaut (400) den aktuellen selbst und sagt es darueber', () => {
      starten();
      standLiefern(stand());
      fixture.componentInstance.angehakt = true;
      fixture.detectChanges();

      knopf('Einwilligen und weiter').click();
      http.expectOne({ method: 'POST', url: URL }).flush(null, { status: 400, statusText: 'Bad Request' });
      const neu = { kennung: '2026-11-13', text: 'Ich willige ausdrücklich ein, neu …' };
      standLiefern(stand({ aktueller_wortlaut: neu }));

      expect(el().querySelector('[data-testid="wortlaut-geaendert"]')?.textContent).toContain(
        'Der Text hat sich gerade geändert. Bitte lies ihn und stimm neu zu.',
      );
      expect(el().textContent).toContain(neu.text);
      expect(fixture.componentInstance.angehakt).toBeFalse();
      expect(el().textContent).not.toContain('Noch einmal');
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it('ohne Einwilligung weiter speichert nichts', () => {
      starten('/einwerfen');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      http.expectNone({ method: 'POST', url: URL });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen');
    });

    // UX-Review B2: wer bewusst ohne weitergeht, wird nicht bei jedem Start wieder hergefuehrt
    it('ohne Einwilligung weiter merkt sich die Entscheidung mit dem gezeigten Wortlaut', () => {
      starten('/einwerfen');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      // Am Konto, nicht im Browser (Entscheidung Maintainer 13.11.2026)
      const anfrage = http.expectOne({ method: 'POST', url: `${URL}/ohne` });
      expect(anfrage.request.body).toEqual({ wortlaut: WORTLAUT.kennung });
      anfrage.flush(null, { status: 204, statusText: 'No Content' });
      expect(router.navigateByUrl).toHaveBeenCalledWith('/einwerfen');
    });

    it('ohne Einwilligung öffnet sich die Hilfe danach nicht wieder (Parameter hilfe fällt weg)', () => {
      starten('/result?searchQuery=x&hilfe=1');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      expect(router.navigateByUrl).toHaveBeenCalledWith('/result?searchQuery=x');
    });

    it('mit Einwilligung bleibt der Parameter hilfe, die Hilfe öffnet sich danach', () => {
      starten('/search?hilfe=1');
      standLiefern(stand());

      fixture.componentInstance.angehakt = true;
      fixture.detectChanges();
      knopf('Einwilligen und weiter').click();
      http.expectOne({ method: 'POST', url: URL }).flush(null, { status: 204, statusText: 'No Content' });

      expect(router.navigateByUrl).toHaveBeenCalledWith('/search?hilfe=1');
    });

    it('fuehrt nur innerhalb der App zurueck', () => {
      starten('//fremd.example/');
      standLiefern(stand());

      knopf('Ohne Einwilligung weiter').click();

      expect(router.navigateByUrl).toHaveBeenCalledWith('/search');
    });
  });

  describe('Stand und Widerruf', () => {
    it('zeigt Zeitpunkt und Wortlaut der Einwilligung', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      expect(el().textContent).toContain('05.11.2026');
      expect(el().querySelector('.wortlaut')?.textContent).toContain(WORTLAUT.text);
      expect(el().querySelector('mat-checkbox')).toBeNull();
    });

    it('zeigt das Datum eines Wortlauts mit Suffix in der Kennung (2026-11-05-b)', () => {
      starten(null);
      const zweiter = { kennung: '2026-11-05-b', text: 'Dazu gehören ein Punktestand, ein Level, Quests und Meilenstein-Abzeichen …' };
      standLiefern(
        stand({
          eingewilligt: true,
          wortlaut: '2026-11-05-b',
          eingewilligt_am: '2026-11-06T09:30:00Z',
          aktueller_wortlaut: zweiter,
        }),
      );

      expect(el().textContent).toContain('Wortlaut vom 05.11.2026');
      expect(el().querySelector('.wortlaut')?.textContent).toContain(zweiter.text);
    });

    it('sagt vor dem Widerruf, was mit Beiträgen, Einwürfen und Sätzen geschieht (Löschauftrag)', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      const text = el().textContent!.replace(/\s+/g, ' ');
      expect(text).toContain('Innerhalb von sieben Tagen zeigen deine Beiträge dann „ehemalige Person“');
      expect(text).toContain('deine Einwürfe werden gelöscht');
      expect(text).toContain('Dein Konto bleibt.');
      expect(text).toContain('Was du nach einer neuen Einwilligung beiträgst, bleibt davon unberührt.');
      expect(text).not.toContain('bleibt, bis du es löschst');
    });

    // UX-Review B3: Rueckfrage mit den Folgen, bevor etwas geloescht wird
    it('fragt vor dem Widerruf nach und nennt die Folgen', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      knopf('Einwilligung widerrufen').click();

      expect(dialog.open).toHaveBeenCalledTimes(1);
      const daten = dialog.open.calls.mostRecent().args[1]!.data as typeof WIDERRUF_FRAGE;
      expect(daten.ja).toBe('Widerrufen');
      expect(daten.nein).toBe('Abbrechen');
      expect(daten.text).toContain('Bewertungen werden sofort gelöscht');
      expect(daten.text).toContain('sieben Tagen');
      http.expectOne({ method: 'DELETE', url: URL }).flush(null, { status: 204, statusText: 'No Content' });
      standLiefern(stand({ wortlaut: '2026-11-05', widerrufen_am: '2026-11-06T09:30:00Z' }));
    });

    it('oeffnet bei einem Doppelklick nur eine Rueckfrage', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));
      const offen = new Subject<boolean>();
      dialog.open.and.callFake((() => ({ afterClosed: () => offen.asObservable() })) as any);

      knopf('Einwilligung widerrufen').click();
      knopf('Einwilligung widerrufen').click();
      expect(dialog.open).toHaveBeenCalledTimes(1);

      offen.next(false);
      offen.complete();
      knopf('Einwilligung widerrufen').click();
      expect(dialog.open).toHaveBeenCalledTimes(2);
    });

    it('widerruft nach Abbrechen nicht', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));
      rueckfrage = false;

      knopf('Einwilligung widerrufen').click();
      fixture.detectChanges();

      http.expectNone({ method: 'DELETE', url: URL });
      expect(knopf('Einwilligung widerrufen').disabled).toBeFalse();
    });

    it('widerruft nicht, wenn die Rueckfrage ohne Antwort schliesst (Escape)', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));
      rueckfrage = undefined;

      knopf('Einwilligung widerrufen').click();

      http.expectNone({ method: 'DELETE', url: URL });
      expect(dialog.open).toHaveBeenCalledTimes(1);
    });

    it('widerrufen fragt danach erneut, ohne Haekchen', () => {
      starten(null);
      standLiefern(stand({ eingewilligt: true, wortlaut: '2026-11-05', eingewilligt_am: '2026-11-05T09:30:00Z' }));

      knopf('Einwilligung widerrufen').click();
      http.expectOne({ method: 'DELETE', url: URL }).flush(null, { status: 204, statusText: 'No Content' });
      standLiefern(stand({ wortlaut: '2026-11-05', widerrufen_am: '2026-11-06T09:30:00Z' }));

      expect(el().textContent).toContain('widerrufen');
      expect(fixture.componentInstance.angehakt).toBeFalse();
      expect(knopf('Einwilligen und weiter').disabled).toBeTrue();
    });

    it('zeigt einen frueheren Widerruf auch nach dem Neuladen', () => {
      starten(null);
      standLiefern(stand({ wortlaut: '2026-11-05', widerrufen_am: '2026-11-06T09:30:00Z' }));

      expect(el().querySelector('.hinweis')?.textContent).toContain('06.11.2026');
      expect(el().querySelector('mat-checkbox')).not.toBeNull();
    });

    it('zeigt beim ersten Mal keinen Hinweis auf einen Widerruf', () => {
      starten(null);
      standLiefern(stand());

      expect(el().querySelector('.hinweis')).toBeNull();
      expect(el().textContent).not.toContain('Frühere Einwilligung widerrufen');
    });

    // 2026-11-13: Nur der aktuelle Wortlaut zaehlt; eine fruehere Einwilligung fragt neu
    it('fragt neu, wer einem frueheren Wortlaut zugestimmt hat, und laesst ihn widerrufen', () => {
      starten(null);
      standLiefern(stand({ wortlaut: '2026-11-12', eingewilligt_am: '2026-11-12T09:30:00Z' }));

      expect(el().querySelector('mat-checkbox')).not.toBeNull();
      expect(el().querySelector('.hinweis')?.textContent).toContain('12.11.2026 einem früheren Wortlaut zugestimmt');

      knopf('Frühere Einwilligung widerrufen').click();
      fixture.detectChanges();
      // Waehrend des Widerrufs: weiter die Frage, gesperrt, nicht der Block fuer Eingewilligte
      expect(el().querySelector('mat-checkbox')).not.toBeNull();
      expect(el().textContent).not.toContain('Widerrufst du, kannst du nichts mehr beitragen');
      expect(knopf('Frühere Einwilligung widerrufen').disabled).toBeTrue();
      expect(knopf('Einwilligen und weiter').disabled).toBeTrue();
      http.expectOne({ method: 'DELETE', url: URL }).flush(null, { status: 204, statusText: 'No Content' });
      standLiefern(stand({ wortlaut: '2026-11-12', eingewilligt_am: '2026-11-12T09:30:00Z', widerrufen_am: '2026-11-13T09:30:00Z' }));

      expect(el().querySelector('.hinweis')?.textContent).toContain('13.11.2026 widerrufen');
      expect(el().textContent).not.toContain('Frühere Einwilligung widerrufen');
    });
  });

  it('zeigt einen Fehler, wenn der Stand nicht kommt', () => {
    starten();
    http.expectOne({ method: 'GET', url: URL }).flush(null, { status: 500, statusText: 'Fehler' });
    fixture.detectChanges();

    expect(el().querySelector('[role=alert]')).not.toBeNull();
  });
});
