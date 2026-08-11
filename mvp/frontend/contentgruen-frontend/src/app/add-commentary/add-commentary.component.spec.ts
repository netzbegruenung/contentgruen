import { ComponentFixture, TestBed, fakeAsync, flush, tick } from '@angular/core/testing';
import { AddCommentaryComponent } from './add-commentary.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { CommentaryService } from '../services/commentary.service';
import { AddCommentaryRequest, AddCommentaryResponse } from '../services/dtos/commentaryDtos';
import { CommentaryResult } from '../services/dtos/searchDtos';

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
});
