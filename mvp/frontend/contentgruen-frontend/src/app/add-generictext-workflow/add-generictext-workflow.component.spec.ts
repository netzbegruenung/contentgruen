import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';

import { AddGenerictextWorkflowComponent } from './add-generictext-workflow.component';
import { AddGenerictextComponent } from '../add-generictext/add-generictext.component';
import { environment } from '../../environments/environment';

describe('AddGenerictextWorkflowComponent mit Aussage aus der Adresse', () => {
  let fixture: ComponentFixture<AddGenerictextWorkflowComponent>;
  let component: AddGenerictextWorkflowComponent;
  let http: HttpTestingController;

  const getByIdUrl = `${environment.baseUrl}/api/v1/statement/getById`;

  async function oeffnen(params: Record<string, string>): Promise<void> {
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
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(params) } }
        }
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

  afterEach(() => http.verify());

  it('laedt die Aussage per ID', async () => {
    await oeffnen({ aussage: 'a-1' });

    http.expectOne((req) => req.url === getByIdUrl)
      .flush({ statement_id: 'a-1', statement_text: 'Waermepumpen sind zu teuer' });
    fixture.detectChanges();

    expect(component.statementId).toBe('a-1');
    expect(formular()!.statementText).toBe('Waermepumpen sind zu teuer');
    expect(formular()!.isReplyToStatement).toBeTrue();
  });

  it('nimmt ?searchQuery= nur als Text und ruft dafuer nichts auf', async () => {
    await oeffnen({ searchQuery: 'Waermepumpen sind zu teuer' });

    expect(component.statementId).toBe('');
    expect(formular()!.statementInput).toBe('Waermepumpen sind zu teuer');
  });

  it('ist ausserhalb des Destillier-Ablaufs nicht vorbefuellt', async () => {
    await oeffnen({});

    expect(component.rohinputId).toBeNull();
    expect(formular()!.isReplyToStatement).toBeFalse();
  });
});
