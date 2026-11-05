import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';

import { NICHT_GELADEN, ORIGINAL_NICHT_DA, VariantenComponent, alsKarte } from './varianten.component';
import { VariantenAntwort, VariantenService } from '../services/varianten.service';
import { LoggingService } from '../services/logging.service';

function beitrag(id: string, titel: string, result_type = 'commentary'): any {
  return {
    id,
    title: titel,
    text: `Text zu ${titel}`,
    content_type: result_type,
    created: '2026-11-01T10:00:00Z',
    status: 'visible',
    references: [],
    references_count: 0,
    usage_count: 0,
    varianten: 0,
    result_type,
  };
}

describe('VariantenComponent (#356)', () => {
  let fixture: ComponentFixture<VariantenComponent>;
  let service: jasmine.SpyObj<VariantenService>;

  async function oeffnen(antwort: ReturnType<VariantenService['laden']>): Promise<void> {
    service = jasmine.createSpyObj('VariantenService', ['laden']);
    service.laden.and.returnValue(antwort);
    await TestBed.configureTestingModule({
      imports: [VariantenComponent],
      providers: [
        { provide: VariantenService, useValue: service },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['warn']) },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ id: 'o-1' })) } },
      ],
      // Die Karten selbst prueft beitragskarte.component.spec.ts.
      schemas: [NO_ERRORS_SCHEMA],
    })
      .overrideComponent(VariantenComponent, { set: { imports: [CommonModule], schemas: [NO_ERRORS_SCHEMA] } })
      .compileComponents();
    fixture = TestBed.createComponent(VariantenComponent);
    fixture.detectChanges();
  }

  function seite(): HTMLElement {
    return fixture.nativeElement;
  }

  it('zeigt das Original und seine Varianten', async () => {
    const antwort: VariantenAntwort = {
      original: beitrag('o-1', 'Original'),
      varianten: [beitrag('v-1', 'Erste'), beitrag('v-2', 'Zweite')],
    };
    await oeffnen(of(antwort));

    expect(service.laden).toHaveBeenCalledWith('o-1');
    expect(fixture.componentInstance.original!.titel).toBe('Original');
    expect(fixture.componentInstance.varianten.map((k) => k.id)).toEqual(['v-1', 'v-2']);
    expect(seite().textContent).toContain('2 Varianten');
  });

  it('sagt es, wenn es noch keine gibt', async () => {
    await oeffnen(of({ original: beitrag('o-1', 'Original'), varianten: [] }));

    expect(seite().textContent).toContain('Noch keine Varianten.');
  });

  it('nennt ein Original, das es nicht mehr gibt', async () => {
    await oeffnen(throwError(() => ({ status: 404 })));

    expect(seite().querySelector('.hinweis')!.textContent).toContain(ORIGINAL_NICHT_DA);
  });

  it('meldet andere Fehler allgemein', async () => {
    await oeffnen(throwError(() => ({ status: 500 })));

    expect(seite().querySelector('.hinweis')!.textContent).toContain(NICHT_GELADEN);
  });

  it('macht aus einem Beitrag eine Karte seines Typs', () => {
    expect(alsKarte(beitrag('g-1', 'Info', 'generic_text'))!.typ).toBe('generictext');
    expect(alsKarte({ ...beitrag('x', 'X'), result_type: 'unbekannt' })).toBeNull();
  });
});
