import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AddRawInputComponent, einwurfZerlegen } from './add-raw-input.component';
import { RawInputService } from '../services/raw-input.service';
import { LoggingService } from '../services/logging.service';

describe('einwurfZerlegen', () => {
  it('erkennt einen reinen Link als Link', () => {
    expect(einwurfZerlegen('https://example.org/post')).toEqual({
      url: 'https://example.org/post',
    });
  });

  it('schneidet Leerraum vor der Erkennung ab', () => {
    expect(einwurfZerlegen('  https://example.org/post  ')).toEqual({
      url: 'https://example.org/post',
    });
  });

  it('behaelt bei Link mit Notiz beides', () => {
    const ergebnis = einwurfZerlegen('Guter Thread https://example.org/p zu Waermepumpen');

    expect(ergebnis.url).toBe('https://example.org/p');
    expect(ergebnis.content).toBe('Guter Thread https://example.org/p zu Waermepumpen');
  });

  it('behandelt einen Satz ohne Link als Text', () => {
    expect(einwurfZerlegen('Waermepumpen-Foerderung wurde gekuerzt')).toEqual({
      content: 'Waermepumpen-Foerderung wurde gekuerzt',
    });
  });
});

describe('AddRawInputComponent', () => {
  let component: AddRawInputComponent;
  let fixture: ComponentFixture<AddRawInputComponent>;
  let rawInputService: jasmine.SpyObj<RawInputService>;

  beforeEach(async () => {
    const serviceSpy = jasmine.createSpyObj('RawInputService', ['addRawInput']);
    serviceSpy.addRawInput.and.returnValue(of({ id: 'neue-id' }));
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']);

    await TestBed.configureTestingModule({
      imports: [AddRawInputComponent, BrowserAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: RawInputService, useValue: serviceSpy },
        { provide: LoggingService, useValue: loggingSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AddRawInputComponent);
    component = fixture.componentInstance;
    rawInputService = TestBed.inject(RawInputService) as jasmine.SpyObj<RawInputService>;
    fixture.detectChanges();
  });

  it('wird erstellt', () => {
    expect(component).toBeTruthy();
  });

  it('wirft nichts ein, solange nichts dasteht', () => {
    component.einwurfForm.setValue({ einwurf: '   ', imageUrl: '' });

    component.einwerfen();

    expect(rawInputService.addRawInput).not.toHaveBeenCalled();
  });

  it('schickt einen Satz als Text', () => {
    component.einwurfForm.setValue({ einwurf: 'Ein guter Fund', imageUrl: '' });

    component.einwerfen();

    expect(rawInputService.addRawInput).toHaveBeenCalledWith({ content: 'Ein guter Fund' });
  });

  it('nimmt eine Bild-Adresse allein an', () => {
    component.einwurfForm.setValue({
      einwurf: '',
      imageUrl: 'https://example.org/bild.png',
    });

    component.einwerfen();

    expect(rawInputService.addRawInput).toHaveBeenCalledWith({
      image_url: 'https://example.org/bild.png',
    });
  });

  it('laesst das Formular nach dem Einwerfen offen und leer', () => {
    component.einwurfForm.setValue({ einwurf: 'Ein guter Fund', imageUrl: '' });

    component.einwerfen();

    expect(component.einwurfForm.value.einwurf).toBe('');
    expect(component.eingeworfen).toBe(1);
    expect(component.fehler).toBeNull();
  });

  it('zaehlt mehrere Einwuerfe in einer Sitzung', () => {
    component.einwurfForm.setValue({ einwurf: 'eins', imageUrl: '' });
    component.einwerfen();
    component.einwurfForm.setValue({ einwurf: 'zwei', imageUrl: '' });
    component.einwerfen();

    expect(component.eingeworfen).toBe(2);
  });

  it('meldet einen abgewiesenen Einwurf verstaendlich', () => {
    rawInputService.addRawInput.and.returnValue(throwError(() => ({ status: 422 })));
    component.einwurfForm.setValue({ einwurf: 'x', imageUrl: '' });

    component.einwerfen();

    expect(component.fehler).toContain('Adresse');
    expect(component.wirdGespeichert).toBeFalse();
  });

  it('behaelt die Eingabe, wenn das Speichern fehlschlaegt', () => {
    rawInputService.addRawInput.and.returnValue(throwError(() => ({ status: 500 })));
    component.einwurfForm.setValue({ einwurf: 'nicht verlieren', imageUrl: '' });

    component.einwerfen();

    expect(component.einwurfForm.value.einwurf).toBe('nicht verlieren');
    expect(component.eingeworfen).toBe(0);
  });
});
