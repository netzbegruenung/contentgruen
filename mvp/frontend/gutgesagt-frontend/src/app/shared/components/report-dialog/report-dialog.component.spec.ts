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

  it('verlangt bei „Rechtswidriger Inhalt“ eine Begründung', async () => {
    const grund = fixture.componentInstance.reasons.find((g) => g.value === 'illegal_content')!;
    expect(grund.label).toBe('Rechtswidriger Inhalt');

    fixture.componentInstance.selectedReason = 'illegal_content';
    await gutenGlaubenErklaeren();

    expect(meldenKnopf().disabled).toBeTrue();
    expect(element().textContent).toContain('Warum ist der Beitrag rechtswidrig?');

    await eingeben('textarea[name="beschreibung"]', '   ');
    expect(meldenKnopf().disabled).toBeTrue();

    await eingeben('textarea[name="beschreibung"]', 'Volksverhetzung nach § 130 StGB');
    expect(meldenKnopf().disabled).toBeFalse();
  });

  it('lässt die Beschreibung bei anderen Gründen freiwillig', async () => {
    fixture.componentInstance.selectedReason = 'spam';
    await gutenGlaubenErklaeren();

    expect(meldenKnopf().disabled).toBeFalse();
    expect(element().textContent).toContain('Beschreibung (optional)');
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

  it('meldet erst, wenn die Person ihren guten Glauben erklärt hat, und sagt warum', async () => {
    expect(element().textContent).toContain('Ohne diese Erklärung lässt sich nicht melden.');

    await gutenGlaubenErklaeren();

    expect(element().textContent).not.toContain('Ohne diese Erklärung lässt sich nicht melden.');
  });

  it('meldet nicht mit einer E-Mail-Adresse, die keine ist, und sagt es nach dem Verlassen des Feldes', async () => {
    await gutenGlaubenErklaeren();
    await eingeben('input[name="melder_email"]', 'anna@');

    expect(meldenKnopf().disabled).toBeTrue();
    expect(element().textContent).not.toContain('Das ist keine E-Mail-Adresse.');

    const feld = element().querySelector('input[name="melder_email"]') as HTMLInputElement;
    feld.dispatchEvent(new Event('blur'));
    fixture.detectChanges();

    expect(element().textContent).toContain('Das ist keine E-Mail-Adresse.');
    expect(feld.getAttribute('aria-invalid')).toBe('true');
    expect(feld.getAttribute('aria-describedby')).toBe('melder-email-fehler');
  });

  it('bittet bei 422 darum, die Angaben zu prüfen, und schreibt keine Antwort ins Log', async () => {
    const log = spyOn(console, 'error');
    await eingeben('input[name="melder_email"]', 'anna@example.test');
    await gutenGlaubenErklaeren();
    await melden();

    http.expectOne(URL).flush(
      { detail: [{ input: 'anna@example.test' }] },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();

    expect(element().textContent).toContain('Bitte prüfe deine Angaben, etwa die E-Mail-Adresse.');
    expect(JSON.stringify(log.calls.allArgs())).not.toContain('anna@example.test');
  });

  it('bestätigt den Eingang in der App und bleibt offen, bis die Person schließt', async () => {
    await gutenGlaubenErklaeren();
    await melden();

    http.expectOne(URL).flush({ success: true, message: '' });
    fixture.detectChanges();

    const bestaetigung = element().querySelector('[role="status"]')!;
    expect(bestaetigung.textContent).toContain('Deine Meldung ist eingegangen.');
    expect(document.activeElement).toBe(bestaetigung);
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
