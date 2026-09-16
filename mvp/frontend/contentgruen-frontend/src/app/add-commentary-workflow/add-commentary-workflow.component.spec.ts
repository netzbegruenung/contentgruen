import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of } from 'rxjs';
import { AddCommentaryWorkflowComponent } from './add-commentary-workflow.component';
import { AddCommentaryComponent } from '../add-commentary/add-commentary.component';
import { DestillierUebergabeService } from '../destillieren/destillier-uebergabe.service';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { environment } from '../../environments/environment';
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

    expect(uebergabe.nachSpeichern).toHaveBeenCalledWith('id-1', 'beitrag-1', 'commentary');
    expect(navigieren).not.toHaveBeenCalled();
  });

  it('fuehrt beim Abbrechen zurueck zum Einwurf', () => {
    component.onCancel();

    expect(uebergabe.zurueckZumEinwurf).toHaveBeenCalledWith('id-1');
  });
});

/**
 * Worauf der Kommentar antwortet, steht in der Adresse: ?aussage=<id> (aus der
 * Suche) oder ersatzweise ?searchQuery=. Beim Oeffnen wird keine Aussage angelegt.
 */
describe('AddCommentaryWorkflowComponent mit Aussage aus der Adresse', () => {
  let fixture: ComponentFixture<AddCommentaryWorkflowComponent>;
  let component: AddCommentaryWorkflowComponent;
  let http: HttpTestingController;

  const getByIdUrl = `${environment.baseUrl}/api/v1/statement/getById`;

  async function oeffnen(params: Record<string, string>): Promise<void> {
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
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(params) } }
        }
      ]
    })
    .compileComponents();

    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AddCommentaryWorkflowComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function formular(): AddCommentaryComponent | null {
    return fixture.debugElement.query(By.directive(AddCommentaryComponent))?.componentInstance ?? null;
  }

  afterEach(() => http.verify());

  it('laedt die Aussage per ID und zeigt sie als Antwort-auf', async () => {
    await oeffnen({ aussage: 'a-1' });

    expect(formular()).withContext('Formular erst nach dem Laden').toBeNull();
    const anfrage = http.expectOne((req) => req.url === getByIdUrl);
    expect(anfrage.request.params.get('statement_id')).toBe('a-1');
    anfrage.flush({ statement_id: 'a-1', statement_text: 'Waermepumpen sind zu teuer' });
    fixture.detectChanges();

    expect(component.statementId).toBe('a-1');
    expect(formular()!.statementText).toBe('Waermepumpen sind zu teuer');
    expect(formular()!.isReplyToStatement).toBeTrue();
  });

  it('nimmt ?searchQuery= nur als Text und ruft dafuer nichts auf', async () => {
    await oeffnen({ searchQuery: 'Waermepumpen sind zu teuer' });

    // Kein searchStatements, kein addStatement - http.verify() im afterEach.
    expect(component.statementId).toBe('');
    expect(formular()!.statementInput).toBe('Waermepumpen sind zu teuer');
    expect(formular()!.isReplyToStatement).toBeTrue();
  });

  it('zeigt einen Fehler mit erneutem Versuch, wenn die Aussage nicht ladbar ist', async () => {
    await oeffnen({ aussage: 'a-404' });

    http.expectOne((req) => req.url === getByIdUrl).flush('weg', { status: 404, statusText: 'Not Found' });
    fixture.detectChanges();

    expect(formular()).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('konnte nicht geladen werden');

    (fixture.nativeElement.querySelector('.error-container button') as HTMLButtonElement).click();
    http.expectOne((req) => req.url === getByIdUrl).flush({ statement_id: 'a-404', statement_text: 'Doch da' });
    fixture.detectChanges();

    expect(formular()!.statementText).toBe('Doch da');
  });

  it('oeffnet ohne Parameter ein eigenstaendiges Formular', async () => {
    await oeffnen({});

    expect(formular()!.isReplyToStatement).toBeFalse();
  });
});
