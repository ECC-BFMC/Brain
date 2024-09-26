import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SteeringComponent } from './steering.component';

describe('SteeringComponent', () => {
  let component: SteeringComponent;
  let fixture: ComponentFixture<SteeringComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SteeringComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(SteeringComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
