import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MapCursorComponent } from './map-cursor.component';

describe('MapCursorComponent', () => {
  let component: MapCursorComponent;
  let fixture: ComponentFixture<MapCursorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MapCursorComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(MapCursorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
