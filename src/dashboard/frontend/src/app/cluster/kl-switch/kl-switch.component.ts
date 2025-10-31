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
export class KlSwitchComponent implements OnInit, OnDestroy {
  public states = ['0', '15', '30'];
  public currentStateIndex = 0;
  
  public isMobile: boolean = false;

  public enableButton : Boolean = false;
  public serialConnected: Boolean = true;  // Track serial connection status
  private enableButtonSubscription: Subscription | undefined;

  constructor(
    private webSocketService: WebSocketService,
    private clusterService: ClusterService
  ) {}

  ngOnInit()
  {
    // Send KL 0 to backend when entering the website
    this.clusterService.updateKL('0');
    this.webSocketService.sendMessageToFlask(`{"Name": "Klem", "Value": "0"}`);
    
    this.enableButtonSubscription = this.webSocketService.receiveEnableButton().subscribe(
      (message) => {
        this.enableButton = message.value;
      },
      (error) => {
        console.error('Error receiving enablebutton signal:', error);
      }
    );

    this.clusterService.serialConnectionState$.subscribe(serialConnected => {
      this.serialConnected = serialConnected;
      if (!serialConnected) {
        this.currentStateIndex = 0;
        this.clusterService.updateKL('0');
      }
    });

    this.clusterService.isMobileDriving$.subscribe(isMobileDriving => {
      this.isMobile = isMobileDriving;
    });
  }

  // Prevent interaction when serial is disconnected without changing visual styles
  blockIfDisconnected(event: Event) {
    if (!this.serialConnected) {
      event.preventDefault();
      event.stopPropagation();
    }
  }

  setState(index: number) {
    // Don't allow KL changes if serial is disconnected
    if (!this.serialConnected) {
      console.warn('KL Switch: Cannot change KL state - serial connection is lost');
      return;
    }

    if (this.currentState == '30' && this.currentState != this.states[index]) {
    }
    if(this.enableButton)
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

  ngOnDestroy() {
    if (this.enableButtonSubscription) {
      this.enableButtonSubscription.unsubscribe();
    }
  }
}

