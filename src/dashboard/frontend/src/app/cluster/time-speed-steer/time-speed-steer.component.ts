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

import { Component, OnInit, OnDestroy } from '@angular/core';
import { WebSocketService } from './../../webSocket/web-socket.service';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-time-speed-steer',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './time-speed-steer.component.html',
  styleUrl: './time-speed-steer.component.css'
})
export class TimeSpeedSteerComponent implements OnInit, OnDestroy {
  time: number = 0;
  speed: number = 0;
  steer: number = 0;
  private subscriptions = new Subscription();
  maxSteerUpperLimit: number = 25; // Default max steer limit
  maxSteerLowerLimit: number = -25; // Default min steer limit

  constructor(private webSocketService: WebSocketService) { }

  ngOnInit() {
    this.subscriptions.add(
      this.webSocketService.receiveSteerLimits().subscribe((event: { value: { upperLimit: number; lowerLimit: number } }) => {
        if (event && event.value) {
          this.maxSteerUpperLimit = Number((event.value["upperLimit"] / 10).toFixed(1));
          this.maxSteerLowerLimit = Number((event.value["lowerLimit"] / 10).toFixed(1));
        }
      })
    );
  }

  activateFunction() {
    // Ensure steer value is within limits
    const limitedSteer = Math.min(Math.max(this.steer, -this.maxSteerLowerLimit), this.maxSteerUpperLimit);
    this.webSocketService.sendMessageToFlask(`{"Name": "Control", "Value": {"Time":"${this.time*10}","Speed":"${this.speed*10}","Steer":"${limitedSteer*10}"}}`);
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }
}
