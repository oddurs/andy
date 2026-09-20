"""Import the `andy` executable as a module.

andy ships as a single file with no extension, because installing it is meant
to be one `curl`. That is worth keeping and it makes `import andy` impossible,
so the loader lives here once instead of in every test.

The `sys.modules` assignment is not optional: `@dataclass` looks its own class
up in `sys.modules[cls.__module__]` while deciding whether an annotation is
`KW_ONLY`, and without it the import fails inside dataclasses.py with an error
that says nothing about the real cause.
"""

import importlib.machinery
import importlib.util
import os
import sys

ANDY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "andy")


def load():
    if "andy" in sys.modules:
        return sys.modules["andy"]
    loader = importlib.machinery.SourceFileLoader("andy", ANDY)
    spec = importlib.util.spec_from_loader("andy", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["andy"] = module
    loader.exec_module(module)
    return module


andy = load()
