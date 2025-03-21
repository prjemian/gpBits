"""
Custom Motor Classes.
"""

import logging

from ophyd import Component
from ophyd import EpicsMotor
from ophyd import EpicsSignal

logger = logging.getLogger(__name__)
logger.bsdev(__file__)


class EpicsMotor_SREV(EpicsMotor):
    """Provide access to motor steps/revolution configuration."""

    steps_per_revolution = Component(EpicsSignal, ".SREV", kind="config")
