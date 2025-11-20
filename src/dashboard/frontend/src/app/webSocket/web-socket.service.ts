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

import { Injectable } from '@angular/core';
import { Socket } from 'ngx-socket-io';
import { Observable, Subject } from 'rxjs';
@Injectable({
  providedIn: 'root',
})
export class WebSocketService {
  private webSocket: Socket;
  private connectionStatusSubject = new Subject<'connected' | 'disconnected' | 'error'>();
  connectionStatus$ = this.connectionStatusSubject.asObservable();

  private eventSubject = new Subject<{ channel: string, data: any }>();
  private handledEvents = new Set([
    'heartbeat',
    'heartbeat_disconnect',
    'StateChange',
    'memory_channel',
    'cpu_channel',
    'disk_channel',
    'webCamera',
    'Location',
    'Cars',
    'Semaphores',
    'after connect',
    'InstantConsumption',
    'loadBack',
    'WarningSignal',
    'response',
    'BatteryLvl',
    'ResourceMonitor',
    'serialCamera',
    'Recording',
    'CurrentSpeed',
    'CurrentSteer',
    'EnableButton',
    'SteeringLimits',
    'Calibration',
    'CalibPWMData',
    'CalibRunDone',
    'ImuAck'
  ]);

  constructor() {
    this.webSocket = new Socket({
    url: "http://192.168.88.48:5005",
    options: {},
    });

    // Listen for all messages from the WebSocket server
    this.webSocket.onAny((eventName: string, data: any) => {
      if (!this.handledEvents.has(eventName)) {
        this.eventSubject.next({ channel: eventName, data });
      }
    });

    this.webSocket.ioSocket.on('connect', () => {
      this.connectionStatusSubject.next('connected');
    });

    this.webSocket.ioSocket.on('disconnect', () => {
      this.connectionStatusSubject.next('disconnected');
    });

    this.webSocket.ioSocket.on('connect_error', (error: any) => {
      this.connectionStatusSubject.next('error');
    });

    this.webSocket.ioSocket.on('reconnect', () => {
      this.connectionStatusSubject.next('connected');
    });

    this.webSocket.ioSocket.on('reconnect_attempt', () => {
    });

    this.webSocket.ioSocket.on('reconnect_error', (error: any) => {
      this.connectionStatusSubject.next('error');
    });
  }

  // Method to start connection/handshake with the server
  sendMessageToFlask(message: any) {
    this.webSocket.emit('message', message);
  }

  SaveTable(message: any) {
    this.webSocket.emit('save', message);
  }

  LoadTable(message: any) {
    this.webSocket.emit('load', message);
  }

  receiveHeartbeat(): Observable<any> {
    return this.webSocket.fromEvent('heartbeat');
  }

  receiveHeartbeatDisconnect(): Observable<any> {
    return this.webSocket.fromEvent('heartbeat_disconnect');
  }

  receiveSessionAccess(): Observable<any> {
    return this.webSocket.fromEvent('session_access');
  }

  receiveCurrentSerialConnectionState(): Observable<any> {
    return this.webSocket.fromEvent('current_serial_connection_state');
  }

  // Method to receive memory usage updates
  receiveMemoryUsage(): Observable<any> {
    return this.webSocket.fromEvent('memory_channel');
  }

  receiveImuData(): Observable<any> {
    return this.webSocket.fromEvent('ImuData');
  }

  receiveResourceMonitor(): Observable<any> {
    return this.webSocket.fromEvent('ResourceMonitor');
  }

  receiveWarningSignal(): Observable<any> {
    return this.webSocket.fromEvent('WarningSignal');
  }

  receiveLoadTable(): Observable<any> {
    return this.webSocket.fromEvent('loadBack');
  }

  // Method to receive CPU usage updates
  receiveCpuUsage(): Observable<any> {
    return this.webSocket.fromEvent('cpu_channel');
  }

  // Method to receive image updates
  receiveCamera(): Observable<any> {
    return this.webSocket.fromEvent('serialCamera');
  }

  // Method to receive location updates
  receiveLocation(): Observable<any> {
    return this.webSocket.fromEvent('Location');
  }

  // Method to get Enable Buton signal
  receiveEnableButton(): Observable<any> {
    return this.webSocket.fromEvent('EnableButton');
  }

  // Method to receive cars location updates
  receiveCars(): Observable<any> {
    return this.webSocket.fromEvent('Cars');
  }

  // Method to receive instant consumption updates
  receiveInstantConsumption(): Observable<any> {
    return this.webSocket.fromEvent('InstantConsumption');
  }

  // Method to receive battery level updates
  receiveBatteryLevel(): Observable<any> {
    return this.webSocket.fromEvent('BatteryLvl');
  }

  // Method to receive semaphores state updates
  receiveSemaphores(): Observable<any> {
    return this.webSocket.fromEvent('Semaphores');
  }

  // Method to receive current speed state updates
  receiveCurrentSpeed(): Observable<any> {
    return this.webSocket.fromEvent('CurrentSpeed');
  }

  // Method to receive current speed state updates
  receiveCurrentSteer(): Observable<any> {
    return this.webSocket.fromEvent('CurrentSteer');
  }

  // Method to receive current speed state updates
  receiveSerialConnectionState(): Observable<any> {
    return this.webSocket.fromEvent('SerialConnectionState');
  }

  receiveCalibrationData(): Observable<any> {
    return this.webSocket.fromEvent('Calibration');
  }

  receiveSteerLimits(): Observable<any> {
    return this.webSocket.fromEvent('SteeringLimits');
  }

  receiveNucleoAlive(): Observable<any> {
    return this.webSocket.fromEvent('AliveSignal');
  }

  // Method to receive the initial connection confirmation
  onConnect(): Observable<any> {
    return this.webSocket.fromEvent('after connect');
  }

  isConnected(): boolean {
    return this.webSocket.ioSocket.connected;
  }

  getConnectionStatus(): 'connected' | 'disconnected' | 'error' {
    if (this.webSocket.ioSocket.connected) {
      return 'connected';
    } else if (this.webSocket.ioSocket.disconnected) {
      return 'disconnected';
    } else {
      return 'error';
    }
  }

  reconnect(): void {
    this.webSocket.ioSocket.connect();
  }

  isReconnecting(): boolean {
    return this.webSocket.ioSocket.connecting;
  }

  // Method to end the WebSocket connection
  disconnectSocket() {
    this.webSocket.disconnect();
  }

  // Method to receive any unhandled event
  receiveUnhandledEvents(): Observable<{ channel: string, data: any }> {
    return this.eventSubject.asObservable();
  }
}
