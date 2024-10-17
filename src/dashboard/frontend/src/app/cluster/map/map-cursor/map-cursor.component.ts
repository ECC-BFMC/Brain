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

import { Component, Input, OnChanges, SimpleChanges, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-map-cursor',
  standalone: true,
  imports: [],
  templateUrl: './map-cursor.component.html',
  styleUrl: './map-cursor.component.css'
})
export class MapCursorComponent implements OnChanges {
  @Input() cursorRotation: number = 0;
  @Output() cursorLoaded = new EventEmitter<void>();

  ngOnInit(): void {
    this.cursorLoaded.emit();
  }
  
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['cursorRotation']) {
      this.updateRotation();
    }
  }

  updateRotation(): void {
    const cursor = document.getElementById("map-cursor-arrow") as HTMLElement;
    if (cursor) {
      cursor.style.transform = `rotate(${this.cursorRotation}deg)`;
    }
  }
}
