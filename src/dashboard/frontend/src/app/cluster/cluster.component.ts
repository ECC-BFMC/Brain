import { Component, Input, ViewChild } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../webSocket/web-socket.service'

import { SpeedometerComponent } from './speedometer/speedometer.component';
import { BatteryLevelComponent } from './battery-level/battery-level.component';
import { MapComponent } from './map/map.component';
import { CarComponent } from './car/car.component';
import { InstantConsumptionComponent } from './instant-consumption/instant-consumption.component';
import { StateSwitchComponent } from './state-switch/state-switch.component';
import { KlSwitchComponent } from './kl-switch/kl-switch.component';
import { SteeringComponent } from './steering/steering.component';
import { LiveCameraComponent } from './live-camera/live-camera.component';
import { WarningLightComponent } from './warning-light/warning-light.component';
import { HardwareDataComponent} from './hardware-data/hardware-data.component';
import { RecordComponent} from './record/record.component';
import { TimeSpeedSteerComponent} from './time-speed-steer/time-speed-steer.component'
import { SideMarkerComponent } from './side-marker/side-marker.component'

@Component({
  selector: 'app-cluster',
  standalone: true,
  imports: [SpeedometerComponent, BatteryLevelComponent, MapComponent, 
            CarComponent, InstantConsumptionComponent, StateSwitchComponent,
            KlSwitchComponent, SteeringComponent, LiveCameraComponent,
            WarningLightComponent, HardwareDataComponent, RecordComponent,
            TimeSpeedSteerComponent, SideMarkerComponent],
  templateUrl: './cluster.component.html',
  styleUrl: './cluster.component.css'
})
export class ClusterComponent {
  @Input() cursorRotation: number = 0;
  @Input() carPosition: number = 0;
  @Input() carLeftLaneOn: boolean = false;
  @Input() carRightLaneOn: boolean = false;

  @ViewChild(WarningLightComponent) warningLightComponent!: WarningLightComponent;

  warningLightType: string = '';
  public battery: number = 0;
  public speed: number = 0;
  private batterySubscription: Subscription | undefined;
  private speedSubscription: Subscription | undefined;

  constructor( private  webSocketService: WebSocketService) { }

  ngOnInit()
  {
    this.batterySubscription = this.webSocketService.receiveBatteryLevel().subscribe(
      (message) => {
        this.battery = message.value;
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );

    this.speedSubscription = this.webSocketService.receiveCurrentSpeed().subscribe(
      (message) => {
        this.speed = Math.abs(parseInt(message.value));
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );
  }

  ngOnDestroy() {
    if (this.batterySubscription) {
      this.batterySubscription.unsubscribe();
    }

    if (this.speedSubscription) {
      this.speedSubscription.unsubscribe();
    }

    this.webSocketService.disconnectSocket();
  }
  
  setWarningLightType(type: string): void {
    this.warningLightType = type;
    
    if (this.warningLightComponent) {
      this.warningLightComponent.setWarningLightType(this.warningLightType);
    }
  }
}