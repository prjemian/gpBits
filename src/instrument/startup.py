"""
Start Bluesky Data Acquisition sessions of all kinds.

Includes:

* Python script
* IPython console
* Jupyter notebook
* Bluesky queueserver
"""

import logging

import gi  # noqa
import hklpy2
from apsbits.core.best_effort_init import init_bec_peaks
from apsbits.core.catalog_init import init_catalog
from apsbits.core.run_engine_init import init_RE
from apsbits.utils.aps_functions import aps_dm_setup
from apsbits.utils.baseline_setup import setup_baseline_stream
from apsbits.utils.config_loaders import get_config
from apsbits.utils.controls_setup import oregistry
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver
from hklpy2.backends.hkl_soleil import libhkl

logger = logging.getLogger(__name__)
logger.bsdev(__file__)

# Do not track any ophyd objects loaded by imports above.
oregistry.clear()

# Get the configuration
iconfig = get_config()

# Configure the session with callbacks, devices, and plans.
aps_dm_setup(iconfig.get("DM_SETUP_FILE"))

if iconfig.get("USE_BLUESKY_MAGICS", False):
    register_bluesky_magics()

# Initialize core components
bec, peaks = init_bec_peaks(iconfig)
cat = init_catalog(iconfig)
RE, sd = init_RE(iconfig, bec_instance=bec, cat_instance=cat)
RE.md["versions"]["hklpy2"] = hklpy2.__version__
RE.md["versions"]["hkl_soleil"] = libhkl.VERSION

# Import optional components based on configuration
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from .callbacks.nexus_data_file_writer import nxwriter_init

    nxwriter = nxwriter_init(RE)

if iconfig.get("SPEC_DATA_FILES", {}).get("ENABLE", False):
    from .callbacks.spec_data_file_writer import init_specwriter_with_RE
    from .callbacks.spec_data_file_writer import newSpecFile  # noqa: F401
    from .callbacks.spec_data_file_writer import spec_comment  # noqa: F401
    from .callbacks.spec_data_file_writer import specwriter  # noqa: F401

    init_specwriter_with_RE(RE)

# Import all plans
from .plans import *  # noqa

# These imports must come after the above setup.
if running_in_queueserver():
    ### To make all the standard plans available in QS, import by '*', otherwise import
    ### plan by plan.
    from apstools.plans import lineup2  # noqa: F401
    from bluesky.plans import *  # noqa: F403

else:
    # Import bluesky plans and stubs with prefixes set by common conventions.
    # The apstools plans and utils are imported by '*'.
    from apstools.plans import *  # noqa: F403
    from apstools.utils import *  # noqa: F403
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401


def on_startup():
    """Instead of calling RE() sequentially."""
    from apsbits.core.instrument_init import make_devices

    from instrument.plans.setup_gp import setup_devices

    yield from make_devices(file="devices.yml", clear=False)
    yield from make_devices(file="gp_devices.yml", clear=False)
    yield from make_devices(file="ad_devices.yml", clear=False)
    yield from setup_devices()
    setup_baseline_stream(sd, oregistry)


# TODO: https://github.com/BCDA-APS/BITS/issues/92
# def creator_plan(name, geometry="E4CV", solver="hkl_soleil", **kwargs):
#     from hklpy2 import creator

#     yield from bps.null()
#     diffractometer = creator(name=name, geometry=geometry, solver=solver, **kwargs)
#     setattr(sys.modules["__main__"], name, diffractometer)


# def count_device(dets: list[str]):
#     """Run the bp.count plan on items found in oregistry."""
#     from bluesky import plans as bp

#     detectors = [oregistry[det] for det in dets]
#     yield from bp.count(detectors)


RE.md["versions"]["gi"] = gi.__version__
RE(on_startup())
