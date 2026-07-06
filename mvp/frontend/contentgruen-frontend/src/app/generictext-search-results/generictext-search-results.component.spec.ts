import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GenerictextSearchResultsComponent } from './generictext-search-results.component';

describe('GenerictextSearchResultsComponent', () => {
  let component: GenerictextSearchResultsComponent;
  let fixture: ComponentFixture<GenerictextSearchResultsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GenerictextSearchResultsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(GenerictextSearchResultsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
