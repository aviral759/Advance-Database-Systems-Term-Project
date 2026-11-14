import os
import tempfile

# Must run before any `app` import: settings are read at import time.
os.environ["HPS_DATA_DIR"] = tempfile.mkdtemp(prefix="hps-test-")
os.environ["HPS_FAKE_EMBEDDER"] = "1"
os.environ["HPS_READ_ONLY"] = "0"
os.environ.pop("HPS_DEMO_TOKEN", None)