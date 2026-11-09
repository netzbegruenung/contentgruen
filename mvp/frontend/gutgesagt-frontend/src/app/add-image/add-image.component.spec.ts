import { ComponentFixture, TestBed, fakeAsync, flush } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';

import { AddImageComponent } from './add-image.component';
import { ImageService } from '../services/image.service';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';
import { erwarteCc0Hinweis } from '../shared/cc0-hinweis/cc0-hinweis.testing';
import { erwarteSprachhinweisZumBeitrag } from '../shared/components/sprachhinweis/sprachhinweis.testing';

describe('AddImageComponent', () => {
  let fixture: ComponentFixture<AddImageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddImageComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([])
      ]
    })
      .overrideComponent(AddImageComponent, {
        remove: { imports: [BeitragskarteComponent] },
        add: { imports: [BeitragskarteStubComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AddImageComponent);
    fixture.detectChanges();
  });

  it('zeigt über dem Absende-Knopf den CC0-Hinweis mit Links auf CC0 und die Nutzungsbedingungen (#415)', () => {
    erwarteCc0Hinweis(fixture.nativeElement);
  });

  it('gibt Titel und Bildunterschrift dem Sprachhinweis über dem CC0-Hinweis (#405)', () => {
    fixture.componentInstance.imageForm.patchValue({
      title: 'Solardach in Freiburg',
      caption: 'Solarmodule auf dem Dach der Grundschule.',
    });
    fixture.detectChanges();

    erwarteSprachhinweisZumBeitrag(fixture.debugElement, 'Solardach in Freiburg', 'Solarmodule auf dem Dach der Grundschule.');
  });

  it('behaelt nach gescheitertem Speichern die Eingaben und sendet sie mit Erneut versuchen noch einmal', fakeAsync(() => {
    const component = fixture.componentInstance;
    const senden = spyOn(TestBed.inject(ImageService), 'addImage').and.returnValues(
      throwError(() => ({ status: 500 })),
      of({ id: 'b-1' } as any),
    );
    const werte = {
      title: 'Solardach in Freiburg',
      image_url: 'https://example.org/bild.jpg',
      caption: 'Eine ausreichend lange Beschriftung.',
    };
    component.imageForm.patchValue(werte);

    component.saveImageForm();
    fixture.detectChanges();
    const knopf: HTMLButtonElement = fixture.nativeElement.querySelector('.error-state button');
    expect(knopf.textContent).toContain('Erneut versuchen');

    knopf.click();
    fixture.detectChanges();

    expect(senden).toHaveBeenCalledTimes(2);
    expect(senden.calls.mostRecent().args[0].image).toEqual({
      title: werte.title,
      image_url: werte.image_url,
      text: werte.caption,
    });
    expect(component.imageForm.value.title).toBe(werte.title);
    flush();
  }));

  it('bietet keinen KI-Vorschlag fuer die Unterschrift an (#393)', () => {
    const knoepfe: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('form button'));

    expect(knoepfe.length).toBeGreaterThan(0);
    for (const knopf of knoepfe) {
      expect(knopf.textContent).not.toMatch(/KI|Vorschlag/);
      expect(knopf.querySelector('mat-icon')?.textContent?.trim()).not.toBe('auto_awesome');
    }
  });

  it('speichert erst mit einer selbst geschriebenen Unterschrift', () => {
    const component = fixture.componentInstance;
    const senden = spyOn(TestBed.inject(ImageService), 'addImage').and.returnValue(
      of({ id: 'b-1' } as any),
    );
    component.imageForm.patchValue({
      title: 'Solardach in Freiburg',
      image_url: 'https://example.org/bild.jpg',
    });
    fixture.detectChanges();
    const speichern: HTMLButtonElement = fixture.nativeElement.querySelector('.submit-btn');

    expect(speichern.disabled).toBeTrue();
    component.saveImageForm();
    expect(senden).not.toHaveBeenCalled();

    component.imageForm.patchValue({ caption: 'Solarmodule auf dem Dach der Grundschule.' });
    fixture.detectChanges();
    expect(speichern.disabled).toBeFalse();
    component.saveImageForm();
    expect(senden.calls.mostRecent().args[0].image.text).toBe(
      'Solarmodule auf dem Dach der Grundschule.',
    );
  });

  it('beschreibt den Typ mit dem Satz aus der Registry', () => {
    expect(fixture.nativeElement.querySelector('.content-type-description').textContent.trim()).toBe(
      'Ein Bild mit Unterschrift, das für sich spricht.',
    );
  });

  describe('Ladefehler der Bild-URL (#619)', () => {
    /** Ein Bild in der Vorschau, wie es die Karte zur URL zeigt, und sein Ladefehler. */
    function ladefehlerInVorschau(src: string): void {
      const bild = document.createElement('img');
      bild.setAttribute('src', src);
      fixture.nativeElement.querySelector('.preview-content').appendChild(bild);
      bild.dispatchEvent(new Event('error'));
      fixture.detectChanges();
    }

    function hinweis(): HTMLElement | null {
      return fixture.nativeElement.querySelector('.bild-ladefehler');
    }

    it('meldet unter dem Feld, dass sich das Bild nicht laden laesst, und zeigt kein kaputtes Bild', () => {
      const component = fixture.componentInstance;
      component.imageForm.patchValue({ image_url: 'https://example.org/weg.png' });
      fixture.detectChanges();
      expect(hinweis()).toBeNull();

      ladefehlerInVorschau('https://example.org/weg.png');

      expect(hinweis()?.textContent).toContain('Das Bild lässt sich nicht laden – prüf den Link.');
      expect(component.previewResult?.image_result?.image_url).toBe('');
    });

    it('nimmt den Hinweis zurueck, sobald die URL sich aendert', () => {
      const component = fixture.componentInstance;
      component.imageForm.patchValue({ image_url: 'https://example.org/weg.png' });
      ladefehlerInVorschau('https://example.org/weg.png');

      component.imageForm.patchValue({ image_url: 'https://example.org/da.png' });
      fixture.detectChanges();

      expect(hinweis()).toBeNull();
      expect(component.previewResult?.image_result?.image_url).toBe('https://example.org/da.png');
    });

    it('ueberhoert einen verspaeteten Fehler zur vorigen URL', () => {
      fixture.componentInstance.imageForm.patchValue({ image_url: 'https://example.org/da.png' });

      ladefehlerInVorschau('https://example.org/weg.png');

      expect(hinweis()).toBeNull();
    });

    it('sperrt das Speichern nicht', () => {
      const component = fixture.componentInstance;
      component.imageForm.patchValue({
        title: 'Solardach in Freiburg',
        image_url: 'https://example.org/weg.png',
        caption: 'Solarmodule auf dem Dach der Grundschule.',
      });
      ladefehlerInVorschau('https://example.org/weg.png');

      expect(fixture.nativeElement.querySelector('.submit-btn').disabled).toBeFalse();
    });
  });

  it('beschriftet jedes Feld nur einmal und nennt den Titel der Seite nicht noch einmal (#619)', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.input-label')).toBeNull();
    expect(el.textContent).not.toContain('Bild hinzufügen');
    const beschriftungen = Array.from(el.querySelectorAll('mat-label')).map((l) => l.textContent?.trim());
    expect(beschriftungen).toEqual(['Bild-URL', 'Titel', 'Bildunterschrift']);
  });
});
