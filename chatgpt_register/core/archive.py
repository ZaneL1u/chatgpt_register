"""批次输出归档 — 为每次 run_batch 创建独立时间戳目录。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def create_archive_dir(base: str = "output") -> Path:
    """创建 output/YYYYMMDD_HHMM/ 归档目录。

    同一分钟内多次调用时追加 _N 后缀（如 20260315_1430_2）。
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    candidate = Path(base) / stamp
    if not candidate.exists():
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    n = 2
    while True:
        candidate = Path(base) / f"{stamp}_{n}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        n += 1


def prepare_archive_paths(
    archive_dir: Path,
    *,
    output_file: str,
    ak_file: str,
    rk_file: str,
    token_json_dir: str,
    log_file: str,
) -> dict[str, str]:
    """将配置中的文件名重定向到归档目录。

    仅取 basename，忽略原路径前缀。
    log_file 为空时默认使用 batch.log。
    """
    return {
        "output_file": str(archive_dir / Path(output_file).name),
        "ak_file": str(archive_dir / Path(ak_file).name),
        "rk_file": str(archive_dir / Path(rk_file).name),
        "token_json_dir": str(archive_dir / Path(token_json_dir).name),
        "log_file": str(archive_dir / (Path(log_file).name if log_file else "batch.log")),
    }
