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
import { NgFor } from '@angular/common';
import { Subscription } from 'rxjs';
import { trigger, state, style, transition, animate } from '@angular/animations';
import { WebSocketService } from '../../webSocket/web-socket.service'
import { warningLightDictionary } from './warningLightDictionary';

@Component({
  selector: 'app-warning-light',
  standalone: true,
  imports: [NgFor],
  templateUrl: './warning-light.component.html',
  styleUrl: './warning-light.component.css',
  animations: [
    trigger('fadeInOut', [
      state('void', style({ opacity: 0 })),
      transition(':enter', [
        animate('0.5s ease-in', style({ opacity: 1 }))
      ]),
      transition(':leave', [
        animate('0.5s ease-out', style({ opacity: 0 }))
      ])
    ])
  ]
})
export class WarningLightComponent {
  private warningsSubscription: Subscription | undefined;
  warningLights: Array<{"type": string, "time": number}> = [];
  private warningLightDisplayTime: number = 5;
  private callInterval: number = 0.5;
  private intervalId: any;
  private warningLightDictionaryLength: number = Object.keys(warningLightDictionary).length;

  constructor( private  webSocketService: WebSocketService) { }
  ngOnInit() {
    this.warningsSubscription = this.webSocketService.receiveWarningSignal().subscribe(
      (message) => {
        let id = message.value.WarningID
        let type = message.value.WarningName
        this.setWarningLightType(String(id))
      },
    );
  }

  startRepeatingFunction(): void {
    this.intervalId = setInterval(() => {
      this.repeatingFunction();
    }, this.callInterval * 1000);
  }

  repeatingFunction(): void {
    for (let i = 0; i < this.warningLights.length; i++) {
      this.warningLights[i].time -= this.callInterval;
      if (this.warningLights[i].time <= 0) {
        this.triggerRemoveWarningLight(i);
      }
    }

    if (this.warningLights.length === 0) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  triggerRemoveWarningLight(index: number): void {
    this.warningLights.splice(index, 1);
  }

  stopRepeatingFunction(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  ngOnDestroy(): void {
    this.stopRepeatingFunction();
  }

  setWarningLightType(lightType: string): void {
    const lightTypeInt = parseInt(lightType);
    if (lightTypeInt < 0 || lightTypeInt > this.warningLightDictionaryLength || isNaN(lightTypeInt)) {
      return;
    }

    for (let i = 0; i < this.warningLights.length; i++) {
      if (this.warningLights[i].type === warningLightDictionary[lightTypeInt.toString()]) {
        this.warningLights[i].time = this.warningLightDisplayTime;
        return;
      }
    }

    this.warningLights.push({"type": warningLightDictionary[lightTypeInt.toString()], "time": this.warningLightDisplayTime});

    if (!this.intervalId) {
      this.startRepeatingFunction();
    }
  }
}
