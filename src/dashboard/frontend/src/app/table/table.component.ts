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
  private loadedMap: any = {};

  constructor(private webSocketService: WebSocketService) { }

  ngOnInit() {
    this.loadsSubscription = this.webSocketService.receiveLoadTable().subscribe((message) => {
      // New keyed-by-channel format: keep original map and derive UI items
      this.loadedMap = message.data || {};
      const entries = Object.entries(this.loadedMap) as [string, any][];
      this.items = entries.map(([channel, item]) => ({
        channel,
        value: item?.value !== null && item?.value !== undefined ? String(item.value) : '',
        initialValue: item?.initialValue !== null && item?.initialValue !== undefined ? String(item.initialValue) : '',
        hasChanged: item?.hasChanged || false,
        checked: item?.checked || false,
        values: item?.values || [],
        type: item?.type || 'default',
        interval: item?.interval ?? 0,
      }));
    });

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
      existingItem.value = value !== null && value !== undefined ? String(value) : '';
      existingItem.interval = interval;

      // Compare current value to initial value and mark as changed if necessary
      existingItem.hasChanged = existingItem.value !== existingItem.initialValue;
    } else {
      const stringValue = value !== null && value !== undefined ? String(value) : '';
      this.items.push({ 
        channel, 
        value: stringValue, 
        initialValue: stringValue, 
        interval, 
        type: 'default', 
        values: [], 
        checked: false,
        hasChanged: false 
      });
    }
  }
  save() {
    const nonDefaultItems = this.items.filter(item => item.type === 'dropdown' || item.type === 'slider');
    // Update only fields in the loaded map for existing channels
    nonDefaultItems.forEach(item => {
      const entry = this.loadedMap[item.channel] || {};
      entry.value = item.value;
      entry.initialValue = item.value; // reset to saved value
      entry.hasChanged = false;
      // Preserve other fields as-is (type, values, checked, command, etc.)
      this.loadedMap[item.channel] = entry;
    });
    const valueToSend = JSON.stringify(this.loadedMap, null, 2);
    this.webSocketService.SaveTable(valueToSend)
  }

  reset() {
    this.webSocketService.LoadTable("Give me the table please :)")
  }

  load() {
    const SliderItems = this.items.filter(item => item.type == 'slider' && item.checked == true);
    SliderItems.forEach(item => {
      let value = item.value
      let channel = item.channel
      this.webSocketService.sendMessageToFlask(`{"Name": "${channel}", "Value": "${value/100}"}`);
    });
    const nonDefaultItems = this.items.filter(item => item.type == 'dropdown' && item.checked == true);
    nonDefaultItems.forEach(item => {
      let value = 1
      if (item.value == "False")
        value = 0

      let channel = item.channel
      this.webSocketService.sendMessageToFlask(`{"Name": "${channel}", "Value": "${value}"}`);
    });
  }
  getFontSize(value: string): string {
    if (!value || value === null || value === undefined) {
      return '1vw'; // Return default size for undefined/null values
    }
    const baseSize = 1; 
    const maxLength = 15; 
    return `${Math.max(baseSize - (value.length / maxLength) * 0.5, 0.5)}vw`;
  }
  
}

