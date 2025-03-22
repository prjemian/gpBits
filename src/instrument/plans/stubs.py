"""
Plan stubs.

.. autosummary::

    ~ad_peak_simulation
    ~ad_setup
    ~change_ad_simulated_image_parameters
    ~dither_ad_off
    ~dither_ad_on
    ~dither_ad_peak_position
    ~reload_devices
"""

import logging

import numpy as np
from apsbits.utils.controls_setup import oregistry
from apsbits.utils.make_devices import make_devices
from apstools.devices import AD_plugin_primed
from apstools.devices import AD_prime_plugin2
from apstools.devices import TransformRecord
from bluesky import plan_stubs as bps
from ophyd import DetectorBase
from ophyd.ophydobj import Kind

logger = logging.getLogger(__name__)
logger.bsdev(__file__)


def ad_setup(det):
    """Configure the area detector instance in our standard way."""
    if det is None:
        return  #  nothing to do, return silently

    # ad_config = iconfig.get("AREA_DETECTOR", {})  # FIXME
    ad_config = {}
    # The plugins do not block, the cam must wait for the plugins to finish.
    for nm in det.component_names:
        obj = getattr(det, nm)
        if "blocking_callbacks" in dir(obj):  # is it a plugin?
            obj.stage_sigs["blocking_callbacks"] = "No"
    det.cam.stage_sigs["wait_for_plugins"] = "Yes"

    if "hdf1" in det.component_names:
        # override default settings from ophyd
        # fmt: off
        yield from bps.mv(
            det.hdf1.create_directory, -5,
            det.hdf1.file_template, ad_config["HDF5_FILE_TEMPLATE"],
        )
        # fmt: on
        det.hdf1.kind = Kind.config | Kind.normal  # Ensure plugin's read is called.
        det.hdf1.stage_sigs["compression"] = "zlib"
        det.hdf1.stage_sigs.move_to_end("capture", last=True)

        if ad_config.get("ALLOW_PLUGIN_WARMUP", False):
            if not AD_plugin_primed(det.hdf1):
                AD_prime_plugin2(det.hdf1)


def change_ad_simulated_image_parameters(det):
    """
    Make the image be a "peak" (simulate a diffraction spot).

    Randomly-placed, random max, random noise.
    """
    cam = det.cam
    yield from bps.mv(cam.acquire, 0)  # stop the area detector
    yield from bps.sleep(0.25)  # brief pause for AD IOC to finish
    yield from bps.mv(cam.reset, 1)
    yield from bps.mv(cam.acquire_time, 0.01 * (1 - 0.5 * np.random.random()))

    # fmt: off
    yield from bps.mv(
        cam.sim_mode, 1,  # Peaks
        cam.gain, 100*(1 + np.random.random()),
        cam.offset, 10 * np.random.random(),
        cam.noise, 20 * np.random.random(),
    )
    yield from bps.mv(
        cam.peak_start.peak_start_x, round(200 + 500 * np.random.random()),
        cam.peak_start.peak_start_y, round(200 + 500 * np.random.random()),
    )
    yield from bps.mv(
        cam.peak_width.peak_width_x, round(10 + 100 * np.random.random()),
        cam.peak_width.peak_width_y, round(10 + 100 * np.random.random()),
        cam.peak_variation, 0.5 + 20 * np.random.random(),
    )
    # fmt: on


def dither_ad_off():
    """Disable the image peak dithering."""
    # select: 0 = off (Passive)
    dither_x = oregistry.find(name="user_calcs.calc9")
    dither_y = oregistry.find(name="user_calcs.calc10")
    # fmt: off
    yield from bps.mv(
        dither_x.scanning_rate, 0,
        dither_y.scanning_rate, 0,
    )
    # fmt: on


def dither_ad_on(scan_rate_setting=6):
    """Enable the image peak dithering."""
    # select: 6 = 1 Hz (1 second), 9 = 10 Hz (.1 second)
    dither_x = oregistry.find(name="user_calcs.calc9")
    dither_y = oregistry.find(name="user_calcs.calc10")
    # fmt: off
    yield from bps.mv(
        dither_x.scanning_rate, scan_rate_setting,
        dither_y.scanning_rate, scan_rate_setting,
    )
    # fmt: on


def dither_ad_peak_position(det, magnitude=40):
    """
    Dither the peak position using swait records.
    """
    peak = det.cam.peak_start
    formula = f"min(B,max(C,A+{magnitude}*(RNDM-0.5)))"

    dither_x = oregistry.find(name="user_calcs.calc9")
    dither_y = oregistry.find(name="user_calcs.calc10")
    # fmt: off
    yield from bps.mv(
        dither_x.description, "adsimdet peak X dither",
        dither_x.calculation, formula,
        dither_x.channels.A.input_pv, peak.peak_start_x.pvname,
        dither_x.channels.B.input_value, 900,  # upper limit
        dither_x.channels.C.input_value, 100,  # lower limit
        dither_x.output_link_pv, peak.peak_start_x.setpoint_pvname,
    )

    yield from bps.mv(
        dither_y.description, "adsimdet peak Y dither",
        dither_y.calculation, formula,
        dither_y.channels.A.input_pv, peak.peak_start_y.pvname,
        dither_y.channels.B.input_value, 900,  # upper limit
        dither_y.channels.C.input_value, 100,  # lower limit
        dither_y.output_link_pv, peak.peak_start_y.setpoint_pvname,
    )
    yield from dither_ad_on()
    # fmt: on


