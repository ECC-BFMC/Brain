import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MapSemaphoreComponent } from './map-semaphore.component';

describe('MapSemaphoreComponent', () => {
  let component: MapSemaphoreComponent;
  let fixture: ComponentFixture<MapSemaphoreComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MapSemaphoreComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MapSemaphoreComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
