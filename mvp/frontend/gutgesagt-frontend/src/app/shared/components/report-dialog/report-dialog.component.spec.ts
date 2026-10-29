import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { ReportDialogComponent } from './report-dialog.component';
import { ERFUNDENES_MELDEN } from '../../schreibregeln';
import { environment } from '../../../../environments/environment';

const URL = `${environment.baseUrl}/api/v1/moderation/report`;

describe('ReportDialogComponent', () => {
  let fixture: ComponentFixture<ReportDialogComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReportDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        { provide: MatDialogRef, useValue: jasmine.createSpyObj('MatDialogRef', ['close']) },
        { provide: MAT_DIALOG_DATA, useValue: { contentId: 'id', contentType: 'commentary' } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ReportDialogComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    await fixture.whenStable();
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

  async function gutenGlaubenErklaeren() {
    const kasten = element().querySelector('[data-testid="melden-guter-glaube"] input') as HTMLInputElement;
    kasten.click();
    fixture.detectChanges();
    await fixture.whenStable();
  }

  function meldenKnopf(): HTMLButtonElement {
    return element().querySelector('[data-testid="melden-senden"]') as HTMLButtonElement;
  }

  async function melden() {
    meldenKnopf().click();
    fixture.detectChanges();
    await fixture.whenStable();
  }

  it('nennt die Dublette nach dem Glossar', () => {
    const grund = fixture.componentInstance.reasons.find((g) => g.value === 'duplicate');

    expect(grund?.label).toBe('Dublette');
  });

  it('bietet „Erfunden oder sachlich falsch“ an, und der Hinweis zu Erfundenem verweist darauf', () => {
    const grund = fixture.componentInstance.reasons.find((g) => g.value === 'fabricated_or_false')!;

    expect(grund.label).toBe('Erfunden oder sachlich falsch');
    expect(ERFUNDENES_MELDEN).toContain(`„${grund.label}“`);
    expect(ERFUNDENES_MELDEN).not.toContain('„Andere“');
  });

  it('meldet erst, wenn die Person ihren guten Glauben erklärt hat', async () => {
    expect(meldenKnopf().disabled).toBeTrue();

    await gutenGlaubenErklaeren();

    expect(meldenKnopf().disabled).toBeFalse();
  });

  it('sendet Grund, Beschreibung, Name, E-Mail-Adresse und die Erklärung guten Glaubens', async () => {
    fixture.componentInstance.selectedReason = 'fabricated_or_false';
    await eingeben('textarea[name="beschreibung"]', 'Die Zahl stimmt nicht');
    await eingeben('input[name="melder_name"]', ' Anna Beispiel ');
    await eingeben('input[name="melder_email"]', 'anna@example.org');
    await gutenGlaubenErklaeren();

    await melden();

    const anfrage = http.expectOne(URL);
    expect(anfrage.request.body).toEqual({
      content_id: 'id',
      content_type: 'commentary',
      reason: 'fabricated_or_false',
      description: 'Die Zahl stimmt nicht',
      melder_name: 'Anna Beispiel',
      melder_email: 'anna@example.org',
      guter_glaube: true,
    });
    anfrage.flush({ success: true, message: '' });
  });

  it('schickt ohne Name und E-Mail-Adresse keine mit', async () => {
    await gutenGlaubenErklaeren();

    await melden();

    const anfrage = http.expectOne(URL);
    expect(anfrage.request.body.melder_name).toBeNull();
    expect(anfrage.request.body.melder_email).toBeNull();
    expect(anfrage.request.body.guter_glaube).toBeTrue();
    anfrage.flush({ success: true, message: '' });
  });

  it('meldet nicht mit einer E-Mail-Adresse, die keine ist', async () => {
    await gutenGlaubenErklaeren();
    await eingeben('input[name="melder_email"]', 'anna@');

    expect(meldenKnopf().disabled).toBeTrue();
    expect(element().textContent).toContain('Das ist keine E-Mail-Adresse.');
  });

  it('bestätigt den Eingang in der App und bleibt offen, bis die Person schließt', async () => {
    await gutenGlaubenErklaeren();
    await melden();

    http.expectOne(URL).flush({ success: true, message: '' });
    fixture.detectChanges();

    const bestaetigung = element().querySelector('[role="status"]')!;
    expect(bestaetigung.textContent).toContain('Deine Meldung ist eingegangen.');
    expect(bestaetigung.textContent).not.toContain('per E-Mail');
    expect(TestBed.inject(MatDialogRef).close).not.toHaveBeenCalled();
  });

  it('sagt nach dem Eingang, dass die Entscheidung per E-Mail kommt, wenn eine Adresse dasteht', async () => {
    await eingeben('input[name="melder_email"]', 'anna@example.org');
    await gutenGlaubenErklaeren();
    await melden();

    http.expectOne(URL).flush({ success: true, message: '' });
    fixture.detectChanges();

    expect(element().querySelector('[role="status"]')!.textContent).toContain(
      'Unsere Entscheidung teilen wir dir per E-Mail mit.',
    );
  });
});
