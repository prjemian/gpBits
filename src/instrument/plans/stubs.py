"""
Plan stubs.

.. autosummary::

    ~reload_devices
"""

from apsbits.utils.controls_setup import oregistry
from apsbits.utils.make_devices import make_devices


def reload_devices(pause: float = 1, clear: bool = True):
    """(plan) Clear registry before (re)loading devices."""

    if clear:
        # TODO: Clear oregistry.device_names from __main__ namespace
        oregistry.clear()
    yield from make_devices(pause=pause)
