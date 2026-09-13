import { ComponentFixture, TestBed, fakeAsync, flush, tick } from '@angular/core/testing';
import { AddCommentaryComponent } from './add-commentary.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { CommentaryService } from '../services/commentary.service';
import { AddCommentaryRequest, AddCommentaryResponse } from '../services/dtos/commentaryDtos';
import { CommentaryResult } from '../services/dtos/searchDtos';
import { SimpleChange } from '@angular/core';

describe('AddCommentaryComponent', () => {
  let component: AddCommentaryComponent;
  let fixture: ComponentFixture<AddCommentaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AddCommentaryComponent,
        NoopAnimationsModule,
        MatDialogModule,
        MatSnackBarModule
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({}),
            queryParams: of({}),
            snapshot: {
              params: {},
              queryParams: {}
            }
          }
        }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AddCommentaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('verlinkt die Nutzungsbedingungen ueber dem Absenden-Knopf', () => {
    const link: HTMLAnchorElement | null = fixture.nativeElement.querySelector(
      'a[href="/nutzungsbedingungen"]'
    );

    expect(link).toBeTruthy();
    expect(link!.target).toBe('_blank');
  });

  // Titel = Behauptung in einem Satz. Das Limit ist auf die Titelbox der
  // Suchkarte ausgemessen und muss mit dem Backend-Modell uebereinstimmen.
  it('begrenzt den Titel auf 120 Zeichen', () => {
    const titel = component.commentaryForm.get('title')!;

    titel.setValue('a'.repeat(120));
    expect(titel.hasError('maxlength')).toBeFalse();

    titel.setValue('a'.repeat(121));
    expect(titel.hasError('maxlength')).toBeTrue();

    const input: HTMLInputElement = fixture.nativeElement.querySelector('input#title');
    expect(input.maxLength).toBe(120);
  });

  it('fragt im Titelfeld nach dem Punkt in einem Satz', () => {
    expect(fixture.nativeElement.textContent).toContain('Was ist der Punkt? Ein Satz.');
  });

  it('should keep long_text in the payload after the text variants section is collapsed again', fakeAsync(() => {
    const commentaryService = TestBed.inject(CommentaryService);
    const addSpy = spyOn(commentaryService, 'addCommentary')
      .and.returnValue(of({ id: 'commentary-1' } as AddCommentaryResponse));
    spyOn(commentaryService, 'getCommentaryById')
      .and.returnValue(of({} as CommentaryResult));

    component.commentaryForm.patchValue({
      title: 'Testtitel',
      text: 'Ein ausreichend langer Haupttext.'
    });

    const toggle: HTMLButtonElement = fixture.nativeElement.querySelector('.optional-toggle');
    expect(toggle).toBeTruthy();

    // Expand the optional section and fill the long text
    toggle.click();
    fixture.detectChanges();
    tick();

    const longText: HTMLTextAreaElement =
      fixture.nativeElement.querySelector('textarea[formControlName="long_text"]');
    expect(longText).toBeTruthy();
    longText.value = 'Ausführliche Fassung des Kommentars.';
    longText.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    // Collapse it again - the field leaves the DOM
    toggle.click();
    fixture.detectChanges();
    tick();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('textarea[formControlName="long_text"]')).toBeNull();

    component.saveCommentaryForm();
    flush();

    expect(addSpy).toHaveBeenCalled();
    const payload: AddCommentaryRequest = addSpy.calls.mostRecent().args[0];
    expect(payload.commentary.long_text).toBe('Ausführliche Fassung des Kommentars.');
  }));

  describe('Vorbefuellung aus dem Destillier-Ablauf', () => {
    function vorbefuellen(url: string | null): void {
      component.vorbefuellung = {
        rohinputId: 'id-1',
        titel: 'Waermepumpe lohnt sich auch im Altbau',
        url,
      };
      component.ngOnChanges({
        vorbefuellung: new SimpleChange(null, component.vorbefuellung, true),
      });
    }

    it('uebernimmt den Satz als Titel und den Link als Herkunft', () => {
      vorbefuellen('https://example.org/p');

      expect(component.commentaryForm.value.title).toBe('Waermepumpe lohnt sich auch im Altbau');
      expect(component.commentaryForm.value.references).toEqual([
        { reference_string: 'https://example.org/p' },
      ]);
      expect(component.showReferences).toBeTrue();
    });

    it('laesst die Quellen zu, wenn der Einwurf keinen Link hat', () => {
      vorbefuellen(null);

      expect(component.commentaryForm.value.title).toBe('Waermepumpe lohnt sich auch im Altbau');
      expect(component.commentaryForm.value.references).toEqual([]);
      expect(component.showReferences).toBeFalse();
    });
  });
});
