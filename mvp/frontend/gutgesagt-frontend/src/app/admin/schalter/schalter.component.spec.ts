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

    expect(karten()[0].textContent).toContain('Admin: an · wirksam: an');
    expect(knopf(karten()[0]).getAttribute('aria-checked')).toBe('true');
  });

  it('nennt dem Screenreader den Schalter und beschreibt den Zustand', () => {
    laden([schalter({ name: 'punkte', admin_wert: true, wirksam: true })]);

    const karte = karten()[0];
    const button = knopf(karte);
    expect(button.getAttribute('aria-label')).toBe('Punkte und Meilensteine, Admin');
    // Sichtbarer Text des Umschalters steckt im Namen (WCAG 2.5.3)
    expect(karte.querySelector('mat-slide-toggle')!.textContent!.trim()).toBe('Admin');
    const beschreibung = button.getAttribute('aria-describedby')!.split(' ');
    const zustand = karte.querySelector('[data-testid="zustand"]') as HTMLElement;
    expect(beschreibung).toContain(zustand.id);
    expect(zustand.textContent).toContain('wirksam: an');
  });

  it('erklärt, warum ein eingeschalteter Admin-Wert nicht wirkt', () => {
    laden([
      schalter({ name: 'punkte', admin_wert: false, wirksam: false }),
      schalter({ name: 'abzeichen_sichtbar', admin_wert: true, wirksam: false }),
      schalter({ name: 'gepostet', obergrenze: false, admin_wert: true, wirksam: false }),
    ]);

    const [punkte, abzeichen, gepostet] = karten().map(
      (k) => (k.querySelector('[data-testid="zustand"]') as HTMLElement).textContent!.trim(),
    );
    expect(punkte).toBe('Admin: aus · wirksam: aus');
    expect(abzeichen).toBe('Admin: an · wirksam: aus, weil Punkte aus');
    expect(gepostet).toBe('Admin: an · wirksam: aus (Server erlaubt nicht)');
    expect(knopf(karten()[2]).getAttribute('aria-checked')).toBe('true');
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
