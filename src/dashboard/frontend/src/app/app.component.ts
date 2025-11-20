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

import { Component, HostListener, ViewChild, OnDestroy } from '@angular/core';
import { ClusterComponent } from './cluster/cluster.component';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { WebSocketService } from './webSocket/web-socket.service';
import { TableComponent } from './table/table.component';
import { StateSwitchComponent } from './cluster/state-switch/state-switch.component';
import { SettingsComponent } from './settings/settings.component';
import { CommonModule } from '@angular/common'
import * as CryptoJS from 'crypto-js';
import { ClusterService } from './cluster/cluster.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [TableComponent, ClusterComponent, StateSwitchComponent, SettingsComponent, FormsModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnDestroy {

  // HERE PASTE YOUR PASSWORD (md5 hash) - use the following python code to generate your password:
  // >>> import hashlib
  // >>> input = "" # (desired password)
  // >>> md5_hash = hashlib.md5(input.encode()).hexdigest()
  // >>> print(md5_hash)
  // example for "123" -> 202cb962ac59075b964b07152d234b70
  correctPassword = ''; // md5 hash of the password

  enteredPassword = ''; // User input password
  isAuthenticated = false; // Controls whether the content is displayed or not
  showAlert: boolean = false;
  title: string = 'dashboard';
  backendConnected: boolean = true;
  showSettingsModal: boolean = false;

  // Cluster component variables
  cursorRotationSliderValue: number = 0;
  carPositionSliderValue: number = 0;
  carLeftLaneOn: boolean = false;
  carRightLaneOn: boolean = false;

  // Interval variables
  private intervalId: any;
  private alertInterval: any;

  // WebSocket subscriptions
  private sessionAccessSubscription: Subscription | undefined;
  private heartbeatSubscription: Subscription | undefined;
  private heartbeatDisconnectSubscription: Subscription | undefined;
  private connectionStatusSubscription: Subscription | undefined;
  private connectionCheckInterval: any;
  private autoReconnectInterval: any;
  private currentSerialConnectionStateSubscription: Subscription | undefined;
  @ViewChild(ClusterComponent) clusterComponent!: ClusterComponent;
  @ViewChild(TableComponent) tableComponent!: TableComponent;
  @ViewChild('stateSwitch') stateSwitchComponent!: StateSwitchComponent;

  constructor(private webSocketService: WebSocketService, private clusterService: ClusterService) { }

  ngOnInit() {
    //To enable all the NUCLEO futures uncomment this fc:
    //this.startNUCLEOFunctions()

    this.sessionAccessSubscription = this.webSocketService.receiveSessionAccess().subscribe(
      (message) => {
        if (message.data == true) {
          this.isAuthenticated = true;

          // Request current states from backend upon successful login
          this.webSocketService.sendMessageToFlask(`{"Name": "GetCurrentSerialConnectionState"}`);
        }
      },
      (error) => {
        console.error('Error receiving session access:', error);
      }
    );

    this.currentSerialConnectionStateSubscription = this.webSocketService.receiveCurrentSerialConnectionState().subscribe(
      (message) => {
        this.clusterService.updateSerialConnectionState(message.data);
      },
      (error) => {
        console.error('Error receiving current serial connection state:', error);
      }
    );

    this.heartbeatSubscription = this.webSocketService.receiveHeartbeat().subscribe(
      (message) => {
        if (this.isAuthenticated) {
          this.webSocketService.sendMessageToFlask(`{"Name": "Heartbeat"}`);
        }
      }
    );

    this.heartbeatDisconnectSubscription = this.webSocketService.receiveHeartbeatDisconnect().subscribe(
      (message) => {
        this.logout();
      }
    );

    // Check connection status on initialization
    this.backendConnected = this.webSocketService.isConnected();

    this.connectionStatusSubscription = this.webSocketService.connectionStatus$.subscribe(status => {
      if (status === 'disconnected' || status === 'error') {
        this.backendConnected = false;
        this.isAuthenticated = false;
        this.startAutoReconnect();

      } else if (status === 'connected') {
        this.backendConnected = true;
        this.stopAutoReconnect();

        // if (!this.webSocketService.isConnected()) {
        //   this.webSocketService.reconnect();
        // }
      }
    });
  }

  submitPassword() {
    if (this.correctPassword === '' && this.enteredPassword === this.correctPassword) {
      this.showAlert = true;
      this.webSocketService.sendMessageToFlask(`{"Name": "SessionAccess"}`);
      return;
    }

    const enteredPasswordHash = CryptoJS.MD5(this.enteredPassword).toString();
    if (enteredPasswordHash === this.correctPassword) {
      this.showAlert = false;
      this.webSocketService.sendMessageToFlask(`{"Name": "SessionAccess"}`);
    }
  }

  @HostListener('window:beforeunload', ['$event'])
  handleUnload(event: Event) {
    if (this.isAuthenticated) {
      this.logout();
    }

    event.preventDefault();
  }

  @HostListener('window:keydown', ['$event'])
  handleGlobalKeyDown(event: KeyboardEvent) {
    if (event.key === ' ') {
      event.preventDefault(); // Prevent scroll down on spacebar globally
    }
  }

  logout() {
    this.isAuthenticated = false;
    this.webSocketService.sendMessageToFlask(`{"Name": "SessionEnd"}`);
  }

  dismissAlert() {
    this.showAlert = false;

    if (this.alertInterval) {
      clearInterval(this.alertInterval);
    }

    this.alertInterval = setInterval(() => {
      this.showAlert = true;
    }, 900000);
  }

  openSettings() {
    this.showSettingsModal = true;
  }

  closeSettings() {
    this.showSettingsModal = false;
  }

  sendMessage(message: string) {
    this.webSocketService.sendMessageToFlask(message);
  }

  startAutoReconnect() {
    if (!this.autoReconnectInterval) {
      this.autoReconnectInterval = setInterval(() => {
        if (!this.webSocketService.isConnected()) {
          this.webSocketService.reconnect();
        }
      }, 2000); // Every 2 seconds
    }
  }

  stopAutoReconnect() {
    if (this.autoReconnectInterval) {
      clearInterval(this.autoReconnectInterval);
      this.autoReconnectInterval = null;
    }
  }

  manualReconnect() {
    this.webSocketService.reconnect();
  }

  ngOnDestroy() {
    if (this.alertInterval) {
      clearInterval(this.alertInterval);
    }

    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    if (this.connectionCheckInterval) {
      clearInterval(this.connectionCheckInterval);
    }

    if (this.autoReconnectInterval) {
      clearInterval(this.autoReconnectInterval);
    }

    if (this.connectionStatusSubscription) {
      this.connectionStatusSubscription.unsubscribe();
    }

    if (this.heartbeatSubscription) {
      this.heartbeatSubscription.unsubscribe();
    }

    if (this.heartbeatDisconnectSubscription) {
      this.heartbeatDisconnectSubscription.unsubscribe();
    }
  }

  startInfiniteLoop(): void {
    let speed = 0;
    let steer = 0;
    let speedDirection = 1;  // 1 means increasing, -1 means decreasing
    let steerDirection = 1;

    this.intervalId = setInterval(() => {
      // Update speed value
      speed += speedDirection * 10; // Change speed in steps of 10
      if (speed >= 50 || speed <= -50) {
        speedDirection *= -1; // Reverse the direction of change
      }

      // Update steer value
      steer += steerDirection * 5; // Change steer in steps of 5
      if (steer >= 20 || steer <= -20) {
        steerDirection *= -1; // Reverse the direction of change
      }

      // Send the updated messages
      this.sendMessage(`{"Name": "SpeedMotor", "Value": "${speed.toFixed(1)}"}`);
      this.sendMessage(`{"Name": "SteerMotor", "Value": "${steer.toFixed(1)}"}`);
    }, 1000); // 1000ms = 1 second
  }

  startNUCLEOFunctions() {
    this.sendMessage("{\"Name\": \"ToggleInstant\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleBatteryLvl\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleImuData\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleResourceMonitor\", \"Value\": 1}")
  }
}
