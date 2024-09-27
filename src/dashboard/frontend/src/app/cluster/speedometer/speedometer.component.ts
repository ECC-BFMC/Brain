import { Component } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'

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
  
  constructor( private  webSocketService: WebSocketService) { }

  ngOnInit()
  {
    this.updateNeedle();

    // Listen for speed
    this.speedSubscription = this.webSocketService.receiveCurrentSpeed().subscribe(
      (message) => {
        // 100% - 60cm/s
        // 0%   - 0cm/s
        this.speed = Math.abs(message.value * 100 / 60);
        this.updateNeedle();
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
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