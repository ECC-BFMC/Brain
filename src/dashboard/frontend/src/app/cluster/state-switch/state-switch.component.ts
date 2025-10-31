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

import { Component, HostListener, OnInit } from '@angular/core';
import { WebSocketService } from '../../webSocket/web-socket.service';
import { NgFor, NgIf } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { ClusterService } from '../cluster.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-state-switch',
  standalone: true,
  imports: [NgFor, NgIf, MatIconModule],
  templateUrl: './state-switch.component.html',
  styleUrl: './state-switch.component.css'
})
export class StateSwitchComponent implements OnInit {
  public states: string[] = ['stop', 'manual', 'legacy', 'auto'];
  public currentStateIndex: number = 0;

  public isMobile: boolean = false;

  private activeKeys: Set<string> = new Set();

  private speed: number = 0;
  private speedIncrement: number = 5;
  private maxSpeed: number = 50;
  private minSpeed: number = -50;

  private maxSteer: number = 25;
  private minSteer: number = -25;
  private steer: number = 0;
  private lastSteer: number = 0;
  private steerNumOfSteps: number = 10;
  private steerIncrement: number = (Math.abs(this.maxSteer) / this.steerNumOfSteps);
  private steerDecrement: number = (Math.abs(this.maxSteer) / this.steerNumOfSteps);
  private steerInterval: any;
  private steerDecreaseInterval: any;
  private isSteering: boolean = false;


  private steerLimitsSubscription: Subscription | undefined;

  klState: string = '';

  constructor(
    private webSocketService: WebSocketService,
    private clusterService: ClusterService
  ) {}

  ngOnInit() {
    // Notify backend of the actual initial driving mode
    this.webSocketService.sendMessageToFlask(`{"Name": "DrivingMode", "Value": "${this.currentState}"}`);   

    this.clusterService.isMobileDriving$.subscribe(isMobileDriving => {
      this.isMobile = isMobileDriving;
    });

    this.clusterService.kl$.subscribe(state => {
      this.klState = state;
      
      if (this.klState === '15' || this.klState === '0') {
        this.speed = 0;
        this.steer = 0; 
      }
    });

    this.steerLimitsSubscription = this.webSocketService.receiveSteerLimits().subscribe(
      (message) => {
        this.maxSteer = Number((message.value["upperLimit"] / 10).toFixed(1));
        this.minSteer = Number((message.value["lowerLimit"] / 10).toFixed(1));
        this.steerIncrement = (Math.abs(this.maxSteer) / this.steerNumOfSteps);
        this.steerDecrement = (Math.abs(this.maxSteer) / this.steerNumOfSteps);
      }
    );
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent) {

    if (this.currentState == 'manual' && this.klState === '30') {

      if (this.activeKeys.has(event.key))
        return;
    
      this.activeKeys.add(event.key);

      switch(event.key) {
        case 'w':
          this.increaseSpeed();
          break;
        case 's':
          this.decreaseSpeed();
          break;
        case 'a':
          if (!this.isSteering) { 
            this.isSteering = true
            this.stopDecreasingSteering();
            this.startSteeringLeft();
          }
          break;
        case 'd':
          if (!this.isSteering) { 
            this.isSteering = true
            this.stopDecreasingSteering();
            this.startSteeringRight();  
          }
          break;
        case ' ':
          this.brakeReset();
          break;
        default:
          break;
      }
    }
  }

  @HostListener('window:keyup', ['$event'])
  handleKeyUp(event: KeyboardEvent) {
    if (this.currentState === 'manual' && this.activeKeys.has(event.key)) {
      this.activeKeys.delete(event.key);
      
      // Only stop steering when 'a' or 'd' is released
      if (event.key === 'a' || event.key === 'd') {
        this.stopSteering();
        this.startDecreasingSteer();
      }
    }
  }

  setState(index: number) {
    if (this.currentState == 'manual' && this.currentState != this.states[index]) {
      this.brakeReset();
      this.stopSteering();
    }

    this.currentStateIndex = index;    
    this.clusterService.updateDrivingMode(this.states[index]);
    this.webSocketService.sendMessageToFlask(`{"Name": "DrivingMode", "Value": "${this.states[index]}"}`);   
  }

