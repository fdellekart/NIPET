import os

from niftypet.timing import ReconTimer

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

timer = ReconTimer(os.getenv("GIT_COMMIT_SHORT_SHA"))
