"""GPT Sol: CPU-only full archive verification; write aggregates, never member IDs.

Run with Python -I from scripts/, passing all paths explicitly. No extraction,
network, model imports or dataset records are written. Progress is a JSON report.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import zipfile


def verify(archive: Path, output: Path, expected_bytes: int, expected_sha256=None):
    started = time.monotonic()
    before = archive.stat()
    report = {"attribution": "GPT Sol; actual CPU archive reads, no inference",
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "expected_bytes": expected_bytes, "bytes": before.st_size,
              "size_matches": before.st_size == expected_bytes, "stage": "sha256"}

    def save():
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(".tmp")
        temp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        temp.replace(output)

    save()
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    report.update(sha256=digest.hexdigest(), expected_sha256=expected_sha256,
                  sha256_matches=(digest.hexdigest() == expected_sha256) if expected_sha256 else None,
                  checksum_status="compared to supplied reference" if expected_sha256 else
                  "first local reference; not a publisher-authenticated checksum", stage="crc")
    save()
    extensions = Counter()
    checked = failed = directories = uncompressed = images = annotation_files = 0
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        for info in infos:
            if info.is_dir():
                directories += 1
            else:
                suffix = Path(info.filename).suffix.lower()
                extensions[suffix] += 1
                images += suffix in {".png", ".jpg", ".jpeg", ".bmp"}
                annotation_files += suffix in {".json", ".xml", ".csv", ".txt", ".mat"}
            try:
                # Reading to EOF checks decompression and the stored CRC for EVERY member.
                with z.open(info) as member:
                    for block in iter(lambda: member.read(1024 * 1024), b""):
                        uncompressed += len(block)
                checked += 1
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, OSError):
                failed += 1
            if (checked + failed) % 2000 == 0:
                report.update(crc_members_checked=checked, crc_failed_members=failed)
                save()
    after = archive.stat()
    report.update(stage="complete", member_count=len(infos), directory_count=directories,
                  file_count=len(infos) - directories, image_count=images,
                  annotation_file_count=annotation_files, file_extensions=dict(sorted(extensions.items())),
                  crc_members_checked=checked, crc_failed_members=failed,
                  uncompressed_bytes_read=uncompressed,
                  unchanged_during_verification=(before.st_size, before.st_mtime_ns) ==
                  (after.st_size, after.st_mtime_ns),
                  completed_utc=datetime.now(timezone.utc).isoformat())
    report["passed"] = (report["size_matches"] and failed == 0 and checked == len(infos)
                        and report["unchanged_during_verification"]
                        and report["sha256_matches"] is not False)
    save()
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--expected-bytes", type=int, default=57_481_286_834)
    ap.add_argument("--expected-sha256")
    args = ap.parse_args()
    result = verify(args.archive, args.output, args.expected_bytes, args.expected_sha256)
    raise SystemExit(0 if result["passed"] else 1)
