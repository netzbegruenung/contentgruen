import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { SearchViewComponent } from './search-view.component';
import { FANGKORB_KURZ } from '../shared/fangkorb-texte';

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

  it('zeigt den Markennamen als Zeile ueber der Ueberschrift, ohne Gedankenstrich', () => {
    const hero: HTMLElement = fixture.nativeElement.querySelector('.start-hero');

    expect(hero.querySelector('.hero-eyebrow')!.textContent!.trim()).toBe('Gut gesagt');
    expect(hero.querySelector('.hero-eyebrow')!.nextElementSibling).toBe(hero.querySelector('.hero-title'));
    expect(hero.querySelector('.hero-title')!.textContent!.trim()).toBe('Nie wieder sprachlos');
  });

  it('stellt unter Titel und Untertitel das Such-Band mit Erklaerzeile, Suchfeld und Beispiel', () => {
    const hero: HTMLElement = fixture.nativeElement.querySelector('.start-hero');
    const band: HTMLElement = fixture.nativeElement.querySelector('.such-band');

    expect(hero.querySelector('.hero-title')).toBeTruthy();
    expect(hero.nextElementSibling).toBe(band);
    expect(band.querySelector('.such-erklaerung')!.textContent).toContain('Post reinkopieren – Antwort finden – Verwenden!');
    expect(band.querySelector('app-search')).toBeTruthy();
    expect(band.textContent).toContain('Beispiel probieren');
  });

  it('fuehrt mit zwei Kacheln zum Einwerfen und zum Verfassen', () => {
    const kacheln: HTMLAnchorElement[] = Array.from(
      fixture.nativeElement.querySelectorAll('a.start-kachel'),
    );

    expect(kacheln.map((kachel) => kachel.getAttribute('href'))).toEqual(['/einwerfen', '/contribute']);
    expect(kacheln[0].textContent).toContain(FANGKORB_KURZ);
  });

  it('zeigt keine Statistik-Kacheln und fragt keine Metriken ab', () => {
    const http = TestBed.inject(HttpTestingController);

    expect(fixture.nativeElement.querySelector('.metric-card')).toBeNull();
    expect(http.match((anfrage) => anfrage.url.includes('metrics')).length).toBe(0);
  });
});
