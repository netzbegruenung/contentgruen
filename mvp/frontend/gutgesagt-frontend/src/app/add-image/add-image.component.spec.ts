import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';

import { AddImageComponent, SPEICHERN_FEHLGESCHLAGEN } from './add-image.component';
import { ImageService } from '../services/image.service';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';
import type { BeitragGespeichert } from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';
import { OHNE_AUSSAGE } from '../beitragsformular/antwort-auf/antwort-auf.component';
import { typBeschreibung } from '../shared/content-type-registry';
import { erwarteCc0Hinweis } from '../shared/cc0-hinweis/cc0-hinweis.testing';
import { erwarteSprachhinweisZumBeitrag } from '../shared/components/sprachhinweis/sprachhinweis.testing';

const WERTE = {
  image_url: 'https://example.org/dach.jpg',
  title: 'Solardach auf der Grundschule',
  caption: 'Die Stadt hat alle Schuldächer mit Solarmodulen belegt.',
};

describe('AddImageComponent', () => {
  let fixture: ComponentFixture<AddImageComponent>;
  let component: AddImageComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddImageComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    })
      .overrideComponent(AddImageComponent, {
        remove: { imports: [BeitragskarteComponent] },
        add: { imports: [BeitragskarteStubComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AddImageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  function element<T extends HTMLElement = HTMLElement>(selektor: string): T | null {
    return fixture.nativeElement.querySelector(selektor);
  }

  it('zeigt über dem Speichern-Knopf den CC0-Hinweis mit Links auf CC0 und die Nutzungsbedingungen (#415)', () => {
    erwarteCc0Hinweis(fixture.nativeElement);
  });

  it('gibt Titel und Unterschrift dem Sprachhinweis über dem CC0-Hinweis (#405)', () => {
    component.imageForm.patchValue(WERTE);
    fixture.detectChanges();

    erwarteSprachhinweisZumBeitrag(fixture.debugElement, WERTE.title, WERTE.caption);
  });

  describe('dieselben Bausteine wie die anderen Formulare (#619)', () => {
    it('zeigt die Formularhilfe mit dem Satz aus der Registry', () => {
      expect(element('app-formular-hilfe')?.textContent).toContain(typBeschreibung('image'));
    });

    it('hat "Antwort auf" über der Bild-URL, Gegenlesen neben der Vorschau und die Formular-Leiste', () => {
      const block = element('form app-antwort-auf')!;
      expect(block).not.toBeNull();
      expect(block.compareDocumentPosition(element('#image_url')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(element('.preview-column app-gegenlesen')).not.toBeNull();
      expect(element('app-formular-leiste .submit-btn')).not.toBeNull();
    });

    it('beschriftet jedes Feld einmal und hat keinen eigenen Abbrechen-Knopf', () => {
      const beschriftungen = Array.from(fixture.nativeElement.querySelectorAll('form > mat-form-field mat-label')).map(
        (l: any) => l.textContent.trim(),
      );
      expect(beschriftungen).toEqual(['Bild-URL', 'Titel', 'Bildunterschrift']);
      expect(fixture.nativeElement.textContent).not.toContain('Abbrechen');
    });
  });

  it('speichert erst mit einer selbst geschriebenen Unterschrift (ADR 0003)', () => {
    const senden = spyOn(TestBed.inject(ImageService), 'addImage').and.returnValue(of({ id: 'b-1' }));
    component.imageForm.patchValue({ ...WERTE, caption: '' });
    fixture.detectChanges();

    expect(element<HTMLButtonElement>('.submit-btn')!.disabled).toBeTrue();
    component.speichern();
    expect(senden).not.toHaveBeenCalled();
  });

  it('bietet keinen KI-Vorschlag fuer die Unterschrift an (#393)', () => {
    const knoepfe: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('form button'));
    for (const knopf of knoepfe) {
      expect(knopf.textContent).not.toMatch(/KI|Vorschlag/);
      expect(knopf.querySelector('mat-icon')?.textContent?.trim()).not.toBe('auto_awesome');
    }
  });

  it('speichert Titel einzeilig und meldet ID ohne Aussage', () => {
    const senden = spyOn(TestBed.inject(ImageService), 'addImage').and.returnValue(of({ id: 'b-1', verknuepft: true }));
    let gemeldet: BeitragGespeichert | undefined;
    component.success.subscribe((ergebnis) => (gemeldet = ergebnis));
    component.imageForm.patchValue({ ...WERTE, title: 'Solardach\nauf der Grundschule' });

    component.speichern();

    expect(senden).toHaveBeenCalledOnceWith({
      image: { title: 'Solardach auf der Grundschule', image_url: WERTE.image_url, text: WERTE.caption },
    });
    expect(gemeldet).toEqual({ id: 'b-1', aussage: OHNE_AUSSAGE, verknuepft: true });
  });

  // UX-Review B4: ohne Einwilligung kein "versuche es erneut", der Hinweiskasten sagt es
  it('zeigt bei fehlender Einwilligung (403) keine Fehlermeldung und behaelt die Eingaben', () => {
    spyOn(TestBed.inject(ImageService), 'addImage').and.returnValue(throwError(() => ({ status: 403, error: { detail: 'art9_einwilligung_fehlt' } })));
    component.imageForm.patchValue(WERTE);

    component.speichern();
    fixture.detectChanges();

    expect(component.fehler).toBeNull();
    expect(component.speichert).toBeFalse();
    expect(component.imageForm.value.title).toBe(WERTE.title);
  });

  it('behaelt nach gescheitertem Speichern die Eingaben und speichert mit "Erneut versuchen" dasselbe', () => {
    const senden = spyOn(TestBed.inject(ImageService), 'addImage').and.returnValues(
      throwError(() => ({ status: 500 })),
      of({ id: 'b-1' }),
    );
    component.imageForm.patchValue(WERTE);

    component.speichern();
    fixture.detectChanges();

    expect(component.fehler).toBe(SPEICHERN_FEHLGESCHLAGEN);
    expect(element('.submit-btn')!.textContent).toContain('Erneut versuchen');
    expect(component.imageForm.value.title).toBe(WERTE.title);

    element<HTMLButtonElement>('.submit-btn')!.click();
    expect(senden).toHaveBeenCalledTimes(2);
    expect(senden.calls.mostRecent().args[0].image.title).toBe(WERTE.title);
  });

  describe('Antwort auf (optional, #619)', () => {
    it('schickt eine gewählte Aussage per ID mit und meldet die verknüpfte', () => {
      const senden = spyOn(TestBed.inject(ImageService), 'addImage').and.returnValue(
        of({ id: 'b-1', statement_id: 'a-1', statement_text: 'Solar lohnt sich nicht!', verknuepft: true }),
      );
      let gemeldet: BeitragGespeichert | undefined;
      component.success.subscribe((ergebnis) => (gemeldet = ergebnis));
      component.imageForm.patchValue(WERTE);
      component.aussageSetzen({ id: 'a-1', text: 'Solar lohnt sich nicht' });

      component.speichern();

      expect(senden.calls.mostRecent().args[0].statement_id).toBe('a-1');
      expect(gemeldet).toEqual({ id: 'b-1', aussage: { id: 'a-1', text: 'Solar lohnt sich nicht!' }, verknuepft: true });
    });

    it('schickt eine neue Aussage per Text mit ihren Themen', () => {
      const senden = spyOn(TestBed.inject(ImageService), 'addImage').and.returnValue(of({ id: 'b-1', verknuepft: true }));
      component.imageForm.patchValue({ ...WERTE, themen: ['energie-heizen'] });
      component.aussageSetzen({ id: '', text: 'Solar lohnt sich nicht', neuGewaehlt: true });

      component.speichern();

      expect(senden.calls.mostRecent().args[0]).toEqual(
        jasmine.objectContaining({ statement_text: 'Solar lohnt sich nicht', themen: ['energie-heizen'] }),
      );
    });

    it('sperrt Speichern bei einer Aussage unter 10 Zeichen', () => {
      const senden = spyOn(TestBed.inject(ImageService), 'addImage');
      component.imageForm.patchValue(WERTE);
      component.aussageSetzen({ id: '', text: 'zu kurz' });
      fixture.detectChanges();

      expect(element<HTMLButtonElement>('.submit-btn')!.disabled).toBeTrue();
      component.speichern();
      expect(senden).not.toHaveBeenCalled();
    });

    it('zeigt die Aussage in der Vorschau-Karte und gibt sie dem Gegenlesen', () => {
      component.aussageSetzen({ id: '', text: 'Solar lohnt sich nicht' });

      expect(component.vorschauKarte.statement?.text).toBe('Solar lohnt sich nicht');
      fixture.detectChanges();
      expect(fixture.debugElement.query((d) => d.name === 'app-gegenlesen').componentInstance.aussage).toBe(
        'Solar lohnt sich nicht',
      );
    });
  });

  describe('Ladefehler der Bild-URL', () => {
    function ladefehlerInVorschau(src: string): void {
      const bild = document.createElement('img');
      bild.setAttribute('src', src);
      element('.preview-content')!.appendChild(bild);
      bild.dispatchEvent(new Event('error'));
      fixture.detectChanges();
    }

    it('meldet am Feld, dass sich das Bild nicht laden laesst, und zeigt kein kaputtes Bild', () => {
      component.imageForm.patchValue({ image_url: 'https://example.org/weg.png' });
      fixture.detectChanges();
      expect(element('.bild-ladefehler')).toBeNull();

      ladefehlerInVorschau('https://example.org/weg.png');

      expect(element('mat-form-field .bild-ladefehler')?.textContent).toContain('Das Bild lässt sich nicht laden – prüf den Link.');
      expect(element('.preview-content .vorschau-ladefehler')).not.toBeNull();
      expect(component.vorschauKarte.bildUrl).toBeUndefined();
    });

    it('nimmt den Hinweis zurueck, sobald die URL sich aendert, und ueberhoert verspaetete Fehler', () => {
      component.imageForm.patchValue({ image_url: 'https://example.org/weg.png' });
      ladefehlerInVorschau('https://example.org/weg.png');

      component.imageForm.patchValue({ image_url: 'https://example.org/da.png' });
      ladefehlerInVorschau('https://example.org/weg.png');

      expect(element('.bild-ladefehler')).toBeNull();
      expect(component.vorschauKarte.bildUrl).toBe('https://example.org/da.png');
    });

    it('sperrt das Speichern nicht', () => {
      component.imageForm.patchValue({ ...WERTE, image_url: 'https://example.org/weg.png' });
      ladefehlerInVorschau('https://example.org/weg.png');

      expect(element<HTMLButtonElement>('.submit-btn')!.disabled).toBeFalse();
    });
  });
});

describe('AddImageComponent mit der echten Vorschau-Karte', () => {
  it('bemerkt den Ladefehler des Bildes, das die Karte zur eingegebenen URL zeigt', async () => {
    await TestBed.configureTestingModule({
      imports: [AddImageComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    const fixture = TestBed.createComponent(AddImageComponent);
    fixture.detectChanges();

    // Eine Adresse auf dem eigenen Server laedt ohne Klick (#447) und scheitert hier.
    fixture.componentInstance.imageForm.patchValue({ image_url: location.origin + '/assets/gibt-es-nicht-619.png' });
    fixture.detectChanges();
    const bild: HTMLImageElement = fixture.nativeElement.querySelector('.preview-content app-fremdes-bild img');
    expect(bild).withContext('die Karte zeigt das Bild').not.toBeNull();
    bild.dispatchEvent(new Event('error'));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('mat-form-field .bild-ladefehler')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.preview-content app-fremdes-bild img')).toBeNull();
  });
});

describe('Formularhilfe Bild (#619)', () => {
  it('nennt Privatpersonen nur ohne ihr Einverständnis als Ausschluss', async () => {
    const { FORMULAR_HILFE } = await import('../beitragsformular/formular-hilfe/formular-hilfe-texte');
    expect(FORMULAR_HILFE.image?.istNicht).toContain(
      'Bilder, an denen du keine Rechte hast oder auf denen Privatpersonen ohne ihr Einverständnis erkennbar sind',
    );
  });
});
