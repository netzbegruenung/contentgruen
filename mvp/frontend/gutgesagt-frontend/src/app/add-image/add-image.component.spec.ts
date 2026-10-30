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
import { CONSENT_HINWEIS } from '../shared/consent-hinweis';

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

  it('verlinkt die Nutzungsbedingungen ueber dem Absenden-Knopf', () => {
    const link: HTMLAnchorElement | null = fixture.nativeElement.querySelector(
      'a[href="/nutzungsbedingungen"]'
    );

    expect(link).toBeTruthy();
    expect(link!.target).toBe('_blank');
    expect(link!.closest('p')!.classList).toContain('submit-hint');
    expect(link!.closest('p')!.textContent!.replace(/\s+/g, ' ').trim()).toBe(
      `${CONSENT_HINWEIS.vorLink}${CONSENT_HINWEIS.link}${CONSENT_HINWEIS.nachLink}`,
    );
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
});
