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

import { Component, HostListener } from '@angular/core';
import { WebSocketService } from '../../webSocket/web-socket.service';
import { NgFor } from '@angular/common';

@Component({
  selector: 'app-state-switch',
  standalone: true,
  imports: [NgFor],
  templateUrl: './state-switch.component.html',
  styleUrl: './state-switch.component.css'
})
export class StateSwitchComponent {
  public states: string[] = ['stop', 'manual', 'legacy', 'auto'];
  public currentStateIndex: number = 0;

  private isArrowUpHeld: boolean = false;
  private isArrowDownHeld: boolean = false;

  private speed: number = 0;
  private speedIncrement: number = 5;
  private maxSpeed: number = 50;
  private minSpeed: number = -50;

  private steer: number = 0;
  private steerIncrement: number = 2.5;
  private maxSteer: number = 25;
  private minSteer: number = -25;

  constructor(private  webSocketService: WebSocketService) { }

  @HostListener('window:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent): void {
    if (this.currentState == 'manual') {
      switch(event.key) {
        case 'w':
          if (!this.isArrowUpHeld) {
            this.isArrowUpHeld = true;
            this.increaseSpeed();
          }
          break;
        case 's':
          if (!this.isArrowDownHeld) {
            this.isArrowDownHeld = true;
            this.decreaseSpeed();
          }
          break;
        case 'a':
          this.steerLeft();
          break;
        case 'd':
          this.steerRight();
          break;
        default:
          break;
      }
    }
  }

  @HostListener('window:keyup', ['$event'])
  handleKeyUp(event: KeyboardEvent): void {
    if (this.currentState == 'manual') {
      switch(event.key) {
        case 'w':
          if (this.isArrowUpHeld) {
            this.isArrowUpHeld = false;
          }
          break;
        case 's':
          if (this.isArrowDownHeld) {
            this.isArrowDownHeld = false;
          }
          break;
        default:
          break;
      }
    }
  }

  setState(index: number) {
    if (this.currentState == 'manual' && this.currentState != this.states[index]) {
      this.speedReset();
      this.steerReset();
    }

    this.currentStateIndex = index;    
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

  private increaseSpeed(): void {
    this.speed += this.speedIncrement;
    if (this.speed > this.maxSpeed) {
      this.speed = this.maxSpeed;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${this.speed*10}"}`);   
  }

  private decreaseSpeed(): void {
    this.speed -= this.speedIncrement;
    if (this.speed < this.minSpeed) {
      this.speed = this.minSpeed;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${this.speed*10}"}`);   
  }

  private steerLeft(): void {
    this.steer -= this.steerIncrement;
    if (this.steer < this.minSteer) {
      this.steer = this.minSteer;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${this.steer*10}"}`);   
  }

  private steerRight(): void {
    this.steer += this.steerIncrement;
    if (this.steer > this.maxSteer) {
      this.steer = this.maxSteer;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${this.steer*10}"}`);   
  }

  private speedReset(): void { 
    this.speed = 0;
    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${this.speed*10}"}`);   
  }

  private steerReset(): void { 
    this.steer = 0;
    this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${this.steer*10}"}`);   
  }
}

