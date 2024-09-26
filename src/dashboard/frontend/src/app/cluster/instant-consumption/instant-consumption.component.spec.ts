import { ComponentFixture, TestBed } from '@angular/core/testing';

import { InstantConsumptionComponent } from './instant-consumption.component';

describe('InstantConsumptionComponent', () => {
  let component: InstantConsumptionComponent;
  let fixture: ComponentFixture<InstantConsumptionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InstantConsumptionComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(InstantConsumptionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