  get currentState() {
    return this.states[this.currentStateIndex];
  }

  getSliderPosition(index: number): string {
    const totalStates = this.states.length;
    const percentage = (index / totalStates) * 100;
    return `calc(${percentage}%)`;
  }

  public onButtonPress(direction: string): void { 
    if (direction == "left") {
      this.stopDecreasingSteering();
      this.startSteeringLeft();
    }
    else if (direction == "right") {
      this.stopDecreasingSteering();
      this.startSteeringRight();
    }
  }

  public onButtonRelease(): void { 
    this.stopSteering();
    this.startDecreasingSteer();
  }

  public increaseSpeed(): void {
    this.speed += this.speedIncrement;

    if (this.speed > this.maxSpeed) {
      this.speed = this.maxSpeed;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${Math.round(this.speed*10)}"}`);   
  }

  public decreaseSpeed(): void {
    this.speed -= this.speedIncrement;

    if (this.speed < this.minSpeed) {
      this.speed = this.minSpeed;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${Math.round(this.speed*10)}"}`);   
  }

  private startSteeringRight() {
    this.steerInterval = setInterval(() => {

      this.steer += this.steerIncrement;

      if (this.steer > this.maxSteer) {
        this.steer = this.maxSteer;
      }
      
      if (this.lastSteer != this.maxSteer) { 
        this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${Math.round(this.steer*10)}"}`);  
      }
 
      this.lastSteer = this.steer;
    }, 50);
  }
   
  private startSteeringLeft() {
    this.steerInterval = setInterval(() => {

      this.steer -= this.steerIncrement;

      if (this.steer < this.minSteer) {
        this.steer = this.minSteer;
      }

      if (this.lastSteer != this.minSteer) { 
        this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${Math.round(this.steer*10)}"}`);
      }
        
      this.lastSteer = this.steer;
    }, 50);
  }

  private startDecreasingSteer() { 
    this.steerDecreaseInterval = setInterval(() => {
      if (this.steer == 0 || this.isSteering)
        return;
    
      if (this.steer < 0) {
        this.steer += this.steerDecrement;
    
        if (this.steer > 0) { 
          this.steer = 0;
        }
      }
    
      if (this.steer > 0) {
        this.steer -= this.steerDecrement;
    
        if (this.steer < 0) { 
          this.steer = 0;
        }
      }
    
      this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${Math.round(this.steer*10)}"}`); 
    }, 50)
  }

  private speedReset(): void { 
    this.speed = 0;
    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${Math.round(this.speed*10)}"}`);   
  }

  private steerReset(): void { 
    this.steer = 0;
    this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${Math.round(this.steer*10)}"}`);   
  }

  private brakeReset(): void { 
    this.steer = 0;
    this.speed = 0;
    this.webSocketService.sendMessageToFlask(`{"Name": "Brake", "Value": "0"}`);   
  }

  private stopSteering() {
    if (this.steerInterval) {
      clearInterval(this.steerInterval); 
      this.steerInterval = null; 
    }
    this.isSteering = false; 
  }

  private stopDecreasingSteering() {
    if (this.steerDecreaseInterval) { 
      clearInterval(this.steerDecreaseInterval);
      this.steerDecreaseInterval = null;
    }
  }

  getSliderWidth(): string {
    return `calc(100% / ${this.states.length})`;
  }

  getSliderColor() {
    if (this.currentState === 'legacy') {
      return '#2b8fd1';
    }

    if (this.currentState === 'manual') {
      return '#f0ad4e';
    }

    if (this.currentState === 'stop') {
      return '#d9534f';
    }

    if (this.currentState === 'auto') {
      return '#5cb85c';
    }

    return '#2b8fd1';
  }

  ngOnDestroy() {
    if (this.steerLimitsSubscription) {
      this.steerLimitsSubscription.unsubscribe();
    }
  }
}
