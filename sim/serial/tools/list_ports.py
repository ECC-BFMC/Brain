"""Simulated serial-port discovery."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ListPortInfo:
    device: str
    description: str = "Brain NUCLEO Simulator"
    hwid: str = "SIMULATED"


def comports():
    return [ListPortInfo("/dev/ttyACM0")]
