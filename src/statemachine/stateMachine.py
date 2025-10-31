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

import threading
import multiprocessing
import os
import atexit
from typing import Dict
from src.statemachine.systemMode import SystemMode
from src.statemachine.transitionTable import TransitionTable
from src.utils.messages.messageHandlerSender import messageHandlerSender
from src.utils.messages.allMessages import StateChange

class StateMachine:
    """
    Multiprocessing-safe Singleton StateMachine with transition validation.
    
    Features:
    - Singleton instance per process (thread-safe)
    - Shared state across all processes
    - Process and thread-safe operations
    - Automatic cleanup on process exit
    - Transition validation using external TransitionTable
    
    Usage:
        # 1. In your MAIN process, initialize the shared state FIRST
        StateMachine.initialize_shared_state(queueList)
        
        # 2. In any process, get the instance with queueList
        state_machine = StateMachine.get_instance(queueList)
        
        # 3. Use it - transitions are automatically validated
        state_machine.request_mode(SystemMode.AUTO)
        
        # Cleanup happens automatically when the main process exits!
    """
    
    # per-process singleton management
    _instances: Dict[int, 'StateMachine'] = {}
    _thread_lock = threading.Lock()
    
    # shared state across processes
    _manager = None
    _shared_state = None
    _process_lock = None
    _initialized = False
    _queueList = None

    def __new__(cls, *args, **kwargs) -> 'StateMachine':
        """Ensure only one instance per process (thread-safe)."""
        process_id = os.getpid()
        
        with cls._thread_lock:
            if process_id not in cls._instances:
                cls._instances[process_id] = super(StateMachine, cls).__new__(cls)
            return cls._instances[process_id]

    @classmethod
    def initialize_shared_state(cls, queueList):
        """Initialize shared state - MUST be called from the main.py BEFORE creating other processes."""
        if cls._manager is not None:
            return
            
        cls._manager = multiprocessing.Manager()
        cls._shared_state = cls._manager.dict()
        cls._process_lock = cls._manager.Lock()
        
        # initialize shared state
        cls._shared_state['mode'] = SystemMode.DEFAULT
        cls._queueList = queueList
        cls._initialized = True
        
        # register automatic cleanup on process exit
        atexit.register(cls.cleanup)
        
    @classmethod
    def initialize_starting_mode(cls):
        """Initialize the starting mode."""
        if not cls._initialized:
            raise RuntimeError("Must call StateMachine.initialize_shared_state() from the main.py before creating any instances.")

        cls._send_starting_mode(cls._shared_state['mode'])

    @classmethod
    def get_instance(cls):
        """Get the singleton instance for this process."""
        return cls()

    def __init__(self):
        """Initialize the StateMachine instance."""
        if not self._initialized:
            raise RuntimeError("Must call StateMachine.initialize_shared_state() from the main.py before creating any instances.")

        # only initialize once per instance
        if not getattr(self, '_instance_initialized', False):
            self.stateChangeSender =  messageHandlerSender(StateMachine._queueList, StateChange)
            setattr(self, '_instance_initialized', True)

    def request_mode(self, action: str) -> bool:
        """Request a mode change if the transition is valid."""
        if self._process_lock is None or self._shared_state is None:
            raise RuntimeError("Shared state not initialized")
            
        with self._process_lock:
            current_mode = self._shared_state['mode']

            # validate transition
            mode = TransitionTable.get_next_mode(current_mode, action)
            if not mode['transition_valid']:
                print(f"\033[1;97m[ State Machine ] :\033[0m \033[1;93mWARNING\033[0m - Invalid transition from \033[1;94m{current_mode.name}\033[0m with action \033[1;94m{action}\033[0m, ignoring request")
                return False

            self._shared_state['mode'] = mode['next_mode']
            
            if current_mode.name == mode['next_mode'].name:
                # print(f"\033[1;97m[ State Machine ] :\033[0m \033[1;93mWARNING\033[0m - Already in \033[1;94m{mode['next_mode'].name}\033[0m mode")
                return False
            
            print(f"\033[1;97m[ State Machine ] :\033[0m \033[1;92mINFO\033[0m - Mode changed from \033[1;94m{current_mode.name}\033[0m to \033[1;94m{mode['next_mode'].name}\033[0m")

            # send state change notification
            self._send_state_change(mode['next_mode'])
            return True

    def get_mode(self) -> SystemMode:
        """Get the current mode (multiprocessing-safe)."""
        if self._process_lock is None or self._shared_state is None:
            raise RuntimeError("Shared state not initialized")
            
        with self._process_lock:
            return self._shared_state['mode']

    def _send_state_change(self, mode: SystemMode):
        """Send state change notification via message queue."""
        if self.stateChangeSender:
            try:
                self.stateChangeSender.send(mode.name)
            except Exception as e:
                print(f"\033[1;97m[ State Machine ] :\033[0m \033[1;93mWARNING\033[0m - Failed to send state change: {e}")

    @classmethod
    def _send_starting_mode(cls, mode: SystemMode):
        """Send the starting mode to all listeners using a temporary sender."""
        if cls._queueList is not None and cls._shared_state is not None:
            try:
                sender = messageHandlerSender(cls._queueList, StateChange)
                sender.send(mode.name)
                print(f"\033[1;97m[ State Machine ] :\033[0m \033[1;92mINFO\033[0m - Starting in \033[1;94m{mode.name}\033[0m mode")
            except Exception as e:
                print(f"\033[1;97m[ State Machine ] :\033[0m \033[1;93mWARNING\033[0m - Failed to send starting mode: {e}")

    @classmethod
    def cleanup(cls):
        """Cleanup shared resources - automatically called on process exit."""
        if cls._manager is not None:
            try:
                cls._manager.shutdown()
            except Exception as e:
                print(f"StateMachine: Error during cleanup: {e}")
            finally:
                cls._manager = None
                cls._shared_state = None
                cls._process_lock = None
                cls._initialized = False
                cls._queueList = None

    @classmethod
    def is_initialized(cls):
        """Check if shared state is initialized."""
        return cls._initialized
