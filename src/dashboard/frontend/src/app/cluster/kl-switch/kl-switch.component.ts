import { Component } from '@angular/core';
import { NgFor } from '@angular/common';
import { WebSocketService } from '../../webSocket/web-socket.service';

@Component({
  selector: 'app-kl-switch',
  standalone: true,
  imports: [NgFor],
  templateUrl: './kl-switch.component.html',
  styleUrl: './kl-switch.component.css'
})
export class KlSwitchComponent {
  public states = ['0', '15', '30'];
  public currentStateIndex = 0;

  constructor( private  webSocketService: WebSocketService) { }

  setState(index: number) {
    if (this.currentState == '30' && this.currentState != this.states[index]) {
      this.speedReset();
      this.steerReset();
    }

    this.currentStateIndex = index; 
    this.webSocketService.sendMessageToFlask(`{"Name": "Klem", "Value": "${this.states[this.currentStateIndex]}"}`);   
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
    if (this.currentState === '0') {
      return '#d9534f';
    }

    if (this.currentState === '15') {
      return '#f0ad4e';
    }

    if (this.currentState === '30') {
      return '#5cb85c';
    }

    return '#2b8fd1';
  }

  private speedReset(): void { 
    this.webSocketService.sendMessageToFlask(`{"Name": "SpeedMotor", "Value": "${0}"}`);   
  }

  private steerReset(): void { 
    this.webSocketService.sendMessageToFlask(`{"Name": "SteerMotor", "Value": "${0}"}`);   
  }
}

