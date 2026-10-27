import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject, of } from 'rxjs';
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { AddPostWorkflowComponent } from './add-post-workflow.component';
import { DestillierUebergabeService } from '../destillieren/destillier-uebergabe.service';

describe('AddPostWorkflowComponent', () => {
  let fixture: ComponentFixture<AddPostWorkflowComponent>;
  let component: AddPostWorkflowComponent;
  let params: BehaviorSubject<ParamMap>;
  let uebergabe: jasmine.SpyObj<DestillierUebergabeService>;

  const GESPEICHERT = { id: 'p-1', aussage: { id: '', text: '' }, verknuepft: true };

  beforeEach(async () => {
    params = new BehaviorSubject(convertToParamMap({}));
    uebergabe = jasmine.createSpyObj<DestillierUebergabeService>('DestillierUebergabeService', [
      'vorbefuellungLaden',
      'mitBeitragVerknuepfen',
    ]);
    uebergabe.vorbefuellungLaden.and.returnValue(
      of({ einwurfId: 'e-1', titel: 'Der Satz', url: 'https://www.instagram.com/p/abc/' }),
    );
    uebergabe.mitBeitragVerknuepfen.and.returnValue(of(true));

    await TestBed.configureTestingModule({
      imports: [AddPostWorkflowComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: DestillierUebergabeService, useValue: uebergabe },
      ],
    })
      .overrideProvider(ActivatedRoute, { useValue: { queryParamMap: params } })
      .compileComponents();

    fixture = TestBed.createComponent(AddPostWorkflowComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fuehrt nach dem Verfassen auf die Ergebnisseite des Posts', () => {
    const navigieren = spyOn(TestBed.inject(Router), 'navigate');

    component.onSuccess(GESPEICHERT);

    expect(uebergabe.mitBeitragVerknuepfen).not.toHaveBeenCalled();
    expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-post', 'gespeichert', 'p-1'], {
      queryParams: {},
      state: {},
      replaceUrl: true,
    });
  });

  it('befuellt aus dem Einwurf vor und verknuepft ihn nach dem Speichern mit dem Post', () => {
    params.next(convertToParamMap({ einwurf: 'e-1' }));
    const navigieren = spyOn(TestBed.inject(Router), 'navigate');

    expect(component.vorbefuellung?.titel).toBe('Der Satz');

    component.onSuccess(GESPEICHERT);

    expect(uebergabe.mitBeitragVerknuepfen).toHaveBeenCalledOnceWith('e-1', 'p-1', 'post');
    expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-post', 'gespeichert', 'p-1'], {
      queryParams: { einwurf: 'e-1' },
      state: { einwurfVerknuepft: true },
      replaceUrl: true,
    });
  });
});
