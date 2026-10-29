import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { AdminLayoutComponent } from './admin-layout.component';

describe('AdminLayoutComponent', () => {
  let fixture: ComponentFixture<AdminLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminLayoutComponent],
      providers: [provideRouter([]), provideNoopAnimations()],
    }).compileComponents();
    fixture = TestBed.createComponent(AdminLayoutComponent);
    fixture.detectChanges();
  });

  it('zeigt im Kopf das Logo statt des Sämlings (#416)', () => {
    const kopf: HTMLElement = fixture.nativeElement.querySelector('.admin-toolbar');

    const logo = kopf.querySelector<HTMLImageElement>('img.admin-logo');
    expect(logo).not.toBeNull();
    expect(logo!.getAttribute('src')).toBe('marke/logo.svg');
    expect(logo!.getAttribute('alt')).toBe('');
    expect(kopf.textContent).not.toContain('🌱');
    expect(kopf.textContent!.trim()).toBe('Gut gesagt – Admin');
  });
});
