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

"""Zero-copy transport for camera frames between processes.

The camera thread publishes each raw lores frame into a small shared-memory
ring buffer instead of (only) JPEG/base64-encoding it through the gateway
queues. Any other process (lane detection, sign detection, ...) attaches a
reader by name and always gets the newest fully-written frame, with no
serialization on either side.

Writer side (owns the segment, one per camera):

    writer = SharedFrameWriter(history=1)
    writer.write(frame)          # frame: np.uint8 array of LORES_FRAME_SHAPE
    writer.close()               # unlinks the segment

Reader side (any process, any number of readers). Consumers driven by the
gateway notifications use NotifiedFrameReader, which handles attaching and
returns each frame at most once:

    frameReader = NotifiedFrameReader()
    result = frameReader.read(notification)   # the gateway message payload
    if result is not None:
        frame, timestamp, seq = result

Polling consumers can attach a SharedFrameReader directly:

    reader = SharedFrameReader()
    result = reader.readLatest()
    if result is not None:
        frame, timestamp, seq = result   # seq increases by 1 per frame
    oldResult = reader.readBack(1)        # one frame before the latest, if still resident
    reader.close()

Consistency: each slot carries a sequence number that is zeroed before the
frame bytes are written and restored afterwards, and readers re-check it after
copying. A torn (mid-write) read is therefore detected and retried on the
next-newest slot. Public buffer sizing is expressed as history: history=N lets
readers ask for readBack(0)..readBack(N). Internally this allocates N + 2 slots:
latest + N past frames + one spare slot so the oldest requested frame is not
normally the slot being overwritten next.
"""

import struct
import time
from multiprocessing import shared_memory

import numpy as np

try:
    from multiprocessing import resource_tracker
except ImportError:  # pragma: no cover
    resource_tracker = None

# Segments published by threadCamera (each only while someone subscribes to the
# corresponding gateway message): the lores stream after YUV->BGR conversion,
# and the full-resolution main stream.
CAMERA_SHM_NAME = "bfmc_camera_lores"
LORES_FRAME_SHAPE = (270, 512, 3)
CAMERA_MAIN_SHM_NAME = "bfmc_camera_main"
MAIN_FRAME_SHAPE = (1080, 2048, 3)

_U64 = struct.Struct("<Q")       # global header offset 0: latest published sequence
_U32 = struct.Struct("<I")       # global header offset 8: raw ring slot count
_SLOT_HEADER = struct.Struct("<Qd")  # per slot: sequence number, capture timestamp
_GLOBAL_HEADER_SIZE = 16         # padded so slots stay 8-byte aligned
_SLOT_HEADER_SIZE = 16
_SLOTS_OFFSET = 8


def _attachUntracked(name):
    """Attach to an existing segment without registering it with this process's
    resource tracker: on Python < 3.13 the tracker unlinks the segment when the
    attaching process exits, which would kill it for the writer and all other
    readers. Only the writer may unlink."""
    try:
        return shared_memory.SharedMemory(name=name, track=False)
    except TypeError:  # Python < 3.13: no `track` parameter
        shm = shared_memory.SharedMemory(name=name)
        if resource_tracker is not None:
            try:
                resource_tracker.unregister(shm._name, "shared_memory")
            except Exception:
                pass
        return shm


