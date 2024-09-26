import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ClusterComponent } from './cluster.component';

describe('ClusterComponent', () => {
  let component: ClusterComponent;
  let fixture: ComponentFixture<ClusterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ClusterComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ClusterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
