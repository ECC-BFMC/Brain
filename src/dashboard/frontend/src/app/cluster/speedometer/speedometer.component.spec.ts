import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SpeedometerComponent } from './speedometer.component';

describe('SpeedometerComponent', () => {
  let component: SpeedometerComponent;
  let fixture: ComponentFixture<SpeedometerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SpeedometerComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(SpeedometerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