class _FrameBufferBase:
    def __init__(self, shape, dtype, slots):
        self._shape = tuple(shape)
        self._dtype = np.dtype(dtype)
        self._slots = int(slots)
        if self._slots < 2:
            raise ValueError("frame buffer needs at least 2 raw slots")
        self._history = self._slots - 2
        frameNbytes = int(np.prod(self._shape)) * self._dtype.itemsize
        # round the frame block up to a multiple of 8 to keep slot headers aligned
        self._stride = _SLOT_HEADER_SIZE + -(-frameNbytes // 8) * 8
        self._size = _GLOBAL_HEADER_SIZE + self._slots * self._stride
        self._shm = None
        self._frames = None

    def _slotOffset(self, slot):
        return _GLOBAL_HEADER_SIZE + slot * self._stride

    def _mapSlots(self):
        self._frames = [
            np.ndarray(
                self._shape,
                dtype=self._dtype,
                buffer=self._shm.buf,
                offset=self._slotOffset(i) + _SLOT_HEADER_SIZE,
            )
            for i in range(self._slots)
        ]

    def close(self):
        # drop the ndarray views first: SharedMemory.close() refuses to close
        # while exported buffers are still alive
        self._frames = None
        if self._shm is not None:
            self._shm.close()
            self._shm = None


class SharedFrameWriter(_FrameBufferBase):
    """Single-writer frame ring buffer. Creates (and on close unlinks) the segment."""

    def __init__(
        self,
        name=CAMERA_SHM_NAME,
        shape=LORES_FRAME_SHAPE,
        dtype=np.uint8,
        history=1,
    ):
        history = int(history)
        if history < 0:
            raise ValueError("history must be >= 0")
        super().__init__(shape, dtype, history + 2)
        # remove a stale segment left behind by a previous crashed run
        try:
            stale = shared_memory.SharedMemory(name=name)
            stale.close()
            stale.unlink()
        except FileNotFoundError:
            pass

        try:
            self._shm = shared_memory.SharedMemory(name=name, create=True, size=self._size)
        except FileExistsError:
            # On Windows a segment remains named while any reader still has it
            # open, and unlink() cannot remove it eagerly. Reuse a compatible
            # leftover segment instead of failing during stream restart/shutdown.
            self._shm = shared_memory.SharedMemory(name=name)
            if self._shm.size < self._size:
                size = self._shm.size
                self.close()
                raise ValueError(
                    f"segment '{name}' is {size} bytes, expected >= {self._size}; "
                    "stale writer geometry does not match"
                )
        _U64.pack_into(self._shm.buf, 0, 0)
        _U32.pack_into(self._shm.buf, _SLOTS_OFFSET, self._slots)
        self._mapSlots()
        self._seq = 0

    def write(self, frame, timestamp=None):
        """Publish one frame, overwriting the oldest slot. Returns the frame's
        sequence number (1-based, increases by 1 per write)."""
        frame = np.asarray(frame)
        if frame.shape != self._shape or frame.dtype != self._dtype:
            raise ValueError(
                f"expected {self._shape} {self._dtype} frame, got {frame.shape} {frame.dtype}"
            )
        if timestamp is None:
            timestamp = time.time()

        seq = self._seq + 1
        slot = seq % self._slots
        offset = self._slotOffset(slot)
        buf = self._shm.buf

        # zero the slot sequence first so a reader copying this slot mid-write
        # sees a mismatch and retries instead of returning a torn frame
        _U64.pack_into(buf, offset, 0)
        self._frames[slot][:] = frame
        _SLOT_HEADER.pack_into(buf, offset, seq, timestamp)
        _U64.pack_into(buf, 0, seq)
        self._seq = seq
        return seq

    def close(self):
        shm = self._shm
        super().close()
        if shm is not None:
            try:
                shm.unlink()
            except FileNotFoundError:
                pass


class SharedFrameReader(_FrameBufferBase):
    """Attaches to an existing frame ring buffer. Must match the writer's frame geometry."""

    def __init__(
        self,
        name=CAMERA_SHM_NAME,
        shape=LORES_FRAME_SHAPE,
        dtype=np.uint8,
        history=None,
    ):
        shm = _attachUntracked(name)
        discoveredSlots = _U32.unpack_from(shm.buf, _SLOTS_OFFSET)[0]
        if discoveredSlots == 0:
            expectedHistory = 1 if history is None else int(history)
            discoveredSlots = expectedHistory + 2
        elif history is not None and int(history) + 2 != discoveredSlots:
            shm.close()
            raise ValueError(
                f"segment '{name}' has history {discoveredSlots - 2}, reader expected {history}"
            )

        super().__init__(shape, dtype, discoveredSlots)
        self._shm = shm
        if self._shm.size < self._size:
            size = self._shm.size
            self.close()
            raise ValueError(
                f"segment '{name}' is {size} bytes, expected >= {self._size}; "
                "reader geometry does not match the writer"
            )
        self._mapSlots()

    @property
    def history(self):
        """Maximum n accepted by readBack(n): latest is 0, oldest past frame is history."""
        return self._history

    def _readSeqOnce(self, seq):
        slot = seq % self._slots
        offset = self._slotOffset(slot)
        buf = self._shm.buf
        actualSeq, timestamp = _SLOT_HEADER.unpack_from(buf, offset)
        if actualSeq != seq:
            return None
        frame = self._frames[slot].copy()
        if _U64.unpack_from(buf, offset)[0] == seq:
            return frame, timestamp, seq
        return None

    def readSeq(self, seq):
        """Return a specific absolute sequence if it is still within history.

        Returns None when the sequence was never written, was overwritten, is
        outside the public history window, or is being overwritten right now.
        """
        seq = int(seq)
        if seq <= 0:
            return None
        latest = _U64.unpack_from(self._shm.buf, 0)[0]
        if latest == 0 or seq > latest or latest - seq > self._history:
            return None
        return self._readSeqOnce(seq)

    def readBack(self, n=0):
        """Return the frame n steps behind latest.

        n=0 is the latest frame. n=history is the oldest public past frame.
        Returns None when n is outside that range or the target frame is not
        available safely.
        """
        n = int(n)
        if n < 0 or n > self._history:
            return None
        latest = _U64.unpack_from(self._shm.buf, 0)[0]
        if latest == 0 or latest <= n:
            return None
        return self.readSeq(latest - n)

    def readLatest(self):
        """Return (frame_copy, timestamp, seq) for the newest published frame,
        or None if nothing has been published yet."""
        for _ in range(self._slots + 1):
            result = self.readBack(0)
            if result is not None:
                return result
        return None


class NotifiedFrameReader:
    """Reads frames announced by the camera's gateway notifications
    ({"seq", "timestamp", "shm", "shape"}). Attaches to each segment on first
    use and returns every frame at most once, so consumers just do:

        result = frameReader.read(notification)
        if result is not None:
            frame, timestamp, seq = result
    """

    def __init__(self):
        self._readers = {}
        self._lastSeq = {}

    def read(self, notification):
        """Returns (frame_copy, timestamp, seq) for the newest frame in the
        notification's segment, or None while the segment does not exist yet
        or its newest frame was already returned."""
        shmName = notification["shm"]
        reader = self._readers.get(shmName)
        if reader is None:
            try:
                reader = SharedFrameReader(name=shmName, shape=tuple(notification["shape"]))
            except FileNotFoundError:
                return None  # the writer's segment is not up yet; retry on the next notification
            self._readers[shmName] = reader

        result = reader.readLatest()
        if result is None or result[2] == self._lastSeq.get(shmName):
            return None
        self._lastSeq[shmName] = result[2]
        return result

    def close(self):
        for reader in self._readers.values():
            reader.close()
        self._readers = {}
        self._lastSeq = {}
