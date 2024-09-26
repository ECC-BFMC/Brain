import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';

@Component({
  selector: 'app-car',
  standalone: true,
  imports: [],
  templateUrl: './car.component.html',
  styleUrl: './car.component.css'
})
export class CarComponent implements OnChanges {
  @Input() position: number = 0;
  @Input() leftLaneOn: boolean = false;
  @Input() rightLaneOn: boolean = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['position'] || changes['leftLaneOn'] || changes['rightLaneOn']) {
      this.updateCar();
    }
  }

  updateCar(): void {
    const car = document.getElementById("car-image-svg") as HTMLElement;
    if (car) {
      const xTranslation = this.position * 0.70;
      car.style.transform = `translateX(${xTranslation}%)`;

      const leftLine = document.getElementById("car-road-line-left") as HTMLElement;      
      const rightLine = document.getElementById("car-road-line-right") as HTMLElement;

      if (this.rightLaneOn)
        if (xTranslation > 55)
          rightLine.style.stroke = "red";
        else if (xTranslation > 30)
          rightLine.style.stroke = "orange";
        else
          rightLine.style.stroke = "green";
      else
        rightLine.style.stroke = "white";

      if (this.leftLaneOn) 
        if (xTranslation < -55)
          leftLine.style.stroke = "red";
        else if (xTranslation < -30)
          leftLine.style.stroke = "orange";
        else
          leftLine.style.stroke = "green";
      else
        leftLine.style.stroke = "white";
    }
  }
}



