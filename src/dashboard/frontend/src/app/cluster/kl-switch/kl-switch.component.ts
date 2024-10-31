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
import { NgFor, NgIf } from '@angular/common';
import { WebSocketService } from '../../webSocket/web-socket.service';
import { Subscription } from 'rxjs';
import { ClusterService } from '../cluster.service';

@Component({
  selector: 'app-kl-switch',
  standalone: true,
  imports: [NgFor, NgIf],
  templateUrl: './kl-switch.component.html',
  styleUrl: './kl-switch.component.css'
})
export class KlSwitchComponent {
  public states = ['0', '15', '30'];
  public currentStateIndex = 0;
  
  public isMobile: boolean = false;

  public enableButon : Boolean = false;
  private enableButtonSubscription: Subscription | undefined;

  constructor(private webSocketService: WebSocketService,
    private clusterService: ClusterService
  ) { }

  ngOnInit()
  {
    this.enableButtonSubscription = this.webSocketService.receiveEnableButton().subscribe(
      (message) => {
        this.enableButon = message.value
      },
      (error) => {
        console.error('Error receiving enablebutton signal:', error);
      }
    );

    this.clusterService.isMobileDriving$.subscribe(isMobileDriving => {
      this.isMobile = isMobileDriving;
    });
  }

  setState(index: number) {
    if (this.currentState == '30' && this.currentState != this.states[index]) {
    }
    if(this.enableButon)
      this.currentStateIndex = index; 

    this.clusterService.updateKL(this.states[this.currentStateIndex])
    this.webSocketService.sendMessageToFlask(`{"Name": "Klem", "Value": "${this.states[this.currentStateIndex]}"}`);   
  }

  get currentState() {
    return this.states[this.currentStateIndex];
  }

  getSliderPosition(index: number): string {
    const totalStates = this.states.length;
    const percentage = (index / totalStates) * 100;
    return `calc(${percentage}%)`;
  }

  getSliderWidth(): string {
    return `calc(100% / ${this.states.length})`;
  }

  getSliderColor() {
    if (this.currentState === '0') {
      return '#d9534f';
    }

    if (this.currentState === '15') {
      return '#f0ad4e';
    }

    if (this.currentState === '30') {
      return '#5cb85c';
    }

    return '#2b8fd1';
  }
}

