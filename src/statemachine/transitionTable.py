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

from typing import Dict

try:
    from src.statemachine.systemMode import SystemMode
except ImportError:
    from systemMode import SystemMode


class TransitionTable:
    """
    Manages state transition rules for the StateMachine.

    This class encapsulates the logic for validating mode transitions using a dictionary-based transition table.
    The table maps the current SystemMode and an action string to the next SystemMode, if the transition is valid.
    The get_next_mode method returns a dictionary indicating whether the transition is valid and, if so, provides the next SystemMode object (not its string name).
    """
    # Transition table: current_mode -> set of allowed next modes based on the action
    _TRANSITIONS: Dict[SystemMode, Dict[str, SystemMode]] = {
        SystemMode.DEFAULT: {
            "dashboard_auto_button" : SystemMode.AUTO,
            "dashboard_manual_button" : SystemMode.MANUAL,
            "dashboard_legacy_button" : SystemMode.LEGACY,
            "dashboard_stop_button" : SystemMode.STOP
        },
        SystemMode.AUTO: {
            "dashboard_manual_button" : SystemMode.MANUAL,
            "dashboard_legacy_button" : SystemMode.LEGACY,
            "dashboard_stop_button" : SystemMode.STOP,
            "dashboard_auto_button" : SystemMode.AUTO # this is a special case, because the auto button is always available
        },
        SystemMode.MANUAL: {    
            "dashboard_auto_button" : SystemMode.AUTO,
            "dashboard_legacy_button" : SystemMode.LEGACY,
            "dashboard_stop_button" : SystemMode.STOP,
            "dashboard_manual_button" : SystemMode.MANUAL # this is a special case, because the manual button is always available
        },
        SystemMode.LEGACY: {
            "dashboard_auto_button" : SystemMode.AUTO,
            "dashboard_manual_button" : SystemMode.MANUAL,
            "dashboard_stop_button" : SystemMode.STOP,
            "dashboard_legacy_button" : SystemMode.LEGACY # this is a special case, because the legacy button is always available
        },
        SystemMode.STOP: {
            "dashboard_auto_button" : SystemMode.AUTO,
            "dashboard_manual_button" : SystemMode.MANUAL,
            "dashboard_legacy_button" : SystemMode.LEGACY,
            "dashboard_stop_button" : SystemMode.STOP # this is a special case, because the stop button is always available
        }
    }
    
    @classmethod
    def get_next_mode(cls, currentMode: SystemMode, action: str):
        """Check if transition is valid."""
        next_mode = cls._TRANSITIONS.get(currentMode, {}).get(action, None)
        return {"transition_valid": next_mode is not None, "next_mode": next_mode if next_mode is not None else None}
