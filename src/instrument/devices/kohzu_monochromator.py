"""
Simulated Kohzu Double-Crystal Monochromator (DCM)
"""

import logging

from apstools.devices import KohzuSeqCtl_Monochromator
from bluesky import plan_stubs as bps
from ophyd import EpicsMotor
from ophyd import FormattedComponent as FCpt

logger = logging.getLogger(__name__)
logger.bsdev(__file__)


class KohzuDCM(KohzuSeqCtl_Monochromator):
    """Kohzu Double-Crystal Monochromator."""

    m_theta = FCpt(EpicsMotor, "{prefix}{_m_th}", kind="normal", labels=["motor"])
    m_y = FCpt(EpicsMotor, "{prefix}{_m_y}", kind="normal", labels=["motor"])
    m_z = FCpt(EpicsMotor, "{prefix}{_m_z}", kind="normal", labels=["motor"])

    def __init__(self, prefix="", *, m_th="", m_y="", m_z="", **kwargs):  # noqa D107
        self._m_th = m_th
        self._m_y = m_y
        self._m_z = m_z
        super().__init__(prefix, **kwargs)

    def into_control_range(self, p_theta=2, p_y=-15, p_z=90):
        """
        (plan stub) Move the Kohzu motors into range so the energy controls will work.

        Written as a bluesky plan so that all motors can be moved
        simultaneously.  Return early if the motors are already in range.

        USAGE::

            RE(dcm.into_control_range())
        """
        args = []
        if self.m_theta.position < p_theta:
            args += [self.m_theta, p_theta]
        if self.m_y.position > p_y:
            args += [self.m_y, p_y]
        if self.m_z.position < p_z:
            args += [self.m_z, p_z]
        if len(args) == 0:
            # all motors in range, no work to do.
            return
        yield from bps.mv(*args)
        yield from bps.sleep(1)  # allow IOC to react
        yield from bps.mv(self.operator_acknowledge, 1, self.mode, "Auto")

    def stop(self):
        """Tell the motors to stop."""
        self.m_theta.stop()
        self.m_y.stop()
        self.m_z.stop()
