import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';

import { AddImageComponent } from './add-image.component';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';

describe('AddImageComponent', () => {
  let fixture: ComponentFixture<AddImageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddImageComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([])
      ]
    })
      .overrideComponent(AddImageComponent, {
        remove: { imports: [BeitragskarteComponent] },
        add: { imports: [BeitragskarteStubComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AddImageComponent);
    fixture.detectChanges();
  });

  it('verlinkt die Nutzungsbedingungen ueber dem Absenden-Knopf', () => {
    const link: HTMLAnchorElement | null = fixture.nativeElement.querySelector(
      'a[href="/nutzungsbedingungen"]'
    );

    expect(link).toBeTruthy();
    expect(link!.target).toBe('_blank');
  });
});
