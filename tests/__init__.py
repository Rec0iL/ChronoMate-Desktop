"""Tests package.

Every test run gets its own throwaway settings and session folders, so running the tests never
touches the user's real ~/.config/ChronoMate/settings.json or saved sessions.
"""

import atexit
import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="chronomate-tests-")
os.environ["CHRONOMATE_CONFIG_DIR"] = os.path.join(_TMP, "config")
os.environ["CHRONOMATE_DATA_DIR"] = os.path.join(_TMP, "data")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
atexit.register(shutil.rmtree, _TMP, True)
