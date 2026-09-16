import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_BOTTOM_SHEET_DATA } from '@angular/material/bottom-sheet';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Subject, of, throwError } from 'rxjs';

import { EinwurfBeitragSheetComponent } from './einwurf-beitrag-sheet.component';
import { RohlingBeitrag } from '../beitragskarte/karten-daten';
import { CommentaryService } from '../services/commentary.service';
import { GenericTextService } from '../services/generic-text.service';
import { LoggingService } from '../services/logging.service';

function beitrag(overrides: Partial<RohlingBeitrag> = {}): RohlingBeitrag {
  return { contentId: 'c-1', typ: 'commentary', satz: 'Ein Satz', ...overrides };
}

function inhalt(id: string, title: string): any {
  return {
    id,
    title,
    text: 'Text des Beitrags',
    content_type: 'commentary',
    created: '2026-09-13T12:00:00Z',
    last_modified: '2026-09-13T12:00:00Z',
    original_author: 'alice',
    last_modified_by: 'alice',
    references: [],
    usage_count: 0,
  };
}

describe('EinwurfBeitragSheetComponent', () => {
  let commentary: jasmine.SpyObj<CommentaryService>;
  let genericText: jasmine.SpyObj<GenericTextService>;

  async function erstellen(
    beitraege: RohlingBeitrag[],
  ): Promise<ComponentFixture<EinwurfBeitragSheetComponent>> {
    await TestBed.configureTestingModule({
      imports: [EinwurfBeitragSheetComponent, NoopAnimationsModule],
      providers: [
        // Das Sheet zeigt die volle Beitragskarte, und die zieht ueber die
        // Nutzungserfassung einen HttpClient nach.
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_BOTTOM_SHEET_DATA, useValue: { beitraege } },
        { provide: CommentaryService, useValue: commentary },
        { provide: GenericTextService, useValue: genericText },
        {
          provide: LoggingService,
          useValue: jasmine.createSpyObj('LoggingService', ['debug', 'error', 'warn', 'info']),
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(EinwurfBeitragSheetComponent);
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => {
    commentary = jasmine.createSpyObj('CommentaryService', ['getCommentaryById']);
    genericText = jasmine.createSpyObj('GenericTextService', ['getGenericTextById']);
  });

  it('laedt bei genau einem Beitrag sofort', async () => {
    commentary.getCommentaryById.and.returnValue(of(inhalt('c-1', 'Der Beitrag')));
    const fixture = await erstellen([beitrag()]);

    expect(commentary.getCommentaryById).toHaveBeenCalledOnceWith('c-1');
    expect(fixture.componentInstance.karte!.titel).toBe('Der Beitrag');
    expect(fixture.componentInstance.laedt).toBeFalse();
  });

  /**
   * Wer in der Auswahl weiterklickt, waehrend die erste Anfrage noch laeuft, darf
   * nicht die alte Antwort zu sehen bekommen - auch dann nicht, wenn sie spaeter
   * eintrifft als die neue.
   */
  it('verwirft die Antwort einer abgeloesten Anfrage, auch wenn sie zuletzt kommt', async () => {
    const langsam = new Subject<any>();
    const schnell = new Subject<any>();
    commentary.getCommentaryById.and.returnValues(langsam, schnell);
    const fixture = await erstellen([beitrag({ contentId: 'c-1' }), beitrag({ contentId: 'c-2' })]);
    const komponente = fixture.componentInstance;

    komponente.oeffnen(beitrag({ contentId: 'c-1', satz: 'Erster' }));
    komponente.oeffnen(beitrag({ contentId: 'c-2', satz: 'Zweiter' }));

    schnell.next(inhalt('c-2', 'Zweiter Beitrag'));
    schnell.complete();
    langsam.next(inhalt('c-1', 'Erster Beitrag'));
    langsam.complete();
    fixture.detectChanges();

    expect(komponente.karte!.id).toBe('c-2');
    expect(komponente.karte!.titel).toBe('Zweiter Beitrag');
  });

  it('zeigt eine Zeile statt eines leeren Sheets, wenn der Beitrag weg ist', async () => {
    commentary.getCommentaryById.and.returnValue(throwError(() => ({ status: 404 })));
    const fixture = await erstellen([beitrag()]);

    expect(fixture.componentInstance.fehler).toBeTrue();
    expect(fixture.nativeElement.querySelector('.sheet-fehler').textContent).toContain(
      'nicht mehr verfügbar',
    );
  });

  it('zeigt ohne bekannten Typ dieselbe Zeile und fragt keinen Endpunkt', async () => {
    const fixture = await erstellen([beitrag({ typ: null })]);

    expect(commentary.getCommentaryById).not.toHaveBeenCalled();
    expect(genericText.getGenericTextById).not.toHaveBeenCalled();
    expect(fixture.componentInstance.fehler).toBeTrue();
  });

  it('bietet bei mehreren Beitraegen erst die Auswahl', async () => {
    const fixture = await erstellen([
      beitrag({ contentId: 'c-1', satz: 'Erster' }),
      beitrag({ contentId: 'c-2', satz: 'Zweiter' }),
    ]);

    expect(commentary.getCommentaryById).not.toHaveBeenCalled();
    const knoepfe = Array.from(
      fixture.nativeElement.querySelectorAll('.auswahl-knopf') as NodeListOf<HTMLElement>,
    ).map((knopf) => knopf.textContent!.trim());
    expect(knoepfe).toEqual(['Erster', 'Zweiter']);
  });
});
