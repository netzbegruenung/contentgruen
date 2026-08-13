import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';

import { ReferenceInputComponent } from './reference-input.component';
import { ReferenceService } from '../services/reference.service';

describe('ReferenceInputComponent', () => {
    let component: ReferenceInputComponent;
    let fixture: ComponentFixture<ReferenceInputComponent>;
    let referenceServiceStub: jasmine.SpyObj<ReferenceService>;

    beforeEach(async () => {
        referenceServiceStub = jasmine.createSpyObj<ReferenceService>('ReferenceService', [
            'addReference',
            'isValidUrl'
        ]);
        referenceServiceStub.addReference.and.returnValue(
            of({ id: 'server-id-1', was_new: true } as any)
        );
        referenceServiceStub.isValidUrl.and.returnValue(false);

        await TestBed.configureTestingModule({
            imports: [ReferenceInputComponent, BrowserAnimationsModule],
            providers: [
                provideHttpClient(),
                provideHttpClientTesting(),
                { provide: ReferenceService, useValue: referenceServiceStub }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ReferenceInputComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    function blurSourceInput(relatedTarget: HTMLElement | null): void {
        component.onInputBlur({ relatedTarget } as unknown as FocusEvent);
    }

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    // Punkt 2: Chip entsteht beim Verlassen des Feldes, ohne "+"-Klick.
    describe('Uebernahme beim Verlassen des Feldes', () => {
        it('should add a reference chip when the source input loses focus', () => {
            component.urlControl.setValue('Instagram-Reel von @gruene, Juli 2026');

            blurSourceInput(null);

            expect(component.selectedReferences.length).toBe(1);
            expect(component.selectedReferences[0].reference_string)
                .toBe('Instagram-Reel von @gruene, Juli 2026');
            // Danach steht ein leeres Feld fuer die naechste Quelle bereit
            expect(component.urlControl.value).toBe('');
        });

        it('should not add a reference when focus moves into the description field', () => {
            component.urlControl.setValue('Instagram-Reel von @gruene, Juli 2026');
            component.revealDescription();
            fixture.detectChanges();

            const descriptionField: HTMLElement = fixture.nativeElement
                .querySelector('.reference-description-input');
            expect(descriptionField).withContext('Beschreibungsfeld sichtbar').toBeTruthy();

            blurSourceInput(descriptionField);

            expect(component.selectedReferences.length).toBe(0);
            expect(component.urlControl.value).toBe('Instagram-Reel von @gruene, Juli 2026');
        });

        it('should not add a reference when focus moves to a remove button of an existing chip', () => {
            component.writeValue([{ reference_string: 'Bereits erfasste Quelle' }]);
            fixture.detectChanges();

            component.urlControl.setValue('Zweite Quelle, noch nicht bestaetigt');

            const removeButton: HTMLElement = fixture.nativeElement
                .querySelector('.reference-item button');
            expect(removeButton).withContext('Entfernen-Button vorhanden').toBeTruthy();

            blurSourceInput(removeButton);

            expect(component.selectedReferences.length).toBe(1);
            expect(component.urlControl.value).toBe('Zweite Quelle, noch nicht bestaetigt');
        });
    });

    // Punkt 4: Fallback gegen stillen Verlust beim Speichern.
    describe('flushPendingInput', () => {
        it('should adopt text left in the input field and publish it to the form value', () => {
            const emitted: any[] = [];
            component.registerOnChange(value => emitted.push(value));

            component.urlControl.setValue('Broschuere der Ortsgruppe, Mai 2026');

            const adopted = component.flushPendingInput();

            expect(adopted).toBeTrue();
            expect(component.selectedReferences.length).toBe(1);
            expect(emitted.length).toBeGreaterThan(0);
            expect(emitted[emitted.length - 1]).toEqual([
                { reference_string: 'Broschuere der Ortsgruppe, Mai 2026', description: undefined }
            ]);
        });

        it('should do nothing when the input field is empty', () => {
            const adopted = component.flushPendingInput();

            expect(adopted).toBeFalse();
            expect(component.selectedReferences.length).toBe(0);
            expect(referenceServiceStub.addReference).not.toHaveBeenCalled();
        });
    });
});
