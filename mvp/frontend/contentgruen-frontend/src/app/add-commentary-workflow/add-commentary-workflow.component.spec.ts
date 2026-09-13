import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of } from 'rxjs';
import { AddCommentaryWorkflowComponent } from './add-commentary-workflow.component';
import { AddCommentaryComponent } from '../add-commentary/add-commentary.component';
import { DestillierUebergabeService } from '../destillieren/destillier-uebergabe.service';
import { provideRouter, Router } from '@angular/router';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';

describe('AddCommentaryWorkflowComponent', () => {
  let component: AddCommentaryWorkflowComponent;
  let fixture: ComponentFixture<AddCommentaryWorkflowComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AddCommentaryWorkflowComponent,
        HttpClientTestingModule,
        BrowserAnimationsModule,
        MatDialogModule,
        MatSnackBarModule
      ],
      providers: [
        // Echter Router statt Stub: das eingebettete Formular verlinkt seit dem
        // Hinweis ueber dem Absenden-Knopf die Nutzungsbedingungen per routerLink.
        provideRouter([])
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AddCommentaryWorkflowComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('ist ausserhalb des Destillier-Ablaufs nicht vorbefuellt', () => {
    expect(component.rohinputId).toBeNull();
    expect(component.vorbefuellung).toBeNull();
  });
});

describe('AddCommentaryWorkflowComponent im Destillier-Ablauf', () => {
  let component: AddCommentaryWorkflowComponent;
  let fixture: ComponentFixture<AddCommentaryWorkflowComponent>;
  let uebergabe: jasmine.SpyObj<DestillierUebergabeService>;

  beforeEach(async () => {
    uebergabe = jasmine.createSpyObj('DestillierUebergabeService', [
      'rohinputId',
      'vorbefuellungLaden',
      'nachSpeichern',
      'zurueckZumEinwurf',
    ]);
    uebergabe.rohinputId.and.returnValue('id-1');
    uebergabe.vorbefuellungLaden.and.returnValue(
      of({
        rohinputId: 'id-1',
        titel: 'Waermepumpe lohnt sich auch im Altbau',
        url: 'https://example.org/p',
      }),
    );

    await TestBed.configureTestingModule({
      imports: [
        AddCommentaryWorkflowComponent,
        HttpClientTestingModule,
        BrowserAnimationsModule,
        MatDialogModule,
        MatSnackBarModule
      ],
      providers: [
        provideRouter([]),
        { provide: DestillierUebergabeService, useValue: uebergabe }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AddCommentaryWorkflowComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fuellt das Formular aus dem Einwurf vor', () => {
    const formular = fixture.debugElement.query(By.directive(AddCommentaryComponent))
      .componentInstance as AddCommentaryComponent;

    expect(uebergabe.vorbefuellungLaden).toHaveBeenCalledWith('id-1');
    expect(formular.commentaryForm.value.title).toBe('Waermepumpe lohnt sich auch im Altbau');
    expect(formular.showReferences).toBeTrue();
  });

  it('markiert nach dem Speichern und springt weiter statt nach /contribute', () => {
    const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

    component.onSuccess('beitrag-1');

    expect(uebergabe.nachSpeichern).toHaveBeenCalledWith('id-1', 'beitrag-1');
    expect(navigieren).not.toHaveBeenCalled();
  });

  it('fuehrt beim Abbrechen zurueck zum Einwurf', () => {
    component.onCancel();

    expect(uebergabe.zurueckZumEinwurf).toHaveBeenCalledWith('id-1');
  });
});
