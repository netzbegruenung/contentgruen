import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { RawInputListComponent } from './raw-input-list.component';
import { RawInput, RawInputService } from '../services/raw-input.service';
import { LoggingService } from '../services/logging.service';

function einwurf(overrides: Partial<RawInput> = {}): RawInput {
  return {
    id: 'id-1',
    content: 'ein Satz',
    url: null,
    image_url: null,
    submitted_by: 'testuser',
    source_channel: 'web',
    status: 'open',
    created_at: '2026-08-19T12:00:00Z',
    ...overrides,
  };
}

describe('RawInputListComponent', () => {
  let component: RawInputListComponent;
  let fixture: ComponentFixture<RawInputListComponent>;
  let rawInputService: jasmine.SpyObj<RawInputService>;

  beforeEach(async () => {
    const serviceSpy = jasmine.createSpyObj('RawInputService', ['getRawInputs']);
    serviceSpy.getRawInputs.and.returnValue(
      of({ results_count: 0, results: [], total_records_count: 0 }),
    );
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn']);

    await TestBed.configureTestingModule({
      imports: [RawInputListComponent, BrowserAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: RawInputService, useValue: serviceSpy },
        { provide: LoggingService, useValue: loggingSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RawInputListComponent);
    component = fixture.componentInstance;
    rawInputService = TestBed.inject(RawInputService) as jasmine.SpyObj<RawInputService>;
  });

  it('wird erstellt und laedt die erste Seite', () => {
    fixture.detectChanges();

    expect(component).toBeTruthy();
    expect(rawInputService.getRawInputs).toHaveBeenCalledWith(1, 20);
    expect(component.isLoading).toBeFalse();
  });

  it('zeigt die Einwuerfe', () => {
    rawInputService.getRawInputs.and.returnValue(
      of({
        results_count: 2,
        results: [einwurf({ content: 'a' }), einwurf({ id: 'id-2', content: 'b' })],
        total_records_count: 2,
      }),
    );

    fixture.detectChanges();

    expect(component.dataSource.data.length).toBe(2);
    expect(component.totalRecords).toBe(2);
  });

  it('meldet einen Ladefehler statt still leer zu bleiben', () => {
    rawInputService.getRawInputs.and.returnValue(throwError(() => new Error('kaputt')));

    fixture.detectChanges();

    expect(component.ladefehler).toBeTrue();
    expect(component.isLoading).toBeFalse();
  });

  it('rechnet beim Seitenwechsel auf eins-basierte Seiten um', () => {
    fixture.detectChanges();

    component.onPageChange({ pageIndex: 2, pageSize: 50, length: 100 });

    expect(rawInputService.getRawInputs).toHaveBeenCalledWith(3, 50);
  });

  describe('Darstellung', () => {
    it('zeigt Text, sonst Link, sonst Bild', () => {
      expect(component.vorschau(einwurf({ content: 'Text' }))).toBe('Text');
      expect(
        component.vorschau(einwurf({ content: null, url: 'https://example.org' })),
      ).toBe('https://example.org');
      expect(
        component.vorschau(
          einwurf({ content: null, url: null, image_url: 'https://example.org/b.png' }),
        ),
      ).toBe('https://example.org/b.png');
    });

    it('benennt einen Einwurf ohne Kennung', () => {
      expect(component.einwerferBeschriftung(einwurf({ submitted_by: null }))).toBe(
        'ohne Kennung',
      );
    });

    it('uebersetzt alle Bearbeitungsstaende', () => {
      expect(component.statusBeschriftung('open')).toBe('Offen');
      expect(component.statusBeschriftung('in_progress')).toBe('In Arbeit');
      expect(component.statusBeschriftung('processed')).toBe('Verarbeitet');
      expect(component.statusBeschriftung('discarded')).toBe('Verworfen');
    });
  });
});
