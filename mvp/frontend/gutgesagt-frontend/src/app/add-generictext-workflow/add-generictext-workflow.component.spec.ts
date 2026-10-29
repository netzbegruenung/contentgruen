import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { BehaviorSubject, Subject, of } from 'rxjs';
import {
  AddGenerictextWorkflowComponent,
  EINWURF_MIT_VORHANDENER_VERKNUEPFT,
  EINWURF_NICHT_VERKNUEPFT,
  ERNEUT_VERKNUEPFEN,
} from './add-generictext-workflow.component';
import { AddGenerictextComponent } from '../add-generictext/add-generictext.component';
import { DestillierUebergabeService } from '../destillieren/destillier-uebergabe.service';
import { ActivatedRoute, ParamMap, convertToParamMap, provideRouter, Router } from '@angular/router';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { environment } from '../../environments/environment';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

describe('AddGenerictextWorkflowComponent', () => {
  let component: AddGenerictextWorkflowComponent;
  let fixture: ComponentFixture<AddGenerictextWorkflowComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AddGenerictextWorkflowComponent,
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

    fixture = TestBed.createComponent(AddGenerictextWorkflowComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('ist ausserhalb des Destillier-Ablaufs nicht vorbefuellt', () => {
    expect(component.einwurfId).toBeNull();
    expect(component.vorbefuellung).toBeNull();
  });

  it('macht nach der Wahl der vorhandenen ohne Einwurf nichts weiter', () => {
    const navigieren = spyOn(TestBed.inject(Router), 'navigate');
    const verknuepfen = spyOn(TestBed.inject(DestillierUebergabeService), 'mitBeitragVerknuepfen');

    component.onVorhandenGewaehlt('h-alt');

    expect(verknuepfen).not.toHaveBeenCalled();
    expect(navigieren).not.toHaveBeenCalled();
  });

  it('oeffnet nach dem Speichern die Ergebnisseite und ersetzt das Formular im Verlauf', () => {
    const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

    component.onSuccess({ id: 'beitrag-1', aussage: { id: '', text: '' }, verknuepft: true });

    expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-generictext', 'gespeichert', 'beitrag-1'], {
      queryParams: {},
      state: { aussage: undefined, verknuepft: true },
      replaceUrl: true,
    });
  });
});

describe('AddGenerictextWorkflowComponent im Destillier-Ablauf', () => {
  let component: AddGenerictextWorkflowComponent;
  let fixture: ComponentFixture<AddGenerictextWorkflowComponent>;
  let uebergabe: jasmine.SpyObj<DestillierUebergabeService>;

  beforeEach(async () => {
    uebergabe = jasmine.createSpyObj('DestillierUebergabeService', [
      'vorbefuellungLaden',
      'mitBeitragVerknuepfen',
      'zumNaechsten',
    ]);
    uebergabe.mitBeitragVerknuepfen.and.returnValue(of(true));
    uebergabe.vorbefuellungLaden.and.returnValue(
      of({
        einwurfId: 'id-1',
        titel: 'Waermepumpe lohnt sich auch im Altbau',
        url: 'https://example.org/p',
        kopf: { id: 'id-1', typ: null, titel: null, text: null, erstellt: '', autor: null, autorName: null, nutzung: null, quellen: [] },
      }),
    );

    await TestBed.configureTestingModule({
      imports: [
        AddGenerictextWorkflowComponent,
        HttpClientTestingModule,
        BrowserAnimationsModule,
        MatDialogModule,
        MatSnackBarModule
      ],
      providers: [
        provideRouter([]),
        { provide: DestillierUebergabeService, useValue: uebergabe },
        { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap({ einwurf: 'id-1' })) } }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AddGenerictextWorkflowComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fuellt das Formular aus dem Einwurf vor', () => {
    const formular = fixture.debugElement.query(By.directive(AddGenerictextComponent))
      .componentInstance as AddGenerictextComponent;

    expect(uebergabe.vorbefuellungLaden).toHaveBeenCalledWith('id-1');
    expect(formular.generictextForm.value.title).toBe('Waermepumpe lohnt sich auch im Altbau');
    expect(formular.showReferences).toBeTrue();
  });

  it('verknuepft den Einwurf nach dem Speichern und zeigt die Ergebnisseite mit Herkunft Fangkorb', () => {
    const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

    component.onSuccess({ id: 'beitrag-1', aussage: { id: 'a-1', text: 'Aussage' }, verknuepft: true });

    expect(uebergabe.mitBeitragVerknuepfen).toHaveBeenCalledWith('id-1', 'beitrag-1', 'generic_text');
    expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-generictext', 'gespeichert', 'beitrag-1'], {
      queryParams: { einwurf: 'id-1' },
      state: { aussage: { id: 'a-1', text: 'Aussage' }, verknuepft: true, einwurfVerknuepft: true },
      replaceUrl: true,
    });
  });

  it('verknuepft nach der Wahl den Einwurf mit der vorhandenen Hintergrundinfo und geht zum naechsten', () => {
    const navigieren = spyOn(TestBed.inject(Router), 'navigate');
    const meldung = spyOn(fixture.debugElement.injector.get(MatSnackBar), 'open');

    component.onVorhandenGewaehlt('h-alt');

    expect(uebergabe.mitBeitragVerknuepfen).toHaveBeenCalledOnceWith('id-1', 'h-alt', 'generic_text');
    expect(uebergabe.zumNaechsten).toHaveBeenCalledOnceWith('id-1', 'ausformulieren');
    expect(meldung).toHaveBeenCalledWith(EINWURF_MIT_VORHANDENER_VERKNUEPFT, 'OK', jasmine.anything());
    // Keine Ergebnisseite: gespeichert wurde nichts.
    expect(navigieren).not.toHaveBeenCalled();
  });

  it('bleibt nach der Wahl im Formular, wenn das Verknuepfen scheitert, und laesst es wiederholen', () => {
    uebergabe.mitBeitragVerknuepfen.and.returnValues(of(false), of(true));
    const erneut = new Subject<void>();
    const meldung = spyOn(fixture.debugElement.injector.get(MatSnackBar), 'open').and.returnValue({
      onAction: () => erneut,
    } as any);

    component.onVorhandenGewaehlt('h-alt');

    expect(uebergabe.zumNaechsten).not.toHaveBeenCalled();
    expect(meldung).toHaveBeenCalledWith(EINWURF_NICHT_VERKNUEPFT, ERNEUT_VERKNUEPFEN, jasmine.anything());

    erneut.next();

    expect(uebergabe.mitBeitragVerknuepfen).toHaveBeenCalledTimes(2);
    expect(uebergabe.zumNaechsten).toHaveBeenCalledOnceWith('id-1', 'ausformulieren');
  });

  it('reicht die Wahl im Formular an den Workflow weiter', () => {
    const formular = fixture.debugElement.query(By.directive(AddGenerictextComponent))
      .componentInstance as AddGenerictextComponent;
    spyOn(fixture.debugElement.injector.get(MatSnackBar), 'open');

    formular.vorhandenGewaehlt.emit('h-alt');

    expect(uebergabe.mitBeitragVerknuepfen).toHaveBeenCalledOnceWith('id-1', 'h-alt', 'generic_text');
  });
});

