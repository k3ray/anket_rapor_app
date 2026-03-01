"""Bootstrap package for `python -m app`."""

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]
_src_pkg = Path(__file__).resolve().parent.parent / "src" / "app"
if _src_pkg.exists():
    __path__.append(str(_src_pkg))
