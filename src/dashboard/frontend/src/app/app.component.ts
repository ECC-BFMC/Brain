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

import { Component, HostListener, ViewChild } from '@angular/core';
import { ClusterComponent } from './cluster/cluster.component';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { WebSocketService } from './webSocket/web-socket.service';
import { TableComponent } from './table/table.component';
import { CommonModule } from '@angular/common'
import * as CryptoJS from 'crypto-js'; 

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [TableComponent, ClusterComponent, FormsModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {

  title: string = 'dashboard';
  correctPassword = 'U2FsdGVkX18Lrd7U4IqjmFUNVH7aGbw7SPsLXHb2qlU='; // Encrypted password (AES encrypted "")
  private secretKey = 'ThisIsTheKey'; // Secret key for decryption
  cursorRotationSliderValue: number = 0;
  carPositionSliderValue: number = 0;
  carLeftLaneOn: boolean = false;
  carRightLaneOn: boolean = false;
  clusterLightType: string = '';
  private intervalId: any;

  enteredPassword = ''; // User input password
  isAuthenticated = false; // Controls whether the content is displayed or not

  private sessionAccessSubscription: Subscription | undefined;

  @ViewChild(ClusterComponent) clusterComponent!: ClusterComponent;
  @ViewChild(TableComponent) tableComponent!: TableComponent;

  constructor( private webSocketService: WebSocketService ) { }

  ngOnInit() {
    //To enable all the NUCLEO futures uncomment this fc:
    //this.startNUCLEOFunctions()

    this.sessionAccessSubscription = this.webSocketService.receiveSessionAccess().subscribe(
      (message) => {
        if (message.data == true) { 
          this.isAuthenticated = true;
        }
      },
      (error) => {
        console.error('Error receiving session access:', error);
      }
    );
  }

  submit(): void {
    if (this.clusterComponent) {
      this.clusterComponent.setWarningLightType(this.clusterLightType); 
    }   
  }

  decryptPassword(encryptedPassword: string): string {
    const bytes = CryptoJS.AES.decrypt(encryptedPassword, this.secretKey);
    return bytes.toString(CryptoJS.enc.Utf8); // Return decrypted password
  }

  submitPassword() {
    const decryptedCorrectPassword = this.decryptPassword(this.correctPassword);

    if (this.enteredPassword === decryptedCorrectPassword) {
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

  logout() {
    this.isAuthenticated = false;
    this.webSocketService.sendMessageToFlask(`{"Name": "SessionEnd"}`);
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
  
  startNUCLEOFunctions()
  {
    this.sendMessage("{\"Name\": \"ToggleInstant\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleBatteryLvl\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleImuData\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleResourceMonitor\", \"Value\": 1}")
  }

  sendMessage(message: string) {
    this.webSocketService.sendMessageToFlask(message);
  }
}
