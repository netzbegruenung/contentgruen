import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { BehaviorSubject, of } from 'rxjs';
import { AddCommentaryWorkflowComponent } from './add-commentary-workflow.component';
import { AddCommentaryComponent } from '../add-commentary/add-commentary.component';
import { DestillierUebergabeService } from '../destillieren/destillier-uebergabe.service';
import { ActivatedRoute, ParamMap, convertToParamMap, provideRouter, Router } from '@angular/router';
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
      'vorbefuellungLaden',
      'nachSpeichern',
      'zurueckZumEinwurf',
    ]);
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
        { provide: DestillierUebergabeService, useValue: uebergabe },
        { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap({ rohinput: 'id-1' })) } }
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
  let adresse: BehaviorSubject<ParamMap>;

  const getByIdUrl = `${environment.baseUrl}/api/v1/statement/getById`;

  async function oeffnen(params: Record<string, string>): Promise<void> {
    adresse = new BehaviorSubject(convertToParamMap(params));
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
        { provide: ActivatedRoute, useValue: { queryParamMap: adresse.asObservable() } }
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

  for (const [fall, status] of [['404', 404], ['422', 422], ['Netzfehler', 0]] as const) {
    it(`bleibt nutzbar, wenn die Aussage nicht ladbar ist (${fall})`, async () => {
      await oeffnen({ aussage: 'a-weg' });

      const anfrage = http.expectOne((req) => req.url === getByIdUrl);
      if (status === 0) {
        anfrage.error(new ProgressEvent('error'));
      } else {
        anfrage.flush('weg', { status, statusText: fall });
      }
      fixture.detectChanges();

      const seite: HTMLElement = fixture.nativeElement;
      expect(formular()).withContext('Formular trotz Ladefehler').toBeTruthy();
      expect(seite.querySelector('.aussage-hinweis')!.textContent).toContain('Die Aussage ist nicht mehr verfügbar');
      expect(seite.textContent).not.toContain('Erneut versuchen');
      expect(formular()!.isReplyToStatement).toBeTrue();
      expect(formular()!.statementInput).toBe('');
      expect(component.statementId).toBe('');
    });
  }

  it('zieht nach, wenn sich die Adresse bei offener Seite aendert', async () => {
    await oeffnen({ searchQuery: 'Erste Aussage' });
    expect(formular()!.statementInput).toBe('Erste Aussage');

    adresse.next(convertToParamMap({ aussage: 'a-2' }));
    http.expectOne((req) => req.url === getByIdUrl).flush({ statement_id: 'a-2', statement_text: 'Zweite Aussage' });
    fixture.detectChanges();

    expect(component.statementId).toBe('a-2');
    expect(formular()!.statementInput).toBe('Zweite Aussage');
  });

  it('oeffnet ohne Parameter ein eigenstaendiges Formular', async () => {
    await oeffnen({});

    expect(formular()!.isReplyToStatement).toBeFalse();
    expect(component.rohinputId).toBeNull();
  });
});
