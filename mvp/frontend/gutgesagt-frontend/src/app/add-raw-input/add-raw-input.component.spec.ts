import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import {
  AddRawInputComponent,
  SEITENTITEL_PRAEFIX,
  hinweisVorschlag,
} from './add-raw-input.component';
import { RawInputService } from '../services/raw-input.service';
import { SHARE_EINWURF_SCHLUESSEL } from '../share-target/share-target.guard';
import { LoggingService } from '../services/logging.service';
import { CONSENT_HINWEIS } from '../shared/consent-hinweis';
import { FANGKORB_BESCHREIBUNG } from '../shared/fangkorb-texte';

describe('hinweisVorschlag', () => {
  it('stellt den Seitentitel mit Praefix voran', () => {
    expect(hinweisVorschlag({ url: 'https://example.org/a', titel: 'Ein Titel', text: null })).toBe(
      `${SEITENTITEL_PRAEFIX}Ein Titel`,
    );
  });

  it('nimmt uebrigen Text dazu', () => {
    expect(hinweisVorschlag({ url: null, titel: 'Ein Titel', text: 'noch was' })).toBe(
      'Seitentitel: Ein Titel\nnoch was',
    );
  });

  it('hat ohne Titel und Text keinen Vorschlag', () => {
    expect(hinweisVorschlag({ url: 'https://example.org/a', titel: null, text: null })).toBeNull();
  });
});

