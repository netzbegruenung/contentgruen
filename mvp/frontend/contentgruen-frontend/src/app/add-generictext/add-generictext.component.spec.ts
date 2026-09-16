import { ComponentFixture, TestBed, fakeAsync, flush, tick } from '@angular/core/testing';
import { Subject, of } from 'rxjs';
import { GenericTextService } from '../services/generic-text.service';
import { AddGenericTextResponse } from '../services/dtos/generictextDtos';
import { StatementService, Verknuepfung } from '../services/statement.service';
import { SimpleChange } from '@angular/core';
import { AddGenerictextComponent } from './add-generictext.component';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';

describe('AddGenerictextComponent', () => {
  let component: AddGenerictextComponent;
  let fixture: ComponentFixture<AddGenerictextComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AddGenerictextComponent,
        BrowserAnimationsModule,
        MatSnackBarModule
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([])
      ]
    })
    .overrideComponent(AddGenerictextComponent, {
      remove: { imports: [BeitragskarteComponent] },
      add: { imports: [BeitragskarteStubComponent] },
    })
    .compileComponents();

    fixture = TestBed.createComponent(AddGenerictextComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('uebernimmt Satz und Link aus dem Destillier-Ablauf', () => {
    component.vorbefuellung = {
      rohinputId: 'id-1',
      titel: 'Erneuerbare senken Strompreise deutlich',
      url: 'https://example.org/studie',
    };
    component.ngOnChanges({
      vorbefuellung: new SimpleChange(null, component.vorbefuellung, true),
    });

    expect(component.generictextForm.value.title).toBe('Erneuerbare senken Strompreise deutlich');
    expect(component.generictextForm.value.references).toEqual([
      { reference_string: 'https://example.org/studie' },
    ]);
    expect(component.showReferences).toBeTrue();
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
    const titel = component.generictextForm.get('title')!;

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

  // Das Limit steht im Formularmodell und nicht nur als maxLength im
  // Template: das sperrt nur die Eingabe, vorbefuellte Werte kaemen sonst
  // ungeprueft durch.
  it('begrenzt den Text im Formular auf 2000 Zeichen', () => {
    const text = component.generictextForm.get('text')!;

    text.setValue('a'.repeat(2000));
    expect(text.hasError('maxlength')).toBeFalse();

    text.setValue('a'.repeat(2001));
    expect(text.hasError('maxlength')).toBeTrue();
  });

  describe('Antwort auf eine Aussage', () => {
    function aussageSetzen(text: string, id: string): void {
      component.statementText = text;
      component.statementId = id;
      component.ngOnChanges({ statementText: new SimpleChange('', text, true) });
    }

    function speichernMit(verknuepfung: Subject<Verknuepfung>): jasmine.Spy {
      spyOn(TestBed.inject(GenericTextService), 'addGenericText')
        .and.returnValue(of({ id: 'h-1' } as AddGenericTextResponse));
      const verknuepfen = spyOn(TestBed.inject(StatementService), 'alsAntwortVerknuepfen')
        .and.returnValue(verknuepfung.asObservable());
      component.generictextForm.patchValue({ title: 'Testtitel', text: 'Ein ausreichend langer Text.' });
      component.saveGenericTextForm();
      return verknuepfen;
    }

    it('leert Feld, Text und ID, wenn die Aussage aus der Adresse leer wird', () => {
      aussageSetzen('Waermepumpen sind zu teuer', 'a-1');

      component.statementText = '';
      component.statementId = 'a-1';
      component.ngOnChanges({ statementText: new SimpleChange('Waermepumpen sind zu teuer', '', false) });

      expect(component.statementText).toBe('');
      expect(component.statementInput).toBe('');
      expect(component.statementId).toBe('');
    });

    it('wartet die Verknuepfung ab, bevor es als gespeichert gilt', fakeAsync(() => {
      aussageSetzen('Waermepumpen sind zu teuer', 'a-1');
      const erfolg = spyOn(component.success, 'emit');
      const verknuepfung = new Subject<Verknuepfung>();

      const verknuepfen = speichernMit(verknuepfung);
      tick(3000);

      expect(verknuepfen).toHaveBeenCalledOnceWith('h-1', 'generic_text', 0.9, { id: 'a-1', text: 'Waermepumpen sind zu teuer' });
      expect(component.generictextSaved).toBeFalse();
      expect(erfolg).not.toHaveBeenCalled();

      verknuepfung.next('verknuepft');
      tick(2000);

      expect(component.generictextSaved).toBeTrue();
      expect(erfolg).toHaveBeenCalledOnceWith('h-1');
    }));

    it('nimmt den Text statt der alten ID, wenn die Aussage bearbeitet wurde', fakeAsync(() => {
      aussageSetzen('Waermepumpen sind zu teuer', 'a-1');
      component.statementInput = 'Waermepumpen lohnen sich doch';

      const verknuepfen = speichernMit(new Subject<Verknuepfung>());

      expect(verknuepfen).toHaveBeenCalledOnceWith('h-1', 'generic_text', 0.9, { id: '', text: 'Waermepumpen lohnen sich doch' });
      flush();
    }));

    it('zeigt eine gescheiterte Verknuepfung und springt erst mit Weiter weiter', fakeAsync(() => {
      aussageSetzen('Waermepumpen sind zu teuer', 'a-1');
      const erfolg = spyOn(component.success, 'emit');
      const verknuepfung = new Subject<Verknuepfung>();

      speichernMit(verknuepfung);
      verknuepfung.next('fehlgeschlagen');
      flush();
      fixture.detectChanges();

      expect(erfolg).not.toHaveBeenCalled();
      const hinweis: HTMLElement = fixture.nativeElement.querySelector('.verknuepfungs-fehler');
      expect(hinweis.textContent).toContain('nicht mit der Aussage verknüpft');

      (hinweis.querySelector('button') as HTMLButtonElement).click();
      expect(erfolg).toHaveBeenCalledOnceWith('h-1');
    }));
  });
});
