import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AddGenerictextComponent } from './add-generictext.component';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBarModule } from '@angular/material/snack-bar';

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
    .compileComponents();

    fixture = TestBed.createComponent(AddGenerictextComponent);
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
});