describe('AddRawInputComponent', () => {
  let component: AddRawInputComponent;
  let fixture: ComponentFixture<AddRawInputComponent>;
  let rawInputService: jasmine.SpyObj<RawInputService>;

  /**
   * Die Vorbelegung passiert in ngOnInit, also muss eine Ablage liegen, bevor die
   * Komponente entsteht -- deshalb baut jeder Test die Komponente selbst.
   */
  async function erstellen(ablage: string | null = null): Promise<void> {
    if (ablage === null) {
      sessionStorage.removeItem(SHARE_EINWURF_SCHLUESSEL);
    } else {
      sessionStorage.setItem(SHARE_EINWURF_SCHLUESSEL, ablage);
    }

    const serviceSpy = jasmine.createSpyObj('RawInputService', ['addRawInput']);
    serviceSpy.addRawInput.and.returnValue(of({ id: 'neue-id' }));

    await TestBed.configureTestingModule({
      imports: [AddRawInputComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: RawInputService, useValue: serviceSpy },
        {
          provide: LoggingService,
          useValue: jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']),
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AddRawInputComponent);
    component = fixture.componentInstance;
    rawInputService = TestBed.inject(RawInputService) as jasmine.SpyObj<RawInputService>;
    fixture.detectChanges();
  }

  function eingeben(link: string, hinweis: string): void {
    component.einwurfForm.setValue({ link, hinweis });
    fixture.detectChanges();
  }

  function text(): string {
    return fixture.nativeElement.textContent;
  }

  beforeEach(() => TestBed.resetTestingModule());
  afterEach(() => sessionStorage.removeItem(SHARE_EINWURF_SCHLUESSEL));

  describe('Felder', () => {
    beforeEach(() => erstellen());

    it('hat genau zwei Felder: Link und Hinweis fuer andere', () => {
      const labels = Array.from(fixture.nativeElement.querySelectorAll('mat-label')).map((l) =>
        (l as HTMLElement).textContent!.trim(),
      );

      expect(labels).toEqual(['Link', 'Hinweis für andere']);
      expect(fixture.nativeElement.querySelectorAll('input, textarea').length).toBe(2);
      expect(text()).not.toContain('Bild-Adresse');
    });

    it('verlinkt die Nutzungsbedingungen ueber dem Absenden-Knopf', () => {
      const link: HTMLAnchorElement | null = fixture.nativeElement.querySelector(
        'a[href="/nutzungsbedingungen"]',
      );

      expect(link).toBeTruthy();
      expect(link!.target).toBe('_blank');
      expect(link!.closest('p')!.classList).toContain('submit-hint');
      expect(link!.closest('p')!.textContent!.replace(/\s+/g, ' ').trim()).toBe(
        `${CONSENT_HINWEIS.vorLink}${CONSENT_HINWEIS.link}${CONSENT_HINWEIS.nachLink}`,
      );
    });

    it('zeigt oben eine Hinweisbox mit der Fangkorb-Beschreibung, ohne eigenen Titel', () => {
      const kopf: HTMLElement = fixture.nativeElement.querySelector('.einwurf-kopf');

      expect(kopf.querySelector('.hinweis-box')).toBeTruthy();
      expect(kopf.querySelector('h2')).toBeNull();
      expect(kopf.textContent).toContain(FANGKORB_BESCHREIBUNG);
    });

    it('laesst das Hinweis-Feld mit dem Text wachsen, von zwei bis acht Zeilen', () => {
      const feld: HTMLTextAreaElement = fixture.nativeElement.querySelector('#einwurf-hinweis');

      expect(feld.classList).toContain('cdk-textarea-autosize');
      expect(feld.getAttribute('cdkAutosizeMinRows')).toBe('2');
      expect(feld.getAttribute('cdkAutosizeMaxRows')).toBe('8');
    });

    it('wirft nichts ein, solange nichts dasteht', () => {
      eingeben('  ', '   ');

      component.einwerfen();

      expect(rawInputService.addRawInput).not.toHaveBeenCalled();
    });

    it('nimmt einen Hinweis ohne Link an', () => {
      eingeben('', 'Waermepumpen-Foerderung wurde gekuerzt');

      component.einwerfen();

      expect(rawInputService.addRawInput).toHaveBeenCalledWith({
        content: 'Waermepumpen-Foerderung wurde gekuerzt',
      });
    });

    it('nimmt einen Link ohne Hinweis an', () => {
      eingeben('https://example.org/post', '');

      component.einwerfen();

      expect(rawInputService.addRawInput).toHaveBeenCalledWith({ url: 'https://example.org/post' });
    });

    it('schickt Link und Hinweis getrennt', () => {
      eingeben(' https://example.org/post ', ' Gute Antwort in den Kommentaren ');

      component.einwerfen();

      expect(rawInputService.addRawInput).toHaveBeenCalledWith({
        url: 'https://example.org/post',
        content: 'Gute Antwort in den Kommentaren',
      });
    });

    it('weist im Link-Feld alles ab, was nicht nur ein Link ist', () => {
      eingeben('Guter Thread https://example.org/p', '');
      component.einwurfForm.get('link')!.markAsTouched();
      fixture.detectChanges();

      component.einwerfen();

      expect(rawInputService.addRawInput).not.toHaveBeenCalled();
      expect(component.kannEinwerfen).toBeFalse();
      expect(text()).toContain('Bitte nur einen Link');
    });

    it('entfernt Tracking-Parameter aus dem Link und aus Adressen im Hinweis', () => {
      eingeben(
        'https://www.instagram.com/reel/ABC/?stkn=xyz',
        'siehe auch https://example.org/b?utm_source=x',
      );

      component.einwerfen();

      expect(rawInputService.addRawInput).toHaveBeenCalledWith({
        url: 'https://www.instagram.com/reel/ABC/',
        content: 'siehe auch https://example.org/b',
      });
    });

    it('laesst das Formular nach dem Einwerfen offen und leer und zaehlt mit', () => {
      eingeben('https://example.org/a', 'eins');
      component.einwerfen();
      eingeben('', 'zwei');
      component.einwerfen();

      expect(component.einwurfForm.value).toEqual({ link: '', hinweis: '' });
      expect(component.eingeworfen).toBe(2);
      expect(component.fehler).toBeNull();
    });

    it('meldet einen abgewiesenen Einwurf verstaendlich', () => {
      rawInputService.addRawInput.and.returnValue(throwError(() => ({ status: 422 })));
      eingeben('https://example.org/a', '');

      component.einwerfen();

      expect(component.fehler).toContain('Link');
      expect(component.wirdGespeichert).toBeFalse();
    });

    it('behaelt die Eingabe, wenn das Speichern fehlschlaegt', () => {
      rawInputService.addRawInput.and.returnValue(throwError(() => ({ status: 500 })));
      eingeben('https://example.org/a', 'nicht verlieren');

      component.einwerfen();

      expect(component.einwurfForm.value).toEqual({
        link: 'https://example.org/a',
        hinweis: 'nicht verlieren',
      });
      expect(component.eingeworfen).toBe(0);
    });
  });

  describe('Uebernahme aus dem Teilen-Menue', () => {
    const vomBrowser = JSON.stringify({
      url: 'https://www.tagesschau.de/inland/x-100.html',
      titel: 'AfD klar vor SPD | tagesschau.de',
      text: null,
    });

    it('fuellt bei Instagram nur den Link', async () => {
      await erstellen(
        JSON.stringify({ url: 'https://www.instagram.com/reel/ABC/', titel: null, text: null }),
      );

      expect(component.einwurfForm.value).toEqual({
        link: 'https://www.instagram.com/reel/ABC/',
        hinweis: '',
      });
      expect(component.ausShare).toBeTrue();
      expect(component.istVorbelegt).toBeFalse();
    });

    it('legt den Seitentitel als markierte Vorbelegung ins Hinweis-Feld', async () => {
      await erstellen(vomBrowser);

      expect(component.einwurfForm.value.link).toBe('https://www.tagesschau.de/inland/x-100.html');
      expect(component.einwurfForm.value.hinweis).toBe(
        'Seitentitel: AfD klar vor SPD | tagesschau.de',
      );
      expect(component.istVorbelegt).toBeTrue();
      expect(fixture.nativeElement.querySelector('.hinweis-feld.vorbelegt')).toBeTruthy();
      expect(text()).toContain('Vorschlag aus dem Teilen');
    });

    it('uebernimmt den Vorschlag, wenn er stehen bleibt', async () => {
      await erstellen(vomBrowser);

      component.einwerfen();

      expect(rawInputService.addRawInput).toHaveBeenCalledWith({
        url: 'https://www.tagesschau.de/inland/x-100.html',
        content: 'Seitentitel: AfD klar vor SPD | tagesschau.de',
        source_channel: 'share',
      });
    });

    it('entfernt den Vorschlag mit einem Griff', async () => {
      await erstellen(vomBrowser);
      const knopf: HTMLButtonElement = fixture.nativeElement.querySelector(
        'button.vorbelegung-entfernen',
      );

      knopf.click();
      fixture.detectChanges();
      component.einwerfen();

      expect(fixture.nativeElement.querySelector('button.vorbelegung-entfernen')).toBeNull();
      expect(rawInputService.addRawInput).toHaveBeenCalledWith({
        url: 'https://www.tagesschau.de/inland/x-100.html',
        source_channel: 'share',
      });
    });

    it('markiert einen bearbeiteten Vorschlag nicht mehr als Vorbelegung', async () => {
      await erstellen(vomBrowser);

      eingeben('https://www.tagesschau.de/inland/x-100.html', 'Umfrage, lohnt eine Antwort');

      expect(component.istVorbelegt).toBeFalse();
      expect(fixture.nativeElement.querySelector('.hinweis-feld.vorbelegt')).toBeNull();
    });

    it('raeumt die Ablage weg, damit der naechste Aufruf leer beginnt', async () => {
      await erstellen(vomBrowser);

      expect(sessionStorage.getItem(SHARE_EINWURF_SCHLUESSEL)).toBeNull();
    });

    it('zaehlt den naechsten Einwurf wieder als web', async () => {
      await erstellen(vomBrowser);
      component.einwerfen();

      eingeben('', 'von Hand getippt');
      component.einwerfen();

      expect(rawInputService.addRawInput.calls.mostRecent().args[0]).toEqual({
        content: 'von Hand getippt',
      });
    });

    it('befuellt nichts, wenn nichts abgelegt wurde', async () => {
      await erstellen(null);

      expect(component.einwurfForm.value).toEqual({ link: '', hinweis: '' });
      expect(component.ausShare).toBeFalse();
    });

    it('versteht noch die Klartext-Ablage einer aelteren Version', async () => {
      await erstellen('Ein Seitentitel\nhttps://example.org/a');

      expect(component.einwurfForm.value).toEqual({
        link: 'https://example.org/a',
        hinweis: 'Ein Seitentitel',
      });
    });
  });
});