/**
 * Worauf die Hintergrundinfo antwortet, steht in der Adresse: ?aussage=<id> (aus der
 * Suche) oder ersatzweise ?searchQuery=. Beim Oeffnen wird keine Aussage angelegt.
 */
describe('AddGenerictextWorkflowComponent mit Aussage aus der Adresse', () => {
  let fixture: ComponentFixture<AddGenerictextWorkflowComponent>;
  let component: AddGenerictextWorkflowComponent;
  let http: HttpTestingController;
  let adresse: BehaviorSubject<ParamMap>;

  const getByIdUrl = `${environment.baseUrl}/api/v1/statement/getById`;

  async function oeffnen(params: Record<string, string>): Promise<void> {
    adresse = new BehaviorSubject(convertToParamMap(params));
    await TestBed.configureTestingModule({
      imports: [
        AddGenerictextWorkflowComponent,
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
    fixture = TestBed.createComponent(AddGenerictextWorkflowComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function formular(): AddGenerictextComponent | null {
    return fixture.debugElement.query(By.directive(AddGenerictextComponent))?.componentInstance ?? null;
  }

  afterEach(() => {
    // Die Themenliste laedt das Formular selbst (#455); sonst bleibt nichts offen.
    http.match((r) => r.url.endsWith('/api/v1/statement/themen'));
    http.verify();
  });

  it('laedt die Aussage per ID und zeigt sie als Antwort-auf', async () => {
    await oeffnen({ aussage: 'a-1' });

    expect(formular()).withContext('Formular erst nach dem Laden').toBeNull();
    const anfrage = http.expectOne((req) => req.url === getByIdUrl);
    expect(anfrage.request.params.get('statement_id')).toBe('a-1');
    anfrage.flush({ statement_id: 'a-1', statement_text: 'Waermepumpen sind zu teuer' });
    fixture.detectChanges();

    expect(component.statementId).toBe('a-1');
    expect(formular()!.statementText).toBe('Waermepumpen sind zu teuer');
    expect(formular()!.aussage.text).toBe('Waermepumpen sind zu teuer');
  });

  it('nimmt ?searchQuery= nur als Text und ruft dafuer nichts auf', async () => {
    await oeffnen({ searchQuery: 'Waermepumpen sind zu teuer' });

    // Kein searchStatements, kein addStatement - http.verify() im afterEach.
    expect(component.statementId).toBe('');
    expect(formular()!.aussage).toEqual({ id: '', text: 'Waermepumpen sind zu teuer' });
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
      expect(formular()!.aussage).toEqual({ id: '', text: '' });
      expect(component.statementId).toBe('');
    });
  }

  it('zieht nach, wenn sich die Adresse bei offener Seite aendert', async () => {
    await oeffnen({ searchQuery: 'Erste Aussage' });
    expect(formular()!.aussage.text).toBe('Erste Aussage');

    adresse.next(convertToParamMap({ aussage: 'a-2' }));
    http.expectOne((req) => req.url === getByIdUrl).flush({ statement_id: 'a-2', statement_text: 'Zweite Aussage' });
    fixture.detectChanges();

    expect(component.statementId).toBe('a-2');
    expect(formular()!.aussage.text).toBe('Zweite Aussage');
  });

  it('nennt der Ergebnisseite die Suche samt Anfrage', async () => {
    await oeffnen({ searchQuery: 'Waermepumpen sind zu teuer' });
    const navigieren = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);

    component.onSuccess({ id: 'k-1', aussage: { id: '', text: 'Waermepumpen sind zu teuer' }, verknuepft: true });

    expect(navigieren.calls.mostRecent().args[1]!.queryParams).toEqual({
      von: 'suche',
      suche: 'Waermepumpen sind zu teuer',
    });
  });

  it('oeffnet ohne Parameter ein eigenstaendiges Formular', async () => {
    await oeffnen({});

    expect(formular()!.aussage).toEqual({ id: '', text: '' });
    expect(component.einwurfId).toBeNull();
  });
});
