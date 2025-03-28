"""

Simulated temperature controller.

Add override feature: replace ScalerCH channel counts with computed value.

EXAMPLE::

    # 'noisy' is an EpicsSignalRO known to oregistry
    # It uses an swait record that updates when 'm1' moves.
    scaler1.select_channels(["I0"])
    scaler1.channels.chan02.override_signal_name.put("noisy")

    # demo:
    RE(bp.rel_scan([scaler1], m1, -1, 1, 37))

    # fails:
    RE(lineup2([scaler1], m1, -1, 1, 11))
    # succeeds:
    I0 = scaler1.channels.chan02.s
    RE(lineup2([I0, scaler1], m1, -1, 1, 11))
"""

from collections import OrderedDict

import ophyd
import ophyd.scaler
from apsbits.utils.controls_setup import oregistry
from ophyd import DynamicDeviceComponent as DDCpt
from ophyd import FormattedComponent as FCpt

MAX_CHANNELS = 32


class SubstituteScalerChannelCounts(ophyd.EpicsSignalRO):
    """Get this signal's value from another signal."""

    override_signal_name = None

    def get(self, **kwargs):
        """."""
        signal = oregistry.find(
            name=self.parent.override_signal_name.get(),
            allow_none=True,
        )
        return (signal or super()).get()


class ScalerChannel(ophyd.scaler.ScalerChannel):
    """Override this channel's 's' component."""

    override_signal_name = ophyd.Component(
        ophyd.Signal,
        value="default: scaler channel's 'counts' value",
        kind=ophyd.Kind.config,
    )
    s = FCpt(
        SubstituteScalerChannelCounts,
        "{self.prefix}.S{self._ch_num}",
        kind=ophyd.Kind.hinted,
        auto_monitor=False,
    )


def _sc_chans(attr_fix, id_range):
    """."""
    defn = OrderedDict()
    for k in id_range:
        chan_class = ScalerChannel
        defn["{}{:02d}".format(attr_fix, k)] = (
            chan_class,
            "",
            {"ch_num": k, "kind": ophyd.Kind.normal},
        )
    return defn


class ScalerCH(ophyd.scaler.ScalerCH):
    """Allow override of any channel's value."""

    # use our custom channel support class
    channels = DDCpt(_sc_chans("chan", range(1, MAX_CHANNELS + 1)))
