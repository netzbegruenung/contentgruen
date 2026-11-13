import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { MELDEN_AN_KONTO_VORAUSGEWAEHLT, ReportDialogComponent, meldeDialogOeffnen } from './report-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { ERFUNDENES_MELDEN } from '../../schreibregeln';
import { MeldegrundWert } from '../../meldegruende';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../auth/auth.service';

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

  async function grundWaehlen(grund: MeldegrundWert = 'spam') {
    fixture.componentInstance.selectedReason = grund;
    fixture.detectChanges();
    await fixture.whenStable();
  }

  /** Der Hinweis neben „Melden“, was noch fehlt (#581); leer, wenn nichts fehlt. */
  function fehltHinweis(): string {
    return element().querySelector('[data-testid="melden-fehlt"]')?.textContent?.trim() ?? '';
  }

  function meldenKnopf(): HTMLButtonElement {
    return element().querySelector('[data-testid="melden-senden"]') as HTMLButtonElement;
  }

  // Design-Audit A3/B8 (#512): Auf dem Handy war der Dialog rechts abgeschnitten
  // (min-width 400 px in einem 312 px breiten Dialog), die Felder grau hinterlegt.
  describe('auf dem Handy', () => {
    it('oeffnet hoechstens 95 % der Fensterbreite breit', () => {
      const dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);

      meldeDialogOeffnen(dialog, { contentId: 'id', contentType: 'commentary' });

      expect(dialog.open).toHaveBeenCalledWith(
        ReportDialogComponent,
        jasmine.objectContaining({ maxWidth: '95vw', data: { contentId: 'id', contentType: 'commentary' } }),
      );
    });

    it('erzwingt keine Mindestbreite und nutzt Felder mit Kontur wie ueberall', () => {
      expect(getComputedStyle(element().querySelector('.report-dialog')!).minWidth).toBe('0px');
      const felder = Array.from(element().querySelectorAll('mat-form-field'));
      expect(felder.length).toBeGreaterThan(0);
      felder.forEach((f) => expect(f.classList).toContain('mat-form-field-appearance-outline'));
    });
  });

  // #581: Am Desktop war „Melden“ stumm ausgegraut, die Checkbox lag unter dem Falz und
  // der Grund war mit „Spam“ vorbelegt.
  describe('wenn etwas fehlt', () => {
    it('wählt keinen Grund vor', () => {
      expect(fixture.componentInstance.selectedReason).toBeNull();
      expect(element().querySelector('mat-select')!.getAttribute('aria-required')).toBe('true');
    });

    it('sagt neben dem ausgegrauten „Melden“, was fehlt', () => {
      expect(meldenKnopf().disabled).toBeTrue();
      expect(fehltHinweis()).toBe('Zum Melden fehlen noch: ein Grund und deine Erklärung guten Glaubens.');
    });

    it('nennt nur, was noch fehlt, und verschwindet, wenn alles da ist', async () => {
      await grundWaehlen();
      expect(fehltHinweis()).toBe('Zum Melden fehlt noch: deine Erklärung guten Glaubens.');

      await gutenGlaubenErklaeren();
      expect(meldenKnopf().disabled).toBeFalse();
      expect(element().querySelector('[data-testid="melden-fehlt"]')).toBeNull();
    });

    it('nennt die Begründung bei „Rechtswidriger Inhalt“ und eine ungültige E-Mail-Adresse', async () => {
      await grundWaehlen('illegal_content');
      await eingeben('input[name="melder_email"]', 'anna@');
      await gutenGlaubenErklaeren();
      // Wie die Fehlermeldung am Feld erst nach dem Verlassen, nicht bei jedem Zeichen.
      expect(fehltHinweis()).toBe('Zum Melden fehlt noch: die Begründung, warum der Beitrag rechtswidrig ist.');

      element().querySelector('input[name="melder_email"]')!.dispatchEvent(new Event('blur'));
      fixture.detectChanges();

      expect(fehltHinweis()).toBe(
        'Zum Melden fehlen noch: die Begründung, warum der Beitrag rechtswidrig ist, und eine gültige E-Mail-Adresse (oder das Feld leer lassen).',
      );
    });
  });

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
    await grundWaehlen();
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
    await grundWaehlen();
    await gutenGlaubenErklaeren();

    await melden();

    const anfrage = http.expectOne(URL);
    expect(anfrage.request.body.melder_name).toBeNull();
    expect(anfrage.request.body.melder_email).toBeNull();
    expect(anfrage.request.body.guter_glaube).toBeTrue();
    anfrage.flush({ success: true, message: '' });
  });

  it('meldet erst, wenn die Person ihren guten Glauben erklärt hat, und sagt warum', async () => {
    await grundWaehlen();
    expect(element().textContent).toContain('Ohne diese Erklärung lässt sich nicht melden.');
    expect(fehltHinweis()).toContain('deine Erklärung guten Glaubens');

    await gutenGlaubenErklaeren();

    expect(element().textContent).not.toContain('Ohne diese Erklärung lässt sich nicht melden.');
    expect(fehltHinweis()).toBe('');
  });

  it('prüft die E-Mail-Adresse wie der Suchdienst, etwa ohne .local', async () => {
    await grundWaehlen();
    await gutenGlaubenErklaeren();
    await eingeben('input[name="melder_email"]', 'anna@rechner.local');

    expect(meldenKnopf().disabled).toBeTrue();
  });

  it('meldet nicht mit einer E-Mail-Adresse, die keine ist, und sagt es nach dem Verlassen des Feldes', async () => {
    await grundWaehlen();
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
    await grundWaehlen();
    await eingeben('input[name="melder_email"]', 'anna@beispiel.org');
    await gutenGlaubenErklaeren();
    await melden();

    http.expectOne(URL).flush(
      { detail: [{ input: 'anna@beispiel.org' }] },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();

    expect(element().textContent).toContain('Bitte prüfe deine Angaben, etwa die E-Mail-Adresse.');
    expect(JSON.stringify(log.calls.allArgs())).not.toContain('anna@beispiel.org');
  });

  it('bestätigt den Eingang in der App und bleibt offen, bis die Person schließt', async () => {
    await grundWaehlen();
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

  it('sagt nach dem Eingang, dass Bestätigung und Entscheidung per E-Mail kommen, wenn eine Adresse dasteht', async () => {
    await grundWaehlen();
    await eingeben('input[name="melder_email"]', 'anna@example.org');
    await gutenGlaubenErklaeren();
    await melden();

    http.expectOne(URL).flush({ success: true, message: '' });
    fixture.detectChanges();

    expect(element().querySelector('[role="status"]')!.textContent).toContain(
      'Eine Bestätigung und später unsere Entscheidung schicken wir dir per E-Mail.',
    );
  });
  // UX-Review B17 (Entscheidung Maintainer 13.11.2026): Angemeldete tippen weder Name noch
  // Adresse; das Haekchen laesst den Suchdienst die Adresse des Kontos nehmen. Vorauswahl
  // vorerst aus (MELDEN_AN_KONTO_VORAUSGEWAEHLT, Art. 25 Abs. 2 DSGVO).
  describe('angemeldet', () => {
    const KIM = { isAuthenticated: true, userId: 'kim', userName: 'Kim', claims: null };

    beforeEach(async () => {
      TestBed.inject(AuthService).setUserInfo(KIM);
      fixture = TestBed.createComponent(ReportDialogComponent);
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    });

    function anKonto(): HTMLInputElement {
      return element().querySelector('[data-testid="melden-an-konto"] input') as HTMLInputElement;
    }

    async function haekchenSetzen() {
      anKonto().click();
      fixture.detectChanges();
      await fixture.whenStable();
    }

    it('fragt weder nach Name noch nach Adresse und bietet das Haekchen an, nach der Konstante vorausgewaehlt', () => {
      expect(element().querySelector('input[name="melder_name"]')).toBeNull();
      expect(element().querySelector('input[name="melder_email"]')).toBeNull();
      expect(element().querySelector('[data-testid="melden-an-konto"]')!.textContent).toContain(
        'Bestätigung und Entscheidung per Mail an mein Konto',
      );
      expect(anKonto().checked).toBe(MELDEN_AN_KONTO_VORAUSGEWAEHLT);
      expect(MELDEN_AN_KONTO_VORAUSGEWAEHLT).toBeFalse();
      expect(element().textContent).toContain('Die Adresse deines Kontos sehen nur Admins, und nur mit Häkchen.');
    });

    it('schickt mit Haekchen bestaetigung_an_konto, weder Name noch Adresse, und kuendigt die Mail an, wenn der Suchdienst eine gespeichert hat', async () => {
      fixture.componentInstance.melderName = 'Liegengeblieben';
      fixture.componentInstance.melderEmail = 'liegengeblieben@example.com';
      await haekchenSetzen();
      await grundWaehlen();
      await gutenGlaubenErklaeren();

      await melden();

      const anfrage = http.expectOne(URL);
      expect(anfrage.request.body.melder_name).toBeNull();
      expect(anfrage.request.body.melder_email).toBeNull();
      expect(anfrage.request.body.bestaetigung_an_konto).toBeTrue();
      anfrage.flush({ success: true, message: '', mit_email: true });
      fixture.detectChanges();
      expect(element().querySelector('[role="status"]')!.textContent).toContain(
        'Eine Bestätigung und später unsere Entscheidung schicken wir dir per E-Mail.',
      );
    });

    it('verspricht keine Mail, wenn der Suchdienst keine Adresse gespeichert hat (etwa keine im Konto)', async () => {
      await haekchenSetzen();
      await grundWaehlen();
      await gutenGlaubenErklaeren();

      await melden();

      http.expectOne(URL).flush({ success: true, message: '', mit_email: false });
      fixture.detectChanges();
      expect(element().querySelector('[role="status"]')!.textContent).not.toContain('per E-Mail');
    });

    it('schickt ohne Haekchen keine Bitte um Mail', async () => {
      await grundWaehlen();
      await gutenGlaubenErklaeren();

      await melden();

      const anfrage = http.expectOne(URL);
      expect(anfrage.request.body.bestaetigung_an_konto).toBeUndefined();
      anfrage.flush({ success: true, message: '', mit_email: false });
    });

    it('folgt der Anmeldung: Abmelden zeigt die Felder fuer Besucher wieder', async () => {
      TestBed.inject(AuthService).setUserInfo({ isAuthenticated: false, userId: null, userName: null, claims: null });
      fixture.detectChanges();
      await fixture.whenStable();

      expect(element().querySelector('input[name="melder_email"]')).not.toBeNull();
      expect(element().querySelector('[data-testid="melden-an-konto"]')).toBeNull();
    });
  });
});
