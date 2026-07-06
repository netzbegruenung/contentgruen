import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { ReferenceDuplicateDialog } from './reference-duplicate-dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('ReferenceDuplicateDialog', () => {
  let component: ReferenceDuplicateDialog;
  let fixture: ComponentFixture<ReferenceDuplicateDialog>;
  let mockDialogRef: jasmine.SpyObj<MatDialogRef<ReferenceDuplicateDialog>>;

  beforeEach(async () => {
    mockDialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [ReferenceDuplicateDialog, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {
          referenceString: 'test reference',
          existingDescription: 'existing desc',
          newDescription: 'new desc'
        }}
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ReferenceDuplicateDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
