import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MatDialogRef } from '@angular/material/dialog';
import { FeedbackDialogComponent } from './feedback-dialog.component';
import { environment } from '../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/feedback/senden`;

describe('FeedbackDialogComponent', () => {
  let fixture: ComponentFixture<FeedbackDialogComponent>;
  let http: HttpTestingController;
  let dialogRef: jasmine.SpyObj<MatDialogRef<FeedbackDialogComponent>>;

  beforeEach(async () => {
    dialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);
    await TestBed.configureTestingModule({
      imports: [FeedbackDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        { provide: MatDialogRef, useValue: dialogRef },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FeedbackDialogComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  function element(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  async function eingeben(selektor: string, wert: string) {
    const feld = element().querySelector(selektor) as HTMLInputElement | HTMLTextAreaElement;
    feld.value = wert;
    feld.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    await fixture.whenStable();
  }

  function sendenKnopf(): HTMLButtonElement {
    return element().querySelector('[data-testid="feedback-senden"]') as HTMLButtonElement;
  }

  it('sendet erst, wenn ein Text dasteht', async () => {
    expect(sendenKnopf().disabled).toBeTrue();

    await eingeben('textarea[name="text"]', '   ');
    expect(sendenKnopf().disabled).toBeTrue();

    await eingeben('textarea[name="text"]', 'Die Suche ist toll');
    expect(sendenKnopf().disabled).toBeFalse();
  });

  it('sendet Text und Kontakt und bedankt sich', async () => {
    await eingeben('textarea[name="text"]', 'Kopieren klappt mobil nicht');
    await eingeben('input[name="kontakt"]', 'anna@example.org');

    sendenKnopf().click();
    const anfrage = http.expectOne(URL);
    expect(anfrage.request.method).toBe('POST');
    expect(anfrage.request.body).toEqual({ text: 'Kopieren klappt mobil nicht', kontakt: 'anna@example.org' });
    anfrage.flush({ success: true }, { status: 201, statusText: 'Created' });
    fixture.detectChanges();

    expect(element().textContent).toContain('Danke');
    expect(element().querySelector('textarea')).toBeNull();
  });

  it('schickt ohne Kontakt keinen mit', async () => {
    await eingeben('textarea[name="text"]', 'Gefällt mir');

    sendenKnopf().click();
    const anfrage = http.expectOne(URL);
    expect(anfrage.request.body).toEqual({ text: 'Gefällt mir', kontakt: null });
    anfrage.flush({ success: true });
  });

  it('sagt vor dem Senden, was gespeichert wird und wann es geloescht wird', () => {
    const text = element().textContent ?? '';
    expect(text).toContain('optional');
    expect(text).toContain('180 Tagen');
    expect(text).toContain('dein Konto nicht mitgespeichert');
  });

  it('behaelt den Text, wenn das Senden scheitert', async () => {
    await eingeben('textarea[name="text"]', 'Mein langer Text');

    sendenKnopf().click();
    http.expectOne(URL).flush('kaputt', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();
    await fixture.whenStable();

    expect(element().textContent).toContain('nicht gesendet');
    expect((element().querySelector('textarea') as HTMLTextAreaElement).value).toBe('Mein langer Text');
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it('nennt das Limit, wenn zu viel in kurzer Zeit kommt', async () => {
    await eingeben('textarea[name="text"]', 'Noch eins');

    sendenKnopf().click();
    http.expectOne(URL).flush('zu viel', { status: 429, statusText: 'Too Many Requests' });
    fixture.detectChanges();

    expect(element().textContent).toContain('ein paar Minuten');
  });

  it('Abbrechen schliesst ohne zu senden', () => {
    (element().querySelector('[data-testid="feedback-abbrechen"]') as HTMLButtonElement).click();

    expect(dialogRef.close).toHaveBeenCalled();
    http.expectNone(URL);
  });
});
