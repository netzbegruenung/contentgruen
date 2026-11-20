import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { SearchViewComponent } from './search-view.component';
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

  it('stellt unter Titel und Untertitel das Such-Band mit Suchfeld, ohne Erklaer- und Beispielzeile', () => {
    const hero: HTMLElement = fixture.nativeElement.querySelector('.start-hero');
    const band: HTMLElement = fixture.nativeElement.querySelector('.such-band');

    expect(hero.querySelector('.hero-title')).toBeTruthy();
    expect(hero.nextElementSibling).toBe(band);
    expect(band.querySelector('.such-band-inhalt')!.firstElementChild!.tagName.toLowerCase()).toBe('app-search');
    expect(band.textContent).not.toContain('Antwort finden – verwenden');
    // Designrunde 17.11.: Statt „Beispiel probieren“ tippt das Feld Hot Takes vor
    expect(band.textContent).not.toContain('Beispiel probieren');
  });

  it('stellt Willkommen und "Seit deinem letzten Besuch" unter das Suchfeld (Nutzerfuehrung 13.11.)', () => {
    const band: HTMLElement = fixture.nativeElement.querySelector('.such-band');
    const willkommen = band.nextElementSibling as HTMLElement;

    expect(willkommen.tagName.toLowerCase()).toBe('app-rundgang-band');
    expect(willkommen.nextElementSibling!.tagName.toLowerCase()).toBe('app-seit-letztem-besuch');
  });

  // Persona-Runde 18.11.: Der Weg ohne Konto (Community-Karten) kommt vor den Kacheln
  it('stellt die Kacheln unter "Frisch aus der Community"', () => {
    const community: HTMLElement = fixture.nativeElement.querySelector('app-recent-content');

    expect(community.nextElementSibling!.classList).toContain('start-kacheln');
  });

  it('laesst nur das Suchfeld auf dem Start Hot Takes vortippen (Designrunde 17.11.)', () => {
    const suche = fixture.debugElement.query(By.css('.such-band app-search')).componentInstance as SearchComponent;

    expect(suche.beispielAnimation).toBeTrue();
  });

  it('fuehrt mit zwei Kacheln zum Einwerfen und zum Verfassen', () => {
    const kacheln: HTMLAnchorElement[] = Array.from(
      fixture.nativeElement.querySelectorAll('a.start-kachel'),
    );

    expect(kacheln.map((kachel) => kachel.getAttribute('href'))).toEqual(['/einwerfen', '/contribute']);
  });

  // Persona-Runde 18.11.: je ein kurzer Halbsatz sichtbar unter dem Titel
  it('zeigt an den Kacheln Titel und einen kurzen erklaerenden Halbsatz', () => {
    const kacheln: HTMLAnchorElement[] = Array.from(
      fixture.nativeElement.querySelectorAll('a.start-kachel'),
    );

    expect(kacheln.map((kachel) => kachel.querySelector('.kachel-titel')!.textContent!.trim())).toEqual(['Einwerfen', 'Beitragen']);
    const saetze = kacheln.map((kachel) => kachel.querySelector('.kachel-satz') as HTMLElement);
    expect(saetze.map((satz) => satz.textContent!.trim())).toEqual(['Spruch oder Fundstück schicken', 'Eigene Antwort schreiben']);
    saetze.forEach((satz) => expect(satz.hidden).toBeFalse());
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

describe('SearchViewComponent mit Anker #recent-content', () => {
  it('setzt nach dem Sprung den Fokus auf „Frisch aus der Community“ (WCAG 2.4.3, 20.11.)', fakeAsync(() => {
    TestBed.configureTestingModule({
      providers: [
        provideAnimations(),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { params: of({}), queryParams: of({}), fragment: of('recent-content'), snapshot: { params: {}, queryParams: {} } },
        },
      ],
      imports: [SearchViewComponent],
    });
    const fixture = TestBed.createComponent(SearchViewComponent);
    fixture.detectChanges();
    const ueberschrift: HTMLElement = fixture.nativeElement.querySelector('#recent-content h2');

    tick(100);

    expect(ueberschrift.getAttribute('tabindex')).toBe('-1');
    expect(document.activeElement).toBe(ueberschrift);
  }));
});
