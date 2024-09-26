import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LiveCameraComponent } from './live-camera.component';

describe('LiveCameraComponent', () => {
  let component: LiveCameraComponent;
  let fixture: ComponentFixture<LiveCameraComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LiveCameraComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(LiveCameraComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
