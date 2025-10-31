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
  selector: 'app-indicator',
  standalone: true,
  imports: [],
  templateUrl: './indicator.component.html',
  styleUrl: './indicator.component.css'
})
export class IndicatorComponent implements OnChanges {
  @Input() value: number | undefined;
  @Input() minValue: number = 0;
  @Input() maxValue: number = 100;
  @Input() title: string = "";
  @Input() titleOffset: number = 0;
  @Input() symbol: string = "";
  public valuePos: number = 0;
  public maxValueOpacity: number = 1;
  public minValueOpacity: number = 1;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['value']) {
      this.update();
    }
  }

  update(): void { 
    if (this.value !== undefined && this.value !== null) { 
      const currentValue = this.value * 100 / this.maxValue;
      this.valuePos = 80 - (currentValue * 0.85); // * 0.85 because we use only 85%

      if (this.valuePos >= 74) { 
        this.valuePos = 74;
      }

      if (this.valuePos <= 0) { 
        this.valuePos = 0;
      }

      if (this.valuePos <= 16) { 
        this.maxValueOpacity = 0;
      }
      else {
        this.maxValueOpacity = 1;
      }

      if (this.valuePos >= 59) { 
        this.minValueOpacity = 0;
      }
      else {
        this.minValueOpacity = 1;
      }
    }
  }
}