def ad_peak_simulation(
    det: DetectorBase,
    tr: TransformRecord,
    gain: float = None,
    offset: float = 10 * np.random.random(),
    noise: float = 20 * np.random.random(),
    x0: float = None,
    y0: float = None,
    pos_step: float = None,
    sigma_x: float = None,
    sigma_y: float = None,
    sigma_step: float = None,
    variation: float = None,
    balance: float = 0.45,
    border: float = 100,
) -> None:
    """
    Simulate area detector peak position, dither using a transform record.
    """
    cam = det.cam
    chan = tr.channels
    tr.reset()
    yield from bps.mv(cam.acquire, 0)  # stop the area detector
    yield from bps.sleep(0.25)  # brief pause for AD IOC to finish
    yield from bps.mv(cam.reset, 1)
    yield from bps.mv(cam.acquire_time, 0.02 * (1 - 0.5 * np.random.random()))

    def randn(scale=0.3):
        return 0.5 + scale * np.random.randn()

    def v_or_default(v, default):
        if v is None:
            v = default
        return v

    gain = v_or_default(gain, 50 + 150 * randn())
    max_pixel = min(
        det.cam.max_size.max_size_x.get(),
        det.cam.max_size.max_size_y.get(),
    )
    x0 = v_or_default(x0, det.cam.max_size.max_size_x.get() * randn())
    y0 = v_or_default(y0, det.cam.max_size.max_size_y.get() * randn())
    pos_step = v_or_default(pos_step, max_pixel / 40)
    sigma_x = v_or_default(sigma_x, 0.15 * max_pixel * randn())
    sigma_y = v_or_default(sigma_y, 0.15 * max_pixel * randn())
    sigma_step = v_or_default(sigma_step, max_pixel / 40)
    variation = v_or_default(variation, 0.5 + 20 * np.random.random())

    # fmt: off
    yield from bps.mv(
        cam.peak_start.peak_start_x, round(x0),
        cam.peak_start.peak_start_y, round(y0),
        cam.peak_width.peak_width_x, round(sigma_x),
        cam.peak_width.peak_width_y, round(sigma_y),
        cam.peak_variation, max(0.0, variation),

        tr.description, f"{det.prefix} peak dither",
    )
    yield from bps.mv(
        cam.sim_mode, "Peaks",
        # cam.sim_mode, 1,  # Peaks
        cam.gain, gain,
        cam.offset, offset,
        cam.noise, noise,
    )
    # fmt: on

    EXPRESSION = f"min(max(%s,%s),%s)+%s*(rndm-{balance:.3f})"

    # fmt: off
    yield from bps.mv(
        chan.A.comment, "position minimum",
        chan.A.current_value, border,

        chan.B.comment, "position maximum",
        chan.B.current_value, max_pixel - border - 1,

        chan.C.comment, "position step",
        chan.C.current_value, pos_step,

        chan.D.comment, "position X",
        chan.D.input_pv, f"{cam.peak_start.peak_start_x._read_pv.pvname} NPP NMS",
        chan.D.expression, EXPRESSION % ("d", "a", "b", "c"),
        chan.D.output_pv, f"{cam.peak_start.peak_start_x._write_pv.pvname} NPP NMS",

        chan.E.comment, "position Y",
        chan.E.input_pv, f"{cam.peak_start.peak_start_y._read_pv.pvname} NPP NMS",
        chan.E.expression, EXPRESSION % ("e", "a", "b", "c"),
        chan.E.output_pv, f"{cam.peak_start.peak_start_y._write_pv.pvname} NPP NMS",

        chan.F.comment, "width minimum",
        chan.F.current_value, max_pixel / 100,

        chan.G.comment, "width maximum",
        chan.G.current_value, max_pixel / 6,

        chan.H.comment, "width step",
        chan.H.current_value, sigma_step,

        chan.I.comment, "width X",
        chan.I.input_pv, f"{cam.peak_width.peak_width_x._read_pv.pvname} NPP NMS",
        chan.I.expression, EXPRESSION % ("i", "f", "g", "h"),
        chan.I.output_pv, f"{cam.peak_width.peak_width_x._write_pv.pvname} NPP NMS",

        chan.J.comment, "width X",
        chan.J.input_pv, f"{cam.peak_width.peak_width_y._read_pv.pvname} NPP NMS",
        chan.J.expression, EXPRESSION % ("j", "f", "g", "h"),
        chan.J.output_pv, f"{cam.peak_width.peak_width_y._write_pv.pvname} NPP NMS",

        tr.calc_option, "Always",
        tr.scanning_rate, "1 second",
    )
    # fmt: on


def reload_devices(pause: float = 1, clear: bool = True):
    """(plan) Clear registry before (re)loading devices."""

    if clear:
        # TODO: Clear oregistry.device_names from __main__ namespace
        oregistry.clear()
    yield from make_devices(pause=pause)
