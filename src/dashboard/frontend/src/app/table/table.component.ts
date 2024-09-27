import { Component, OnInit} from '@angular/core';
import { CommonModule } from '@angular/common'; // Import CommonModule
import { WebSocketService } from '../webSocket/web-socket.service';
import { FormsModule } from '@angular/forms'; // Import FormsModule
import { Subscription } from 'rxjs';
@Component({
  selector: 'app-table',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.css']
})
export class TableComponent implements OnInit {
  items: { 
    channel: string, 
    value: any, 
    initialValue: any,
    interval: number, 
    type: any, 
    values: any[], 
    checked: any ,
    hasChanged: boolean
  }[] = [];
  private loadsSubscription: Subscription | undefined;
  private lastReceivedTimestamp: { [key: string]: number } = {}; // Track last received timestamp

  constructor(private webSocketService: WebSocketService) { }

  ngOnInit() {
    this.loadsSubscription = this.webSocketService.receiveLoadTable().subscribe(
      (message) => {
        this.items = message.data
      },
    );

    this.webSocketService.receiveUnhandledEvents().subscribe(event => {
      this.updateTable(event.channel, event.data.value);
    });

    this.reset();
  }

  private updateTable(channel: string, value: any) {
    const currentTime = Date.now();
    const lastTimestamp = this.lastReceivedTimestamp[channel] || currentTime;
    const interval = (currentTime - lastTimestamp) / 1000;
    this.lastReceivedTimestamp[channel] = currentTime;

    const existingItem = this.items.find(item => item.channel === channel);

    if (existingItem) {
      existingItem.value = value;
      existingItem.interval = interval;

      // Compare current value to initial value and mark as changed if necessary
      existingItem.hasChanged = existingItem.value !== existingItem.initialValue;
    } else {
      this.items.push({ 
        channel, 
        value: value, 
        initialValue: value, 
        interval, 
        type: 'default', 
        values: [], 
        checked: false,
        hasChanged: false 
      });
    }
  }
  save() {
    const nonDefaultItems = this.items.filter(item => item.type !== 'default');
    nonDefaultItems.forEach(item => {
      item.initialValue = item.value;
      item.hasChanged = false;
    });
    let valueToSend = JSON.stringify(nonDefaultItems, null, 2)
    this.webSocketService.SaveTable(valueToSend)
  }

  reset() {
    this.webSocketService.LoadTable("Give me the table please :)")
  }

  load() {
    const nonDefaultItems = this.items.filter(item => item.type !== 'default' && item.checked == true);
    nonDefaultItems.forEach(item => {
      let value = item.value
      let channel = item.channel
      this.webSocketService.sendMessageToFlask(`{"Name": "${channel}", "Value": "${value/100}"}`);
    });
  }
}

