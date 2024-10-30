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

import { Component, Input, ViewChild, ElementRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'

import { CommonModule } from '@angular/common';

import { MapCursorComponent } from './map-cursor/map-cursor.component';
import { MapSemaphoreComponent } from './map-semaphore/map-semaphore.component';
 
interface Semaphore { 
  x: number;
  y: number;
  state: string;
}

@Component({
  selector: 'app-map',
  standalone: true,
  imports: [MapCursorComponent, MapSemaphoreComponent, CommonModule],
  templateUrl: './map.component.html',
  styleUrl: './map.component.css'
})
export class MapComponent {
  @Input() cursorRotation: number = 0;

  @ViewChild('imageElement') imageElementRef!: ElementRef<HTMLImageElement>;
  @ViewChild('imageContainer') imageContainerRef!: ElementRef<HTMLImageElement>;

  private mapX: number = 0;
  private mapY: number = 0;

  private screenSize = {"width": 100, "height": 100}; // screen size in %
  private mapSize: number = 500; // map size in % for width
  private mapWidth: number = 0;
  private mapHeight: number = 0;

  private cursorSize: number = 6; // cursor size in % for width
  private semaphoreSize: number = 3;

  private semaphoreXOffset: number = 10;
  private semaphoreYOffset: number = 1.45;
  
  public semaphores: Map<number, Semaphore> = new Map<number, Semaphore>();

  private locationSubscription: Subscription | undefined;
  private semaphoresAndCarsSubscription: Subscription | undefined;

  constructor( private  webSocketService: WebSocketService) { }
  
  ngOnInit()
  {
    this.locationSubscription = this.webSocketService.receiveLocation().subscribe(
      (message) => {
        this.mapX = (parseFloat(message.value.x)*100/20.67)
        this.mapY = (100 - parseFloat(message.value.y)*100/13.76) //magic percent + same system of coordinates
        this.updateMap()
      },
    );

    this.semaphoresAndCarsSubscription = this.webSocketService.receiveSemaphores().subscribe(
      (message) => {
        const recv = message.value;
        this.semaphores.set(recv.id, {x: recv.x, y: recv.y, state: recv.state});
      },
    );
    this.updateMap()
  }

  ngOnDestroy() {
    if (this.locationSubscription) {
      this.locationSubscription.unsubscribe();
    }
    if (this.semaphoresAndCarsSubscription) {
      this.semaphoresAndCarsSubscription.unsubscribe();
    }
    this.webSocketService.disconnectSocket();
  }

  onLoadTrack(image: HTMLImageElement): void {
    const imageContainer = document.getElementById("map-track-image-container") as HTMLElement;

    if (imageContainer) {
      imageContainer.style.width = `${this.screenSize["width"]}%`;
      imageContainer.style.height = `${this.screenSize["height"]}%`;  
    }

    this.mapWidth = image.width;
    this.mapHeight = image.height;

    const map = document.getElementById("map-track-image") as HTMLElement;

    if (map) {
      map.style.width = `${this.mapSize}%`;
      map.style.height = `auto`;

      this.mapWidth = this.mapSize;
    }
  }

  onLoadCursor(): void {
    const cursor = document.getElementById("map-cursor") as HTMLElement;

    if (cursor) {
      cursor.style.width = `${this.cursorSize}%`;
      cursor.style.height = `auto`;
    }
  }

  onLoadSemaphore(id: number): void {
    const semaphore = document.getElementById("map-semaphore" + id) as HTMLElement;

    if (semaphore) {
      semaphore.style.position = "absolute";
      semaphore.style.width = `${this.semaphoreSize}%`;
      semaphore.style.height = `auto`;

      this.updateMap();
    }
  }

  updateMap(): void {
    const map = document.getElementById("map-track-image") as HTMLElement;
    let imageContainerHeight: number = 0;

    if (map) {
      if (this.imageContainerRef) {
        const imgContainer = this.imageContainerRef.nativeElement;
        const rect = imgContainer.getBoundingClientRect();
        imageContainerHeight = rect.height;
      }

      if (this.imageElementRef) {
        const image = this.imageElementRef.nativeElement;
        this.mapWidth = this.mapSize;
        this.mapHeight = (100 * image.height) / imageContainerHeight;
      }

      const top = (this.mapY * this.mapHeight) / 100 - this.mapHeight - (this.screenSize["height"] / 2 - this.mapHeight);
      const left = (this.mapX * this.mapWidth) / 100 - this.mapWidth - (this.screenSize["width"] / 2 - this.mapWidth);

      map.style.top = `${-top}%`;
      map.style.left = `${-left}%`;

      this.semaphores.forEach((value: Semaphore, key: number) => {
        console.log("???");
        
        const semaphore = document.getElementById("map-semaphore" + key) as HTMLElement;

        if (semaphore) { 
          const x = (value.x * 100/20.67);
          const y = (value.y * 100/13.76);

          const top_new = (y * this.mapHeight) / 100;
          const left_new = (x * this.mapWidth) / 100;
          
          semaphore.style.top = `${(-top - this.semaphoreXOffset) + top_new}%`;
          semaphore.style.left = `${(-left - this.semaphoreYOffset) + left_new}%`;
        }
      });
    }
  }
}
