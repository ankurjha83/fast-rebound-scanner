"""Append-only JSON/CSV persistence helpers."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Iterable


def write_immutable_json(path: str | Path, payload: dict) -> Path:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    descriptor=os.open(target,flags,0o600)
    with os.fdopen(descriptor,"w",encoding="utf-8") as handle: json.dump(payload,handle,indent=2,sort_keys=True,default=str)
    return target


def append_csv(path: str | Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    records=list(rows)
    if not records: return
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); exists=target.exists()
    with target.open("a",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=fieldnames,extrasaction="ignore")
        if not exists: writer.writeheader()
        writer.writerows(records)


def atomic_json(path: str | Path, payload: dict) -> None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); temporary=target.with_suffix(target.suffix+".tmp")
    temporary.write_text(json.dumps(payload,indent=2,sort_keys=True,default=str),encoding="utf-8"); os.replace(temporary,target)

