import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { SearchViewComponent } from './search-view.component';
import { FANGKORB_KURZ } from '../shared/fangkorb-texte';
import { STARTBEISPIEL } from '../shared/startbeispiel';
import { NavigationService } from '../services/navigation.service';
import { AuthService } from '../auth/auth.service';
import { SearchComponent } from '../search/search.component';
import { By } from '@angular/platform-browser';

describe('SearchViewComponent', () => {
  let component: SearchViewComponent;
  let fixture: ComponentFixture<SearchViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideAnimations(),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({}),
            queryParams: of({}),
            fragment: of(null),
            snapshot: {
              params: {},
              queryParams: {}
            }
          }
        }
      ],
      imports: [SearchViewComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SearchViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Startseite 16.11.: ohne Markenzeile darueber, das Logo im Kopf nennt den Namen
  it('zeigt Ueberschrift und Untertitel ohne Markenzeile darueber', () => {
    const hero: HTMLElement = fixture.nativeElement.querySelector('.start-hero');

    expect(hero.firstElementChild).toBe(hero.querySelector('.hero-title'));
    expect(hero.querySelector('.hero-title')!.textContent!.trim()).toBe('Nie wieder sprachlos');
    expect(hero.querySelector('.hero-subtitle')!.textContent!.trim()).toBe('Bewährte Argumente aus der Community.');
    expect(hero.textContent).not.toContain('Gut gesagt');
  });

  it('stellt unter Titel und Untertitel das Such-Band mit Suchfeld und Beispiel, ohne Erklaerzeile', () => {
    const hero: HTMLElement = fixture.nativeElement.querySelector('.start-hero');
    const band: HTMLElement = fixture.nativeElement.querySelector('.such-band');

    expect(hero.querySelector('.hero-title')).toBeTruthy();
    expect(hero.nextElementSibling).toBe(band);
    expect(band.querySelector('.such-band-inhalt')!.firstElementChild!.tagName.toLowerCase()).toBe('app-search');
    expect(band.textContent).not.toContain('Antwort finden – verwenden');
    expect(band.textContent).toContain('Beispiel probieren');
  });

  it('stellt Willkommen und "Seit deinem letzten Besuch" unter das Suchfeld, vor die Kacheln (Nutzerfuehrung 13.11.)', () => {
    const band: HTMLElement = fixture.nativeElement.querySelector('.such-band');
    const willkommen = band.nextElementSibling as HTMLElement;

    expect(willkommen.tagName.toLowerCase()).toBe('app-rundgang-band');
    expect(willkommen.nextElementSibling!.tagName.toLowerCase()).toBe('app-seit-letztem-besuch');
    expect(willkommen.nextElementSibling!.nextElementSibling!.classList).toContain('start-kacheln');
  });

  it('zeigt als Beispiel das Startbeispiel und sucht genau danach (#601)', () => {
    const navigation = TestBed.inject(NavigationService);
    spyOn(navigation, 'navigateToResult');
    const link: HTMLElement = fixture.nativeElement.querySelector('.beispiel-link');

    expect(link.textContent!.trim()).toBe(`„${STARTBEISPIEL}“`);
    link.click();
    expect(navigation.navigateToResult).toHaveBeenCalledWith(STARTBEISPIEL);
  });

  it('fuehrt mit zwei Kacheln zum Einwerfen und zum Verfassen', () => {
    const kacheln: HTMLAnchorElement[] = Array.from(
      fixture.nativeElement.querySelectorAll('a.start-kachel'),
    );

    expect(kacheln.map((kachel) => kachel.getAttribute('href'))).toEqual(['/einwerfen', '/contribute']);
  });

  // Startseite 16.11.: Der Satz steht nicht mehr sichtbar da, bleibt aber Beschreibung der Kachel
  it('zeigt an den Kacheln nur den Titel und liest den Satz als Beschreibung vor', () => {
    const kacheln: HTMLAnchorElement[] = Array.from(
      fixture.nativeElement.querySelectorAll('a.start-kachel'),
    );

    const saetze = kacheln.map((kachel) => {
      const satz = fixture.nativeElement.querySelector(`#${kachel.getAttribute('aria-describedby')}`) as HTMLElement;
      expect(kachel.contains(satz)).toBe(true);
      expect(satz.hidden).toBe(true);
      expect(satz.getBoundingClientRect().height).toBe(0);
      return satz.textContent!.trim();
    });
    expect(saetze[0]).toBe(FANGKORB_KURZ);
    expect(saetze[1]).toBe('Ausgearbeitet und direkt verwendbar: Kommentar, Hintergrundinfo oder Bild.');
  });

  // R57 (#644): Anonym fuehrten die Kacheln kommentarlos auf die Anmeldung
  describe('Hinweis "mit Konto" an den Kacheln', () => {
    function hinweise(): string[] {
      return Array.from(fixture.nativeElement.querySelectorAll('.start-kachel .kachel-konto')).map(
        (e) => (e as HTMLElement).textContent!.trim(),
      );
    }

    it('steht anonym an beiden Kacheln', () => {
      TestBed.inject(AuthService).setUserInfo({ isAuthenticated: false, userId: null, userName: null, claims: null });
      fixture.detectChanges();
      expect(hinweise()).toEqual(['mit Konto', 'mit Konto']);
      // Im zugaenglichen Namen getrennt vom Titel, nicht "Einwerfenmit Konto"
      const titel = fixture.nativeElement.querySelector('.start-kachel .kachel-titel') as HTMLElement;
      expect(titel.textContent!.replace(/\s+/g, ' ').trim()).toBe('Einwerfen mit Konto');
    });

    it('fehlt angemeldet und solange die Anmeldung noch nicht geklaert ist', () => {
      expect(hinweise()).toEqual([]);
      TestBed.inject(AuthService).setUserInfo({ isAuthenticated: true, userId: 'u1', userName: 'Kim', claims: null });
      fixture.detectChanges();
      expect(hinweise()).toEqual([]);
    });
  });

  // R55 (#644): Ziel des Skip-Links und Autofokus nur am Desktop mit Maus
  it('gibt dem Suchfeld das Ziel des Skip-Links und den Autofokus nur passend zum Geraet', () => {
    const suche = fixture.debugElement.query(By.directive(SearchComponent)).componentInstance as SearchComponent;
    expect(suche.feldId).toBe('suche');
    expect(suche.autofokus).toBe(window.matchMedia('(min-width: 960px) and (hover: hover) and (pointer: fine)').matches);
  });

  it('zeigt keine Statistik-Kacheln und fragt keine Metriken ab', () => {
    const http = TestBed.inject(HttpTestingController);

    expect(fixture.nativeElement.querySelector('.metric-card')).toBeNull();
    expect(http.match((anfrage) => anfrage.url.includes('metrics')).length).toBe(0);
  });
});
