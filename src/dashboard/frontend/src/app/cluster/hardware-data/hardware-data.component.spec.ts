import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HardwareDataComponent } from './hardware-data.component';

describe('HardwareDataComponent', () => {
  let component: HardwareDataComponent;
  let fixture: ComponentFixture<HardwareDataComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HardwareDataComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HardwareDataComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
