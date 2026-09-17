import { TestBed } from '@angular/core/testing';
import { MatBottomSheet } from '@angular/material/bottom-sheet';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { BeitragAnsehenService } from './beitrag-ansehen.service';
import { BeitragSheetComponent } from '../beitragskarte/beitrag-sheet.component';
import { CommentaryService } from '../services/commentary.service';
import { GenericTextService } from '../services/generic-text.service';
import { LoggingService } from '../services/logging.service';

describe('BeitragAnsehenService', () => {
  let service: BeitragAnsehenService;
  let kommentare: jasmine.SpyObj<CommentaryService>;
  let hintergrund: jasmine.SpyObj<GenericTextService>;
  let sheet: jasmine.SpyObj<MatBottomSheet>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(() => {
    kommentare = jasmine.createSpyObj('CommentaryService', ['getCommentaryById']);
    hintergrund = jasmine.createSpyObj('GenericTextService', ['getGenericTextById']);
    sheet = jasmine.createSpyObj('MatBottomSheet', ['open']);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    TestBed.configureTestingModule({
      providers: [
        { provide: CommentaryService, useValue: kommentare },
        { provide: GenericTextService, useValue: hintergrund },
        { provide: MatBottomSheet, useValue: sheet },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['warn']) },
      ],
    });
    service = TestBed.inject(BeitragAnsehenService);
  });

  it('oeffnet einen Kommentar als Karte im Bottom Sheet', () => {
    kommentare.getCommentaryById.and.returnValue(of({ id: 'k-1', title: 'Titel', text: 'Text', references: [] } as any));

    service.oeffnen('k-1', 'commentary');

    expect(kommentare.getCommentaryById).toHaveBeenCalledOnceWith('k-1');
    expect(sheet.open).toHaveBeenCalledTimes(1);
    const [komponente, optionen] = sheet.open.calls.mostRecent().args as any[];
    expect(komponente).toBe(BeitragSheetComponent);
    expect(optionen.ariaLabel).toBe('Titel');
  });

  it('nimmt beide Schreibweisen der Hintergrundinfo', () => {
    hintergrund.getGenericTextById.and.returnValue(of({ id: 'h-1', title: 'H', text: 'T', references: [] } as any));

    expect(service.kannAnsehen('generic_text')).toBeTrue();
    service.oeffnen('h-1', 'generic_text');

    expect(hintergrund.getGenericTextById).toHaveBeenCalledOnceWith('h-1');
    expect(sheet.open).toHaveBeenCalled();
  });

  it('zeigt andere Typen nicht und meldet Ladefehler knapp', () => {
    expect(service.kannAnsehen('image')).toBeFalse();
    service.oeffnen('b-1', 'image');
    expect(sheet.open).not.toHaveBeenCalled();

    kommentare.getCommentaryById.and.returnValue(throwError(() => new Error('404')));
    service.oeffnen('k-weg', 'commentary');
    expect(snackBar.open).toHaveBeenCalled();
    expect(sheet.open).not.toHaveBeenCalled();
  });
});
