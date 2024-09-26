import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StateSwitchComponent } from './state-switch.component';

describe('StateSwitchComponent', () => {
  let component: StateSwitchComponent;
  let fixture: ComponentFixture<StateSwitchComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StateSwitchComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StateSwitchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
