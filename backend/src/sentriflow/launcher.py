"""R4 launcher entry point delegates to the integrated proxy/API lifecycle."""

from sentriflow.proxy.runner import acquire_session as acquire_session
from sentriflow.proxy.runner import run as run
