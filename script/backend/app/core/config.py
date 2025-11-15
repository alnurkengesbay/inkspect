from __future__ import annotations

import os
from pathlib import Path

from typing import Optional

from pydantic import BaseModel


try:
    _project_root = Path(__file__).resolve().parents[4]
except IndexError:
    _project_root = Path(__file__).resolve().parent
_poppler_default: Optional[Path] = None
_poppler_root = _project_root / "poppler"
if _poppler_root.exists():
    for candidate in sorted(_poppler_root.glob("poppler-*/Library/bin")):
        if candidate.exists():
            _poppler_default = candidate.resolve()
            break

_poppler_env = os.getenv("POPPLER_PATH")

_weights_env = os.getenv("DOCSCAN_WEIGHTS_PATH")
_weights_candidates = []
if _weights_env:
    _weights_candidates.append(Path(_weights_env))

_weights_candidates.extend(
    [
        _project_root / "artifacts" / "yolov8_sign_stamp_qr_best.pt",
        _project_root / "runs_custom" / "sign_stamp_qr" / "weights" / "best.pt",
        Path.cwd() / "runs_custom" / "sign_stamp_qr" / "weights" / "best.pt",
    ]
)

_weights_default: Optional[Path] = None
for candidate in _weights_candidates:
    if candidate.exists():
        _weights_default = candidate.resolve()
        break


class Settings(BaseModel):
    project_name: str = "DocScan Pipeline"
    media_root: Path = Path(os.getenv("DOCSCAN_MEDIA_ROOT", Path("media"))).resolve()
    weights_path: Path = (_weights_default or Path("artifacts") / "yolov8_sign_stamp_qr_best.pt").resolve()
    enable_heatmap: bool = True
    heatmap_kernel: int = 51
    heatmap_sigma_scale: float = 0.2
    low_conf_threshold: float = 0.5
    high_conf_threshold: float = 0.8
    poppler_path: Optional[Path] = (
        Path(_poppler_env).resolve()
        if _poppler_env
        else _poppler_default
    )

    class Config:
        arbitrary_types_allowed = True


settings = Settings()
settings.media_root.mkdir(parents=True, exist_ok=True)
(settings.media_root / "jobs").mkdir(exist_ok=True)
(settings.media_root / "tmp").mkdir(exist_ok=True)
