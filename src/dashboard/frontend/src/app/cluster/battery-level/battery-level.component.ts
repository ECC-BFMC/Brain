import { Component } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'

@Component({
  selector: 'app-battery-level',
  standalone: true,
  imports: [],
  templateUrl: './battery-level.component.html',
  styleUrl: './battery-level.component.css'
})
export class BatteryLevelComponent {
  private battery: number = 0;
  private needleStartRotation: number = 30;
  private pathStartPoint: number = 72;
  private pathEndPoint: number = 356;
  private xOffset: number = 30;
  private yOffset: number = -48;
  private angleAmplifier: number = 1.2;
  private batterySubscription: Subscription | undefined;
  
  constructor( private  webSocketService: WebSocketService) { }

  ngOnInit()
  {
    this.updateNeedle();
    
    // Listen for battery
    this.batterySubscription = this.webSocketService.receiveBatteryLevel().subscribe(
      (message) => {
        this.battery = message['int'];
        this.updateNeedle();
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );
  }

  ngOnDestroy() {
    if (this.batterySubscription) {
      this.batterySubscription.unsubscribe();
    }
    this.webSocketService.disconnectSocket();
  }

  updateNeedle(): void {
    let xTranslation: number = 0
    let yTranslation: number = 0
    let rotation: number = 0
    const needle = document.getElementById("battery-level-needle-group");
    const path = document.getElementById("battery-level-path");
    
    rotation += this.needleStartRotation;

    if (path instanceof SVGPathElement) {
      const currentPoint = this.pathStartPoint + (this.pathEndPoint - this.pathStartPoint) * this.battery / 100
      const pathPoint = path.getPointAtLength(currentPoint);
      xTranslation = pathPoint.x + this.xOffset;
      yTranslation = pathPoint.y + this.yOffset;

      const nextPoint = path.getPointAtLength((this.pathEndPoint - this.pathStartPoint) * (this.battery + 1) / 100);
      const angle = Math.atan2(nextPoint.y - pathPoint.y, nextPoint.x - pathPoint.x) * 180 / Math.PI * this.angleAmplifier;
      
      rotation += angle;
    }

    if (needle) { 
      needle.style.transform = `translate(${xTranslation}px, ${yTranslation}px) rotate(${rotation}deg)`;
    }
  }

}