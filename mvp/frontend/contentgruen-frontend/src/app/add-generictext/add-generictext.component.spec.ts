import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AddGenerictextComponent } from './add-generictext.component';
import { provideHttpClient } from '@angular/common/http';
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
        provideHttpClientTesting()
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
});
