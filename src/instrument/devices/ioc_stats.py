"""
IOC statistics: synApps iocStats
"""

import logging

from ophyd import Component
from ophyd import Device
from ophyd import EpicsSignalRO

logger = logging.getLogger(__name__)
logger.bsdev(__file__)


class IocInfoDevice(Device):
    """IOC information"""

    iso8601 = Component(EpicsSignalRO, "iso8601")
    uptime = Component(EpicsSignalRO, "UPTIME")
