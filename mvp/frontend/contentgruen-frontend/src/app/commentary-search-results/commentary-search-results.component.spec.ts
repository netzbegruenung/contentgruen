import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CommentarySearchResultsComponent } from './commentary-search-results.component';

describe('CommentarySearchResultsComponent', () => {
  let component: CommentarySearchResultsComponent;
  let fixture: ComponentFixture<CommentarySearchResultsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CommentarySearchResultsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CommentarySearchResultsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
