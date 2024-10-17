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



