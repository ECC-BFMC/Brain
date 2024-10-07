import { Component } from '@angular/core';
import { WebSocketService } from './../../webSocket/web-socket.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-time-speed-steer',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './time-speed-steer.component.html',
  styleUrl: './time-speed-steer.component.css'
})
export class TimeSpeedSteerComponent {
  time: number = 0;
  speed: number = 0;
  steer: number = 0;

  constructor( private webSocketService: WebSocketService) { }

  activateFunction() {
    this.webSocketService.sendMessageToFlask(`{"Name": "Control", "Value": {"Time":"${this.time}","Speed":"${this.speed}","Steer":"${this.steer}"}}`)
  }
}
