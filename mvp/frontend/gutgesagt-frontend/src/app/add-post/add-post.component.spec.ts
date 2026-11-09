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
import { OHNE_AUSSAGE } from '../beitragsformular/antwort-auf/antwort-auf.component';
import { erwarteCc0Hinweis } from '../shared/cc0-hinweis/cc0-hinweis.testing';
import { erwarteSprachhinweisZumBeitrag } from '../shared/components/sprachhinweis/sprachhinweis.testing';

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

  it('zeigt über dem Speichern-Knopf den CC0-Hinweis mit Links auf CC0 und die Nutzungsbedingungen (#415)', () => {
    erwarteCc0Hinweis(fixture.nativeElement);
  });

  it('gibt Titel und Text dem Sprachhinweis über dem CC0-Hinweis (#405)', () => {
    component.postForm.patchValue(WERTE);
    fixture.detectChanges();

    erwarteSprachhinweisZumBeitrag(fixture.debugElement, WERTE.title, WERTE.text);
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

  it('zeigt hinter dem ? die Schreibregeln, die das Speichern nicht sperren', () => {
    (fixture.nativeElement.querySelector('.erklaerung-umschalter') as HTMLButtonElement).click();
    component.postForm.patchValue(WERTE);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelectorAll('.schreibregeln li').length).toBe(6);
    expect((fixture.nativeElement.querySelector('.submit-btn') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('schickt nichts, solange ein Pflichtfeld fehlt', () => {
    const senden = spyOn(TestBed.inject(PostService), 'addPost');
    component.postForm.patchValue({ ...WERTE, url: '' });

    component.speichern();

    expect(senden).not.toHaveBeenCalled();
  });

  it('speichert ohne "Gepostet von" und schickt dann kein Konto (#618)', () => {
    const senden = spyOn(TestBed.inject(PostService), 'addPost').and.returnValue(of({ id: 'p-2' }));
    component.postForm.patchValue({ ...WERTE, author: '  ' });

    component.speichern();

    expect(senden).toHaveBeenCalledOnceWith({
      post: jasmine.objectContaining({ author: null }),
    });
  });

  it('zeigt bei "Gepostet von" keinen Hinweis, nur "(optional)" (#618)', () => {
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Gepostet von (optional)');
    expect(fixture.nativeElement.textContent).not.toContain('Nur bei Organisationen');
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

  describe('Antwort auf (optional, #619)', () => {
    it('zeigt den Antwort-auf-Block über dem Link', () => {
      const block = fixture.nativeElement.querySelector('form app-antwort-auf');
      const link = fixture.nativeElement.querySelector('#url');

      expect(block).not.toBeNull();
      expect(block.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('schickt eine gewählte Aussage per ID mit und meldet die verknüpfte', () => {
      const senden = spyOn(TestBed.inject(PostService), 'addPost').and.returnValue(
        of({ id: 'p-1', statement_id: 'a-1', statement_text: 'Solar lohnt sich nicht', verknuepft: true }),
      );
      let gemeldet: BeitragGespeichert | undefined;
      component.success.subscribe((ergebnis) => (gemeldet = ergebnis));
      component.postForm.patchValue(WERTE);
      component.aussageSetzen({ id: 'a-1', text: 'Solar lohnt sich nicht' });

      component.speichern();

      expect(senden.calls.mostRecent().args[0].statement_id).toBe('a-1');
      expect(senden.calls.mostRecent().args[0].statement_text).toBeUndefined();
      expect(gemeldet).toEqual({ id: 'p-1', aussage: { id: 'a-1', text: 'Solar lohnt sich nicht' }, verknuepft: true });
    });

    it('schickt eine neue Aussage per Text mit ihren Themen', () => {
      const senden = spyOn(TestBed.inject(PostService), 'addPost').and.returnValue(of({ id: 'p-1', verknuepft: true }));
      component.postForm.patchValue({ ...WERTE, themen: ['klima'] });
      component.aussageSetzen({ id: '', text: 'Solar lohnt sich nicht' });

      component.speichern();

      expect(senden.calls.mostRecent().args[0]).toEqual(
        jasmine.objectContaining({ statement_text: 'Solar lohnt sich nicht', themen: ['klima'] }),
      );
    });

    it('meldet nicht verknüpft, wenn das Backend die Aussage nicht anhängen konnte', () => {
      spyOn(TestBed.inject(PostService), 'addPost').and.returnValue(of({ id: 'p-1', verknuepft: false }));
      let gemeldet: BeitragGespeichert | undefined;
      component.success.subscribe((ergebnis) => (gemeldet = ergebnis));
      component.postForm.patchValue(WERTE);
      component.aussageSetzen({ id: 'a-weg', text: 'Gibt es nicht mehr' });

      component.speichern();

      expect(gemeldet?.verknuepft).toBeFalse();
      expect(gemeldet?.aussage.text).toBe('Gibt es nicht mehr');
    });

    it('sperrt Speichern bei einer Aussage unter 10 Zeichen, leer ist erlaubt', () => {
      const senden = spyOn(TestBed.inject(PostService), 'addPost').and.returnValue(of({ id: 'p-1' }));
      component.postForm.patchValue(WERTE);
      component.aussageSetzen({ id: '', text: 'zu kurz' });
      fixture.detectChanges();

      expect((fixture.nativeElement.querySelector('.submit-btn') as HTMLButtonElement).disabled).toBeTrue();
      component.speichern();
      expect(senden).not.toHaveBeenCalled();

      component.aussageSetzen(OHNE_AUSSAGE);
      component.speichern();
      expect(senden).toHaveBeenCalled();
      expect(senden.calls.mostRecent().args[0].statement_text).toBeUndefined();
    });
  });
});
