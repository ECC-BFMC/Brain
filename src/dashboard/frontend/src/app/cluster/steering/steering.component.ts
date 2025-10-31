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


@Component({
  selector: 'app-steering',
  standalone: true,
  imports: [],
  templateUrl: './steering.component.html',
  styleUrl: './steering.component.css'
})
export class SteeringComponent {
  public angle: number = 0;
  public maxSteerUpperLimit: number = 25; // Default max steer limit
  public maxSteerLowerLimit: number = -25; // Default min steer limit

  private steerSubscription: Subscription | undefined;
  private steerLimitsSubscription: Subscription | undefined;

  constructor( private  webSocketService: WebSocketService) { }

  ngOnInit()
  {
    // Listen for camera
    this.steerSubscription = this.webSocketService.receiveCurrentSteer().subscribe(
      (message) => {
        this.angle = message.value/10;
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );

    this.steerLimitsSubscription = this.webSocketService.receiveSteerLimits().subscribe(
      (message) => {
        this.maxSteerUpperLimit = Number((message.value["upperLimit"] / 10).toFixed(1));
        this.maxSteerLowerLimit = Number((message.value["lowerLimit"] / 10).toFixed(1));
      }
    );
  }

  ngOnDestroy() {
    if (this.steerSubscription) {
      this.steerSubscription.unsubscribe();
    }

    if (this.steerLimitsSubscription) {
      this.steerLimitsSubscription.unsubscribe();
    }

    this.webSocketService.disconnectSocket();
  }
}
