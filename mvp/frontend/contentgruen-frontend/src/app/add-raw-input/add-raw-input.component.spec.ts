import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AddRawInputComponent, einwurfZerlegen } from './add-raw-input.component';
import { RawInputService } from '../services/raw-input.service';
import { SHARE_EINWURF_SCHLUESSEL } from '../share-target/share-target.guard';
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

  it('entfernt Tracking-Parameter auch aus einer von Hand eingefuegten Adresse', () => {
    component.einwurfForm.setValue({
      einwurf: 'https://www.instagram.com/reel/ABC/?stkn=xyz',
      imageUrl: '',
    });

    component.einwerfen();

    expect(rawInputService.addRawInput).toHaveBeenCalledWith({
      url: 'https://www.instagram.com/reel/ABC/',
    });
  });

  it('behaelt die Eingabe, wenn das Speichern fehlschlaegt', () => {
    rawInputService.addRawInput.and.returnValue(throwError(() => ({ status: 500 })));
    component.einwurfForm.setValue({ einwurf: 'nicht verlieren', imageUrl: '' });

    component.einwerfen();

    expect(component.einwurfForm.value.einwurf).toBe('nicht verlieren');
    expect(component.eingeworfen).toBe(0);
  });
});

describe('AddRawInputComponent: Uebernahme aus dem Teilen-Menue', () => {
  let component: AddRawInputComponent;
  let fixture: ComponentFixture<AddRawInputComponent>;
  let rawInputService: jasmine.SpyObj<RawInputService>;

  /**
   * Die Vorbelegung passiert in ngOnInit, also muss der Wert liegen, bevor die
   * Komponente entsteht -- deshalb hier kein Aufbau in beforeEach, sondern eine
   * Funktion, die jeder Test selbst aufruft.
   */
  async function komponenteMitAblage(einwurf: string | null): Promise<void> {
    if (einwurf === null) {
      sessionStorage.removeItem(SHARE_EINWURF_SCHLUESSEL);
    } else {
      sessionStorage.setItem(SHARE_EINWURF_SCHLUESSEL, einwurf);
    }

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
  }

  beforeEach(() => TestBed.resetTestingModule());

  afterEach(() => sessionStorage.removeItem(SHARE_EINWURF_SCHLUESSEL));

  it('befuellt das Feld mit dem geteilten Einwurf', async () => {
    await komponenteMitAblage('https://www.instagram.com/reel/ABC/');

    expect(component.einwurfForm.value.einwurf).toBe('https://www.instagram.com/reel/ABC/');
    expect(component.ausShare).toBeTrue();
  });

  it('raeumt die Ablage weg, damit der naechste Aufruf leer beginnt', async () => {
    await komponenteMitAblage('https://example.org/a');

    expect(sessionStorage.getItem(SHARE_EINWURF_SCHLUESSEL)).toBeNull();
  });

  it('schickt share als Herkunftskanal mit', async () => {
    await komponenteMitAblage('https://example.org/a');

    component.einwerfen();

    expect(rawInputService.addRawInput).toHaveBeenCalledWith({
      url: 'https://example.org/a',
      source_channel: 'share',
    });
  });

  it('uebernimmt Titel und Adresse getrennt in content und url', async () => {
    await komponenteMitAblage('Ein Seitentitel\nhttps://example.org/a');

    component.einwerfen();

    expect(rawInputService.addRawInput).toHaveBeenCalledWith({
      url: 'https://example.org/a',
      content: 'Ein Seitentitel\nhttps://example.org/a',
      source_channel: 'share',
    });
  });

  it('zaehlt den naechsten Einwurf wieder als web', async () => {
    await komponenteMitAblage('https://example.org/a');
    component.einwerfen();

    component.einwurfForm.setValue({ einwurf: 'von Hand getippt', imageUrl: '' });
    component.einwerfen();

    expect(rawInputService.addRawInput.calls.mostRecent().args[0]).toEqual({
      content: 'von Hand getippt',
    });
  });

  it('befuellt nichts, wenn nichts abgelegt wurde', async () => {
    await komponenteMitAblage(null);

    expect(component.einwurfForm.value.einwurf).toBe('');
    expect(component.ausShare).toBeFalse();
  });
});
