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

        it('should not add a reference when focus moves into the description field of a chip', () => {
            component.writeValue([{ reference_string: 'Bereits erfasste Quelle' }]);
            component.startDescriptionEdit(0);
            fixture.detectChanges();

            component.urlControl.setValue('Instagram-Reel von @gruene, Juli 2026');

            const descriptionField: HTMLElement = fixture.nativeElement
                .querySelector('.reference-description-input');
            expect(descriptionField).withContext('Beschreibungsfeld sichtbar').toBeTruthy();

            blurSourceInput(descriptionField);

            expect(component.selectedReferences.length).toBe(1);
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

        // Dritte Variante desselben stillen Verlusts: Beschreibung getippt,
        // Feld noch offen, gespeichert.
        it('should adopt an open chip description instead of dropping it on save', () => {
            const emitted: any[] = [];
            component.writeValue([{ reference_string: 'Instagram-Reel von @gruene, Juli 2026' }]);
            component.registerOnChange(value => emitted.push(value));

            component.startDescriptionEdit(0);
            component.descriptionControl.setValue('Aussage zur Waermeplanung');

            const adopted = component.flushPendingInput();

            expect(adopted).toBeTrue();
            expect(component.selectedReferences[0].description).toBe('Aussage zur Waermeplanung');
            expect(emitted[emitted.length - 1]).toEqual([
                {
                    reference_string: 'Instagram-Reel von @gruene, Juli 2026',
                    description: 'Aussage zur Waermeplanung'
                }
            ]);
        });
    });

    // Punkt 2/3: Die Beschreibung haengt am Chip, nicht am Eingabefeld.
    describe('Beschreibung am Chip', () => {
        it('should add a description to an existing chip after the fact', () => {
            const emitted: any[] = [];
            component.writeValue([{ reference_string: 'Broschuere der Ortsgruppe, Mai 2026' }]);
            component.registerOnChange(value => emitted.push(value));
            fixture.detectChanges();

            const toggle: HTMLButtonElement = fixture.nativeElement
                .querySelector('.reference-item .description-toggle');
            expect(toggle).withContext('Link am Chip vorhanden').toBeTruthy();
            expect(toggle.textContent).toContain('Beschreibung hinzufügen');

            toggle.click();
            fixture.detectChanges();

            expect(component.editingDescriptionIndex).toBe(0);
            const descriptionField: HTMLElement = fixture.nativeElement
                .querySelector('.reference-item .reference-description-input');
            expect(descriptionField).withContext('Feld am Chip sichtbar').toBeTruthy();

            component.descriptionControl.setValue('Seite 4, Absatz zum Radverkehr');
            const changed = component.commitDescriptionEdit();
            fixture.detectChanges();

            expect(changed).toBeTrue();
            expect(component.editingDescriptionIndex).toBeNull();
            expect(component.selectedReferences[0].description).toBe('Seite 4, Absatz zum Radverkehr');
            expect(emitted[emitted.length - 1]).toEqual([
                {
                    reference_string: 'Broschuere der Ortsgruppe, Mai 2026',
                    description: 'Seite 4, Absatz zum Radverkehr'
                }
            ]);
            // Die Beschreibung steht danach am Chip
            expect(fixture.nativeElement.querySelector('.reference-description').textContent)
                .toContain('Seite 4, Absatz zum Radverkehr');
        });

        it('should offer an existing description for editing', () => {
            component.writeValue([
                { reference_string: 'Broschuere der Ortsgruppe, Mai 2026', description: 'Alte Notiz' }
            ]);
            fixture.detectChanges();

            const toggle: HTMLButtonElement = fixture.nativeElement
                .querySelector('.reference-item .description-toggle');
            expect(toggle.textContent).toContain('Beschreibung bearbeiten');

            component.startDescriptionEdit(0);

            expect(component.descriptionControl.value).toBe('Alte Notiz');

            component.descriptionControl.setValue('Neue Notiz');
            component.commitDescriptionEdit();

            expect(component.selectedReferences[0].description).toBe('Neue Notiz');
        });

        it('should keep the description field usable when the maximum is reached', () => {
            component.maxReferences = 1;
            component.writeValue([{ reference_string: 'Einzige Quelle' }]);

            expect(component.urlControl.disabled).withContext('URL-Feld gesperrt').toBeTrue();
            expect(component.descriptionControl.disabled)
                .withContext('Beschreibung weiter bedienbar').toBeFalse();
        });
    });
});
