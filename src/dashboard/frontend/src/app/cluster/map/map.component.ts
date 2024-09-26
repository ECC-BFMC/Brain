import { Component, Input, ViewChild, ElementRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'

import { MapCursorComponent } from './map-cursor/map-cursor.component';

@Component({
  selector: 'app-map',
  standalone: true,
  imports: [MapCursorComponent],
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
  private locationSubscription: Subscription | undefined;
  
  constructor( private  webSocketService: WebSocketService) { }
  
  ngOnInit()
  {
    this.updateMap()

    this.locationSubscription = this.webSocketService.receiveLocation().subscribe(
      (message) => {
        this.mapX = parseFloat(message.dict.x)
        this.mapY = parseFloat(message.dict.y)
        this.updateMap()
      },
    );
  }

  ngOnDestroy() {
    if (this.locationSubscription) {
      this.locationSubscription.unsubscribe();
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
    }
  }
}
