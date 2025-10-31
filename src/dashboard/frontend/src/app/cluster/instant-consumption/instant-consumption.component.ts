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
import { CommonModule } from '@angular/common';
import { WebSocketService} from '../../webSocket/web-socket.service'
import { ClusterService } from '../cluster.service';

@Component({
  selector: 'app-instant-consumption',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './instant-consumption.component.html',
  styleUrl: './instant-consumption.component.css'
})
export class InstantConsumptionComponent {
  private instant: number = 0;
  private needleStartRotation: number = 35;
  private pathStartPoint: number = 57;
  private pathEndPoint: number = 150;
  private xOffset: number = 17;
  private yOffset: number = -27;
  private angleAmplifier: number = 0.5;
  private instantSubscription: Subscription | undefined;
  private klSubscription: Subscription | undefined;
  private _currentValueAh: number = 0;
  private _showWarning: boolean = false;
  
  get currentValueAh(): number {
    return this._currentValueAh;
  }
  
  get showWarning(): boolean {
    return this._showWarning;
  }
  
  constructor( private  webSocketService: WebSocketService, private clusterService: ClusterService) { }

  ngOnInit()
  {
    this.updateNeedle();
    
    // Listen for instant
    this.instantSubscription = this.webSocketService.receiveInstantConsumption().subscribe({
      next: (message) => {
        // check if consumption exceeds 5.1 Ah
        this._currentValueAh = message.value / 1000; // convert mA to Ah
        this._showWarning = this._currentValueAh >= 5.1;
        
        // 100% - 5 Ah
        // 0%   - 0 Ah
        this.instant = Math.min(Math.max(this._currentValueAh * 100 / 5, 0), 100);
        this.updateNeedle();
      },
      error: () => {
        this._currentValueAh = 0;
        this._showWarning = false;
        this.instant = 0;
        this.updateNeedle();
      }
    });

    // Listen for KL state changes
    this.klSubscription = this.clusterService.kl$.subscribe({
      next: (klState) => {
        if (klState === '0') {
          this.instant = 0;
          this._currentValueAh = 0;
          this._showWarning = false;
          this.updateNeedle();
        }
      },
      error: () => {
        this._currentValueAh = 0;
        this._showWarning = false;
        this.instant = 0;
        this.updateNeedle();
      }
    });
  }

  ngOnDestroy() {
    if (this.instantSubscription) {
      this.instantSubscription.unsubscribe();
    }
    if (this.klSubscription) {
      this.klSubscription.unsubscribe();
    }
    this.webSocketService.disconnectSocket();
  }

  updateNeedle(): void {
    let xTranslation: number = 0;
    let yTranslation: number = 0;
    let rotation: number = 0;
    const needle = document.getElementById("instant-consumption-needle-group");
    const path = document.getElementById("instant-consumption-path");

    rotation += this.needleStartRotation;

    if (path instanceof SVGPathElement) {
      const currentPoint = this.pathStartPoint + (this.pathEndPoint - this.pathStartPoint) * this.instant / 100;
      const pathPoint = path.getPointAtLength(currentPoint);
      xTranslation = pathPoint.x + this.xOffset;
      yTranslation = pathPoint.y + this.yOffset;

      const nextPoint = path.getPointAtLength((this.pathEndPoint - this.pathStartPoint) * (this.instant + 1) / 100);
      const angle = Math.atan2(nextPoint.y - pathPoint.y, nextPoint.x - pathPoint.x) * 180 / Math.PI * this.angleAmplifier;
      
      rotation += angle;
    }

    if (needle) { 
      needle.style.transform = `translate(${xTranslation}px, ${yTranslation}px) rotate(${rotation}deg)`;
    }
  }
}