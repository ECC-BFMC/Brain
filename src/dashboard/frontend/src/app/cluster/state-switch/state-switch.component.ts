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
  private steerIncrement: number = 25;
  private maxSteer: number = 250;
  private minSteer: number = -250;

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

    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${this.speed}"}`);   
  }

  private decreaseSpeed(): void {
    this.speed -= this.speedIncrement;
    if (this.speed < this.minSpeed) {
      this.speed = this.minSpeed;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${this.speed}"}`);   
  }

  private steerLeft(): void {
    this.steer -= this.steerIncrement;
    if (this.steer < this.minSteer) {
      this.steer = this.minSteer;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${this.steer}"}`);   
  }

  private steerRight(): void {
    this.steer += this.steerIncrement;
    if (this.steer > this.maxSteer) {
      this.steer = this.maxSteer;
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${this.steer}"}`);   
  }

  private speedReset(): void { 
    this.speed = 0;
    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${this.speed}"}`);   
  }

  private steerReset(): void { 
    this.steer = 0;
    this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${this.steer}"}`);   
  }
}

