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

import { Component } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'
import { ClusterService } from '../cluster.service';
import { IndicatorComponent } from './indicator/indicator.component';

@Component({
  selector: 'app-hardware-data',
  standalone: true,
  imports: [IndicatorComponent],
  templateUrl: './hardware-data.component.html',
  styleUrl: './hardware-data.component.css'
})
export class HardwareDataComponent {
  private cpuSubscription: Subscription | undefined;
  private memorySubscription: Subscription | undefined;
  private resourceSubscription: Subscription | undefined;
  private klSubscription: Subscription | undefined;
  private watchdogInterval: any;
  private lastCpuUpdateMs: number = 0;
  private lastMemoryUpdateMs: number = 0;
  private lastResourceUpdateMs: number = 0;
  public cpuTemp: number = 0;
  public cpuUsage: number = 0;
  public memoryUsage: number = 0;
  public heap: number = 0;
  public stack: number = 0;
  
  constructor(private  webSocketService: WebSocketService, private clusterService: ClusterService) { }

  ngOnInit()
  {
    // Listen for cpu data
    this.cpuSubscription = this.webSocketService.receiveCpuUsage().subscribe(
      (message) => {
        this.lastCpuUpdateMs = Date.now();
        this.cpuTemp = message['data']['temp'];
        this.cpuUsage = parseInt(message['data']['usage']);
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );
    
    this.resourceSubscription = this.webSocketService.receiveResourceMonitor().subscribe(
      (message) =>{
        this.lastResourceUpdateMs = Date.now();
        this.heap = Math.round(message.value['heap']);
        this.stack = Math.round(message.value['stack']);
      },
      (error) => {
        console.error('Error receiving resource monitor:', error);
      }
    );

    this.memorySubscription = this.webSocketService.receiveMemoryUsage().subscribe(
      (message) => {
        this.lastMemoryUpdateMs = Date.now();
        this.memoryUsage = Math.round(message['data']);
        
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );

    // Listen for KL state changes
    this.klSubscription = this.clusterService.kl$.subscribe(
      (klState) => {
        if (klState === '0') {
          this.resetNucleoData();
        }
      },
      (error) => {
        console.error('Error receiving KL state:', error);
      }
    );

    // Watchdog to reset indicators if no data for > 3 seconds
    this.watchdogInterval = setInterval(() => {
      const now = Date.now();
      if (now - this.lastCpuUpdateMs > 5000) {
        this.cpuTemp = 0;
        this.cpuUsage = 0;
      }
      if (now - this.lastMemoryUpdateMs > 5000) {
        this.memoryUsage = 0;
      }
      if (now - this.lastResourceUpdateMs > 5000) {
        this.heap = 0;
        this.stack = 0;
      }
    }, 1000);
  }

  ngOnDestroy() {
    if (this.cpuSubscription) {
      this.cpuSubscription.unsubscribe();
    }
    if (this.memorySubscription) {
      this.memorySubscription.unsubscribe();
    }
    if (this.resourceSubscription) {
      this.resourceSubscription.unsubscribe();
    }
    if (this.klSubscription) {
      this.klSubscription.unsubscribe();
    }
    if (this.watchdogInterval) {
      clearInterval(this.watchdogInterval);
    }
    this.webSocketService.disconnectSocket();
  }

  resetHardwareData(): void {
    this.cpuTemp = 0;
    this.cpuUsage = 0;
    this.memoryUsage = 0;
    this.heap = 0;
    this.stack = 0;
  }

  resetNucleoData(): void {
    this.heap = 0;
    this.stack = 0;
  }
}
