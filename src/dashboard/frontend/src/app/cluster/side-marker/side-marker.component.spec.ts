import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SideMarkerComponent } from './side-marker.component';

describe('SideMarkerComponent', () => {
  let component: SideMarkerComponent;
  let fixture: ComponentFixture<SideMarkerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SideMarkerComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SideMarkerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
