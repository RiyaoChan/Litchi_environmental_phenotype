from __future__ import annotations

import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from download_orchard_weather_exact import (
    DAILY_MAP,
    HOURLY_MAP,
    build_grid_distinction,
    build_overlap_metrics,
    load_config,
    parse_resolution,
    request_json,
    sha256_bytes,
    validate_daily,
    validate_hourly,
    write_report,
)


def date_chunks(start_date: str, end_date: str) -> list[tuple[str, str]]:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    chunks: list[tuple[str, str]] = []
    for year in range(start.year, end.year + 1):
        left = max(start, pd.Timestamp(year=year, month=1, day=1))
        right = min(end, pd.Timestamp(year=year, month=12, day=31))
        if left <= right:
            chunks.append((left.strftime("%Y-%m-%d"), right.strftime("%Y-%m-%d")))
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description="Download exact-orchard ERA5 in annual chunks")
    parser.add_argument("--config", default="configs/orchard_weather_exact.yaml")
    parser.add_argument("--station", default="data/processed/weather_daily.csv")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    source = cfg["source"]
    outputs = cfg["outputs"]
    raw_dir = Path(outputs["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    for key in [
        "daily_csv",
        "hourly_csv_gz",
        "metadata_json",
        "variable_dictionary_csv",
        "overlap_metrics_csv",
        "grid_distinction_csv",
        "report_md",
    ]:
        Path(outputs[key]).parent.mkdir(parents=True, exist_ok=True)

    downloaded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    chunks = date_chunks(source["start_date"], source["end_date"])
    daily_frames: list[pd.DataFrame] = []
    hourly_frames: list[pd.DataFrame] = []
    dictionary_rows: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {
        "downloaded_at_utc": downloaded_at,
        "source": source,
        "request_strategy": "one combined daily+hourly request per orchard per calendar-year chunk",
        "date_chunks": [{"start": left, "end": right} for left, right in chunks],
        "points": {},
    }

    for point_key, point in cfg["points"].items():
        point_daily: list[pd.DataFrame] = []
        point_hourly: list[pd.DataFrame] = []
        raw_chunks: list[dict[str, Any]] = []
        returned_grids: list[dict[str, Any]] = []
        for chunk_start, chunk_end in chunks:
            params = {
                "latitude": point["latitude"],
                "longitude": point["longitude"],
                "start_date": chunk_start,
                "end_date": chunk_end,
                "daily": ",".join(source["daily_variables"]),
                "hourly": ",".join(source["hourly_variables"]),
                "timezone": source["timezone"],
                "models": source["model"],
                "cell_selection": source.get("cell_selection", "land"),
                "wind_speed_unit": "ms",
                "precipitation_unit": "mm",
                "temperature_unit": "celsius",
            }
            print(json.dumps({"stage": "request", "point": point_key, "start": chunk_start, "end": chunk_end}))
            payload = request_json(source["api_base"], params)
            raw_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            raw_path = raw_dir / f"{point_key}_{chunk_start}_{chunk_end}.json.gz"
            with gzip.open(raw_path, "wb", compresslevel=9) as fh:
                fh.write(raw_bytes)

            daily, daily_dict = parse_resolution(payload, "daily", DAILY_MAP, point_key, point, source)
            hourly, hourly_dict = parse_resolution(payload, "hourly", HOURLY_MAP, point_key, point, source)
            point_daily.append(daily)
            point_hourly.append(hourly)
            dictionary_rows.extend(daily_dict + hourly_dict)
            raw_chunks.append(
                {
                    "start_date": chunk_start,
                    "end_date": chunk_end,
                    "raw_json_gz_sha256": sha256_bytes(raw_path.read_bytes()),
                    "raw_payload_sha256": sha256_bytes(raw_bytes),
                    "n_daily": len(daily),
                    "n_hourly": len(hourly),
                }
            )
            returned_grids.append(
                {
                    "start_date": chunk_start,
                    "end_date": chunk_end,
                    "latitude": payload.get("latitude"),
                    "longitude": payload.get("longitude"),
                    "elevation_m": payload.get("elevation"),
                }
            )

        orchard_daily = pd.concat(point_daily, ignore_index=True)
        orchard_hourly = pd.concat(point_hourly, ignore_index=True)
        daily_frames.append(orchard_daily)
        hourly_frames.append(orchard_hourly)
        unique_grids = {
            (row["latitude"], row["longitude"], row["elevation_m"])
            for row in returned_grids
        }
        if len(unique_grids) != 1:
            raise ValueError(f"Returned ERA5 grid changed across chunks for {point_key}: {unique_grids}")
        grid_latitude, grid_longitude, elevation_m = next(iter(unique_grids))
        metadata["points"][point_key] = {
            "orchard_id": point["orchard_id"],
            "point_id": point["point_id"],
            "latitude_dms": point["latitude_dms"],
            "longitude_dms": point["longitude_dms"],
            "requested_latitude": point["latitude"],
            "requested_longitude": point["longitude"],
            "returned_grid_latitude": grid_latitude,
            "returned_grid_longitude": grid_longitude,
            "elevation_m": elevation_m,
            "coordinate_basis": point["coordinate_basis"],
            "coordinate_source_files": point["coordinate_source_files"],
            "coordinate_source_sha256": point["coordinate_source_sha256"],
            "raw_chunks": raw_chunks,
            "n_daily": len(orchard_daily),
            "n_hourly": len(orchard_hourly),
            "daily_units": payload.get("daily_units", {}),
            "hourly_units": payload.get("hourly_units", {}),
        }

    daily_all = pd.concat(daily_frames, ignore_index=True).sort_values(["orchard_id", "date"], kind="stable")
    hourly_all = pd.concat(hourly_frames, ignore_index=True).sort_values(["orchard_id", "time"], kind="stable")
    validate_daily(daily_all, source["start_date"], source["end_date"])
    validate_hourly(hourly_all, source["start_date"], source["end_date"])

    overlap = build_overlap_metrics(daily_all, Path(args.station), cfg)
    distinction = build_grid_distinction(daily_all)
    variable_dictionary = (
        pd.DataFrame(dictionary_rows)
        .drop_duplicates()
        .sort_values(["resolution", "source_variable"])
    )

    daily_write = daily_all.copy()
    hourly_write = hourly_all.copy()
    daily_write["date"] = daily_write["date"].dt.strftime("%Y-%m-%d")
    hourly_write["time"] = hourly_write["time"].dt.strftime("%Y-%m-%dT%H:%M")
    daily_write.to_csv(outputs["daily_csv"], index=False, encoding="utf-8-sig")
    hourly_write.to_csv(outputs["hourly_csv_gz"], index=False, encoding="utf-8-sig", compression="gzip")
    variable_dictionary.to_csv(outputs["variable_dictionary_csv"], index=False, encoding="utf-8-sig")
    overlap.to_csv(outputs["overlap_metrics_csv"], index=False, encoding="utf-8-sig")
    distinction.to_csv(outputs["grid_distinction_csv"], index=False, encoding="utf-8-sig")
    write_report(Path(outputs["report_md"]), cfg, daily_all, hourly_all, overlap, distinction)

    expected_days = (pd.Timestamp(source["end_date"]) - pd.Timestamp(source["start_date"])).days + 1
    metadata["expected_days_per_point"] = expected_days
    metadata["expected_hours_per_point"] = expected_days * 24
    metadata["total_daily_rows"] = len(daily_all)
    metadata["total_hourly_rows"] = len(hourly_all)
    metadata["daily_csv_sha256"] = sha256_bytes(Path(outputs["daily_csv"]).read_bytes())
    metadata["hourly_csv_gz_sha256"] = sha256_bytes(Path(outputs["hourly_csv_gz"]).read_bytes())
    Path(outputs["metadata_json"]).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "orchards": daily_all["orchard_id"].nunique(),
                "daily_rows": len(daily_all),
                "hourly_rows": len(hourly_all),
                "daily_start": daily_write["date"].min(),
                "daily_end": daily_write["date"].max(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
