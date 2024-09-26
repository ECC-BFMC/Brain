import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KlSwitchComponent } from './kl-switch.component';

describe('KlSwitchComponent', () => {
  let component: KlSwitchComponent;
  let fixture: ComponentFixture<KlSwitchComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KlSwitchComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(KlSwitchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
