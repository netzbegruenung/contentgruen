import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';

import { AddPostComponent, SPEICHERN_FEHLGESCHLAGEN } from './add-post.component';
import { PostService } from '../services/post.service';
import { BeitragskarteComponent } from '../beitragskarte/beitragskarte.component';
import { BeitragskarteStubComponent } from '../beitragskarte/beitragskarte.stub';
import type { BeitragGespeichert } from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';

describe('AddPostComponent', () => {
  let fixture: ComponentFixture<AddPostComponent>;
  let component: AddPostComponent;

  const WERTE = {
    url: 'https://www.instagram.com/p/abc123/',
    author: '@klimaverein',
    title: 'Ein Reel, das Wärmepumpen ohne Fachjargon erklärt',
    text: 'Zeigt in 30 Sekunden, wie eine Wärmepumpe aus kalter Luft Wärme holt.',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddPostComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    })
      .overrideComponent(AddPostComponent, {
        remove: { imports: [BeitragskarteComponent] },
        add: { imports: [BeitragskarteStubComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AddPostComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('verlinkt die Nutzungsbedingungen ueber dem Speichern-Knopf', () => {
    const link: HTMLAnchorElement | null = fixture.nativeElement.querySelector('a[href="/nutzungsbedingungen"]');

    expect(link).toBeTruthy();
    expect(link!.target).toBe('_blank');
    expect(fixture.nativeElement.textContent).toContain('CC0');
  });

  it('leitet die Plattform aus dem Link ab, solange niemand sie selbst gewaehlt hat', () => {
    component.postForm.patchValue({ url: 'https://www.tiktok.com/@x/video/1' });
    expect(component.postForm.value.platform).toBe('tiktok');

    component.postForm.get('platform')!.setValue('youtube');
    component.postForm.get('platform')!.markAsDirty();
    component.postForm.patchValue({ url: 'https://bsky.app/profile/x/post/1' });

    expect(component.postForm.value.platform).toBe('youtube');
  });

  it('uebernimmt aus dem Fangkorb Satz als Titel, Link und Plattform', () => {
    component.vorbefuellung = { einwurfId: 'e-1', titel: 'Der Satz zum Einwurf', url: WERTE.url };
    component.ngOnChanges({ vorbefuellung: {} as any });

    expect(component.postForm.value.title).toBe('Der Satz zum Einwurf');
    expect(component.postForm.value.url).toBe(WERTE.url);
    expect(component.postForm.value.platform).toBe('instagram');
  });

  it('speichert Titel einzeilig, den Namen der Plattform und meldet die ID', () => {
    const senden = spyOn(TestBed.inject(PostService), 'addPost').and.returnValue(of({ id: 'p-1' }));
    let gemeldet: BeitragGespeichert | undefined;
    component.success.subscribe((ergebnis) => (gemeldet = ergebnis));
    component.postForm.patchValue({ ...WERTE, title: 'Ein Reel,\ndas erklärt' });

    component.speichern();

    expect(senden).toHaveBeenCalledOnceWith({
      post: {
        title: 'Ein Reel, das erklärt',
        text: WERTE.text,
        platform: 'Instagram',
        author: WERTE.author,
        url: WERTE.url,
      },
    });
    expect(gemeldet?.id).toBe('p-1');
    expect(gemeldet?.verknuepft).toBeTrue();
  });

  it('schickt nichts, solange ein Pflichtfeld fehlt', () => {
    const senden = spyOn(TestBed.inject(PostService), 'addPost');
    component.postForm.patchValue({ ...WERTE, author: '' });

    component.speichern();

    expect(senden).not.toHaveBeenCalled();
  });

  it('nimmt nur Links mit http oder https', () => {
    component.postForm.patchValue({ ...WERTE, url: 'instagram.com/p/abc' });

    expect(component.postForm.get('url')!.hasError('pattern')).toBeTrue();
  });

  it('behaelt nach gescheitertem Speichern die Eingaben und meldet den Fehler', () => {
    spyOn(TestBed.inject(PostService), 'addPost').and.returnValue(throwError(() => ({ status: 500 })));
    component.postForm.patchValue(WERTE);

    component.speichern();
    fixture.detectChanges();

    expect(component.fehler).toBe(SPEICHERN_FEHLGESCHLAGEN);
    expect(component.postForm.value.title).toBe(WERTE.title);
    expect(component.speichert).toBeFalse();
  });
});
