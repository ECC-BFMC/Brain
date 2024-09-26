import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WarningLightComponent } from './warning-light.component';

describe('WarningLightComponent', () => {
  let component: WarningLightComponent;
  let fixture: ComponentFixture<WarningLightComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WarningLightComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(WarningLightComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
