import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { SchalterComponent } from './schalter.component';
import { Schalter } from '../../services/moderation.service';
import { environment } from '../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/moderation/schalter`;

function schalter(teil: Partial<Schalter> & { name: string }): Schalter {
  return {
    erklaerung: 'Was er tut.',
    umgebungsvariable: 'SEMANTIC_SEARCH_X_AKTIV',
    obergrenze: true,
    admin_wert: false,
    wirksam: false,
    dsfa_hinweis: null,
    ...teil,
  };
}

const DSFA = 'Vor dem Einschalten auf Prod: DSFA beschlossen (docs/DSFA.md Abschnitt 7)';

describe('SchalterComponent', () => {
  let fixture: ComponentFixture<SchalterComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SchalterComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideNoopAnimations()],
    }).compileComponents();

    fixture = TestBed.createComponent(SchalterComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
    http.verify();
  });

  function karten(): HTMLElement[] {
    return Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('[data-testid="schalter"]'));
  }

  function knopf(karte: HTMLElement): HTMLButtonElement {
    return karte.querySelector('mat-slide-toggle button') as HTMLButtonElement;
  }

  function laden(liste: Schalter[]): void {
    http.expectOne(URL).flush({ schalter: liste });
    fixture.detectChanges();
  }

  it('zeigt je Schalter Name, Erklärung, Obergrenze und den DSFA-Hinweis', () => {
    laden([
      schalter({ name: 'punkte', dsfa_hinweis: DSFA }),
      schalter({ name: 'gepostet', obergrenze: false }),
    ]);

    const [punkte, gepostet] = karten();
    expect(punkte.textContent).toContain('Punkte und Meilensteine');
    expect(punkte.textContent).toContain('Was er tut.');
    expect(punkte.textContent).toContain('Server erlaubt: ja');
    expect(punkte.querySelector('[data-testid="dsfa-hinweis"]')!.textContent).toContain('DSFA beschlossen');
    expect(knopf(punkte).disabled).toBeFalse();

    expect(gepostet.textContent).toContain('Server erlaubt: nein');
    expect(gepostet.querySelector('[data-testid="gesperrt"]')).not.toBeNull();
    expect(gepostet.querySelector('[data-testid="dsfa-hinweis"]')).toBeNull();
    expect(knopf(gepostet).disabled).toBeTrue();
  });

  it('setzt beim Umschalten den Admin-Wert und zeigt den neuen Stand ohne Neuladen', () => {
    laden([schalter({ name: 'punkte' })]);

    knopf(karten()[0]).click();
    fixture.detectChanges();

    const anfrage = http.expectOne(`${URL}/punkte`);
    expect(anfrage.request.method).toBe('PUT');
    expect(anfrage.request.body).toEqual({ an: true });
    anfrage.flush({ schalter: [schalter({ name: 'punkte', admin_wert: true, wirksam: true })] });
    fixture.detectChanges();

    expect(karten()[0].textContent).toContain('Wirkt');
    expect(knopf(karten()[0]).getAttribute('aria-checked')).toBe('true');
  });

  it('nimmt den Umschalter bei 409 zurück und zeigt die Erklärung', () => {
    laden([schalter({ name: 'gepostet' })]);

    knopf(karten()[0]).click();
    fixture.detectChanges();
    http
      .expectOne(`${URL}/gepostet`)
      .flush({ detail: 'Der Server erlaubt diesen Schalter nicht.' }, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();

    expect(knopf(karten()[0]).getAttribute('aria-checked')).toBe('false');
    expect(document.body.textContent).toContain('Der Server erlaubt diesen Schalter nicht.');
  });
});
