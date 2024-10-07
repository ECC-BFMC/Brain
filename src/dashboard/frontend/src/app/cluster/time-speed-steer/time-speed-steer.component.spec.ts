import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TimeSpeedSteerComponent } from './time-speed-steer.component';

describe('TimeSpeedSteerComponent', () => {
  let component: TimeSpeedSteerComponent;
  let fixture: ComponentFixture<TimeSpeedSteerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TimeSpeedSteerComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TimeSpeedSteerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
