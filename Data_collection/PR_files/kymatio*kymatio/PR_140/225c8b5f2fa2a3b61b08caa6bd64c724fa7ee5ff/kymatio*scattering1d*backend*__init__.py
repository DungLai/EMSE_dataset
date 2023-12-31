# Backend decision logic at import
# We will have backend fixed at import until we come up with something more
# elegant.

# Here's how it is decided upon:

# 1. Is there an environment variable SCATTERING_BACKEND_1D?
# 2. Is there an environment variable SCATTERING_BACKEND?
# 3. Is there a config file? If so, go and find the backend entry
# 4. Set the backend to DEFAULT_BACKEND

import os
import configparser
import appdirs

DEFAULT_BACKEND = "torch"

# find config file
config_file = os.path.join(appdirs.user_config_dir("scattering"), "scattering.cfg")
cp = configparser.ConfigParser()

if os.path.exists(config_file):
    cp.read(config_file)
    BACKEND = cp.get('general', 'backend_1d',
                     fallback=cp.get('general', 'backend', fallback=None))
    if BACKEND is None:
        BACKEND = DEFAULT_BACKEND
        if 'general' not in cp.sections():
            cp.add_section('general')
        cp['general']['backend_1d'] = BACKEND
        try:
            with open(config_file, "w") as f:
                cp.write(f)
        except:
            pass
else:
    BACKEND = DEFAULT_BACKEND
    # try to write config file
    try:
        dirname = os.path.dirname(config_file)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        cp.add_section('general')
        cp['general']['backend_1d'] = BACKEND
        with open(config_file, "w") as f:
            cp.write(f)
    except:
        pass

# general env:
BACKEND = os.environ.get("SCATTERING_BACKEND", BACKEND)

# 1d specific env:
BACKEND = os.environ.get("SCATTERING_BACKEND_1D", BACKEND)

if BACKEND == 'torch':
    from .backend_torch import *
elif BACKEND == 'skcuda':
    from .backend_skcuda import *
else:
    # For now, raise and error
    raise ValueError("Backend {} unknown".format(BACKEND))
