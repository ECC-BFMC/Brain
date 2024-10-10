import { WebSocketService } from './../../webSocket/web-socket.service';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common'

@Component({
  selector: 'app-record',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './record.component.html',
  styleUrl: './record.component.css'
})
export class RecordComponent {
  recording: boolean = false;
  text: string = "Start Record"

  constructor( private webSocketService: WebSocketService) { }

  changeState() {
    if(this.recording == false){
      this.recording = true;
      this.text = "Stop Record"
    }
    else {
      this.recording = false;
      this.text = "Stop Record"
    }

    this.webSocketService.sendMessageToFlask(`{"Name": "Record", "Value": "${this.recording}"}`);
  }

  getButtonColor() {
    if (this.recording === true) { 
      return "#5cb85c";
    }

    return "#d9534f";
  }
}
