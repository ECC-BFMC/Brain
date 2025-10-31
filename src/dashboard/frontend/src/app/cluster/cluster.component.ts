// Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC orginazers
// All rights reserved.

// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:

//  1. Redistributions of source code must retain the above copyright notice, this
//    list of conditions and the following disclaimer.

//  2. Redistributions in binary form must reproduce the above copyright notice,
//     this list of conditions and the following disclaimer in the documentation
//     and/or other materials provided with the distribution.

// 3. Neither the name of the copyright holder nor the names of its
//    contributors may be used to endorse or promote products derived from
//     this software without specific prior written permission.

// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
import { CommonModule } from '@angular/common';
import { ClusterService } from './cluster.service';
import { provideProtractorTestingSupport } from '@angular/platform-browser';
@Component({
  selector: 'app-cluster',
  standalone: true,
  imports: [SpeedometerComponent, BatteryLevelComponent, MapComponent, 
            CarComponent, InstantConsumptionComponent, StateSwitchComponent,
            KlSwitchComponent, SteeringComponent, LiveCameraComponent,
            WarningLightComponent, HardwareDataComponent, RecordComponent,
            TimeSpeedSteerComponent, SideMarkerComponent, CommonModule],
  templateUrl: './cluster.component.html',
  styleUrl: './cluster.component.css'
})
export class ClusterComponent {
  @Input() cursorRotation: number = 0;
  @Input() carPosition: number = 0;
  @Input() carLeftLaneOn: boolean = false;
  @Input() carRightLaneOn: boolean = false;

  @ViewChild(WarningLightComponent) warningLightComponent!: WarningLightComponent;
  @ViewChild(StateSwitchComponent) stateSwitchComponent!: StateSwitchComponent;
  @ViewChild(KlSwitchComponent) klSwitchComponent!: KlSwitchComponent;

  warningLightType: string = '';
  public battery: number = 0;
  public speed: number = 0;
  private batterySubscription: Subscription | undefined;
  private speedSubscription: Subscription | undefined;
  private warningSubscription: Subscription | undefined;
  public warningSignal: Boolean = false;
  private klSubscription: Subscription | undefined;
  private currentSerialConnectionStateSubscription: Subscription | undefined;
  private serialConnectionStateSubscription: Subscription | undefined;
  constructor( private  webSocketService: WebSocketService, private clusterService: ClusterService) { }

  ngOnInit()
  {
    this.webSocketService.sendMessageToFlask(`{"Name": "GetCurrentSerialConnectionState"}`);

    this.batterySubscription = this.webSocketService.receiveBatteryLevel().subscribe(
      (message) => {
        this.battery = message.value;
      },
      (error) => {
        console.error('Error receiving battery:', error);
      }
    );

    this.speedSubscription = this.webSocketService.receiveCurrentSpeed().subscribe(
      (message) => {
        this.speed = Math.abs(parseInt(message.value)/10);
      },
      (error) => {
        console.error('Error receiving speed:', error);
      }
    );

    this.warningSubscription = this.webSocketService.receiveWarningSignal().subscribe(
      (message) => {
        this.warningSignal = true
      },
      (error) => {
        console.error('Error receiving warning signal:', error);
      }
    );

    this.serialConnectionStateSubscription = this.webSocketService.receiveSerialConnectionState().subscribe(
      (message) => {
        this.clusterService.updateSerialConnectionState(message.value);
      },
      (error) => {
        console.error('Error receiving serial connection state:', error);
      }
    );

    this.klSubscription = this.clusterService.kl$.subscribe(
      (klState) => {
        if (klState === '0') {
          this.battery = 0;
          this.speed = 0;
        }
      },
      (error) => {
        console.error('Error receiving KL state:', error);
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

    if (this.warningSubscription) {
      this.warningSubscription.unsubscribe();
    }

    if (this.klSubscription) {
      this.klSubscription.unsubscribe();
    }

    if (this.currentSerialConnectionStateSubscription) {
      this.currentSerialConnectionStateSubscription.unsubscribe();
    }

    if (this.serialConnectionStateSubscription) {
      this.serialConnectionStateSubscription.unsubscribe();
    }

    this.webSocketService.disconnectSocket();
    this.clusterService.updateKL('0');
  }
  
  setWarningLightType(type: string): void {
    this.warningLightType = type;
    
    if (this.warningLightComponent) {
      this.warningLightComponent.setWarningLightType(this.warningLightType);
    }
  }

  setState(index: number): void {
    if (this.stateSwitchComponent) {
      this.stateSwitchComponent.setState(index);
    }
  }

  setKL(index: number): void {
    if (this.klSwitchComponent) {
      this.klSwitchComponent.setState(index);
    }
  }
}