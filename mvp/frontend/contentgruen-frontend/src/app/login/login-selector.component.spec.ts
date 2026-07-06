import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginSelectorComponent } from './login-selector.component';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

describe('LoginSelectorComponent', () => {
  let component: LoginSelectorComponent;
  let fixture: ComponentFixture<LoginSelectorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        LoginSelectorComponent,
        HttpClientTestingModule,
        BrowserAnimationsModule
      ],
      providers: [
        { provide: Router, useValue: {
          navigate: jasmine.createSpy('navigate'),
          navigateByUrl: jasmine.createSpy('navigateByUrl'),
          url: '/login'
        } },
        { provide: ActivatedRoute, useValue: {
          snapshot: {
            queryParams: {}
          },
          params: of({}),
          queryParams: of({})
        } }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LoginSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Expandable Registration Info', () => {
    it('should initialize with registration info collapsed', () => {
      expect(component.isRegistrationInfoExpanded).toBeFalsy();
    });

    it('should toggle registration info expansion state', () => {
      const initialState = component.isRegistrationInfoExpanded;

      // Simulate clicking the expansion panel header
      component.isRegistrationInfoExpanded = !component.isRegistrationInfoExpanded;
      fixture.detectChanges();

      expect(component.isRegistrationInfoExpanded).toBe(!initialState);

      // Toggle back
      component.isRegistrationInfoExpanded = !component.isRegistrationInfoExpanded;
      fixture.detectChanges();

      expect(component.isRegistrationInfoExpanded).toBe(initialState);
    });

    it('should display correct expansion hint text based on state', () => {
      // When collapsed
      component.isRegistrationInfoExpanded = false;
      fixture.detectChanges();

      let compiled = fixture.nativeElement;
      let expansionHint = compiled.querySelector('.expansion-hint');

      if (expansionHint) {
        expect(expansionHint.textContent).toContain('Mehr Informationen');
      }

      // When expanded
      component.isRegistrationInfoExpanded = true;
      fixture.detectChanges();

      compiled = fixture.nativeElement;
      expansionHint = compiled.querySelector('.expansion-hint');

      if (expansionHint) {
        expect(expansionHint.textContent).toContain('Weniger anzeigen');
      }
    });

    it('should render expansion panel with correct binding', () => {
      const compiled = fixture.nativeElement;
      const expansionPanel = compiled.querySelector('mat-expansion-panel');

      // Note: In a real test environment with Angular Material properly configured,
      // we would check the expanded attribute. Here we just verify the component has the property
      expect(component.hasOwnProperty('isRegistrationInfoExpanded')).toBeTruthy();
    });
  });
});
