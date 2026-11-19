import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { AddImageWorkflowComponent } from './add-image-workflow.component';

describe('AddImageWorkflowComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddImageWorkflowComponent, NoopAnimationsModule],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  it('fuehrt nach dem Speichern auf die Ergebnisseite des Bildes, mit der Aussage (#619)', () => {
    const fixture = TestBed.createComponent(AddImageWorkflowComponent);
    fixture.detectChanges();
    const navigieren = spyOn(TestBed.inject(Router), 'navigate');

    fixture.componentInstance.onSuccess({ id: 'b-1', aussage: { id: 'a-1', text: 'Solar lohnt sich nicht' }, verknuepft: true });

    expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-image', 'gespeichert', 'b-1'], {
      state: { aussage: { id: 'a-1', text: 'Solar lohnt sich nicht' }, verknuepft: true },
      replaceUrl: true,
    });
  });

  it('gibt ohne Aussage keine mit', () => {
    const fixture = TestBed.createComponent(AddImageWorkflowComponent);
    const navigieren = spyOn(TestBed.inject(Router), 'navigate');

    fixture.componentInstance.onSuccess({ id: 'b-1', aussage: { id: '', text: '' }, verknuepft: true });

    expect(navigieren.calls.mostRecent().args[1]?.state).toEqual({ verknuepft: true });
  });
});
