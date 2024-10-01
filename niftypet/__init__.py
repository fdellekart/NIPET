import os

from niftypet.timing import ReconMetadata

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

timer = ReconMetadata(os.getenv("GIT_COMMIT_SHORT_SHA"))
