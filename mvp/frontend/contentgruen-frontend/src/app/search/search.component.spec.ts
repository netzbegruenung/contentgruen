import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { NavigationService } from '../services/navigation.service';

import { SearchComponent } from './search.component';

describe('SearchComponent', () => {
  let component: SearchComponent;
  let fixture: ComponentFixture<SearchComponent>;
  let navigationServiceMock: any;

  beforeEach(async () => {
    navigationServiceMock = jasmine.createSpyObj('NavigationService', ['navigateToResult']);

    await TestBed.configureTestingModule({
      imports: [
        SearchComponent,
        MatFormFieldModule,
        MatInputModule,
      ],
      providers: [
        { provide: NavigationService, useValue: navigationServiceMock },
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations()
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SearchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('onSearch', () => {
    it('should call navigationService.navigateToResult with the search query after debounce', fakeAsync(() => {
      const testQuery = 'test';
      component.searchQuery = testQuery;

      component.onSearch();
      tick(300); // Wait for debounce

      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(testQuery);
    }));

    it('should navigate to result-view when search query is provided', fakeAsync(() => {
      const testQuery = 'test query';
      component.searchQuery = testQuery;

      component.onSearch();
      tick(300); // Wait for debounce

      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(testQuery);
    }));

    it('should not navigate when search query is empty', fakeAsync(() => {
      component.searchQuery = '';

      component.onSearch();
      tick(300); // Wait for debounce

      expect(navigationServiceMock.navigateToResult).not.toHaveBeenCalled();
    }));

    it('should handle search navigation correctly', fakeAsync(() => {
      const testQuery = 'environment policy';
      component.searchQuery = testQuery;

      component.onSearch();
      tick(300); // Wait for debounce

      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(testQuery);
    }));
  });
});
