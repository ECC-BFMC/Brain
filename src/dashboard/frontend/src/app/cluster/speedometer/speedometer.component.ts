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

@Component({
  selector: 'app-speedometer',
  standalone: true,
  imports: [],
  templateUrl: './speedometer.component.html',
  styleUrl: './speedometer.component.css'
})
export class SpeedometerComponent {
  private speed: number = 0;
  private needleStartRotation: number = -30;
  private pathStartPoint: number = 72;
  private pathEndPoint: number = 354;
  private xOffset: number = -32;
  private yOffset: number = -44;
  private angleAmplifier: number = 1.2;
  private speedSubscription: Subscription | undefined;
  private klSubscription: Subscription | undefined;
  constructor( private  webSocketService: WebSocketService, private clusterService: ClusterService) { }

  ngOnInit()
  {
    this.updateNeedle();

    // Listen for speed
    this.speedSubscription = this.webSocketService.receiveCurrentSpeed().subscribe(
      (message) => {
        // 100% - 60cm/s
        // 0%   - 0cm/s
        this.speed = Math.abs(message.value/10 * 100 / 60);
        this.updateNeedle();
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );

    this.klSubscription = this.clusterService.kl$.subscribe(
      (klState) => {
        if (klState === '0') {
          this.speed = 0;
          this.updateNeedle();
        }
      },
      (error) => {
        console.error('Error receiving KL state:', error);
      }
    );
  }

  ngOnDestroy() {
    if (this.speedSubscription) {
      this.speedSubscription.unsubscribe();
    }
    this.webSocketService.disconnectSocket();
  }

  updateNeedle(): void {
    let xTranslation: number = 0
    let yTranslation: number = 0
    let rotation: number = 0
    const needle = document.getElementById("speedometer-needle-group");
    const path = document.getElementById("speedometer-path");

    rotation += this.needleStartRotation;

    if (path instanceof SVGPathElement) {
      const currentPoint = this.pathStartPoint + (this.pathEndPoint - this.pathStartPoint) * this.speed / 100
      const pathPoint = path.getPointAtLength(currentPoint);
      xTranslation = pathPoint.x + this.xOffset;
      yTranslation = pathPoint.y + this.yOffset;

      const nextPoint = path.getPointAtLength((this.pathEndPoint - this.pathStartPoint) * (this.speed + 1) / 100);
      const angle = (Math.atan2(nextPoint.y - pathPoint.y, nextPoint.x - pathPoint.x) - Math.PI) * 180 / Math.PI * this.angleAmplifier;
      
      rotation += angle;
    }

    if (needle) { 
      needle.style.transform = `translate(${xTranslation}px, ${yTranslation}px) rotate(${rotation}deg)`;
    }
  }
}