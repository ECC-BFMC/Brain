# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC organizers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE


from enum import Enum

class BigPrint(Enum):
    C4_BOMB = r"""
                _______________________
              /                       \
              | [██████]    [██████]    |
              | [██████]    [██████]    |
              | [██████]    [██████]    |
              |       TIMER: 00:10      |
              |_________________________|
              \_______________________/
                      LET'S GO!!!
              """

    PLEASE_WAIT = """
                  PPPP   L        EEEEE    A    SSSS  EEEEE       W      W   A   III TTTTT
                  P   P  L        E       A A   S     E           W      W  A A   I    T  
                  PPPP   L        EEEE   A   A   SSS  EEEE        W  W   W A   A  I    T  
                  P      L        E      AAAAA      S E           W W W W  AAAAA  I    T  
                  P      LLLLLL   EEEEE  A   A  SSSS  EEEEE        W   W   A   A III   T  
                  """

    PRESS_CTRL_C =  """
                    PPPP   RRRR   EEEEE  SSSS  SSSS       CCCC  TTTTT RRRR    L          ++       CCCC      !!! 
                    P   P  R   R  E     S     S          C        T   R   R   L          ++      C          !!! 
                    PPPP   RRRR   EEEE   SSS   SSS       C        T   RRRR    L      ++++++++++  C          !!! 
                    P      R R    E         S     S      C        T   R R     L          ++      C            
                    P      R  R   EEEEE  SSSS  SSSS       CCCC    T   R  R    LLLLL      ++       CCCC      !!!
                    """