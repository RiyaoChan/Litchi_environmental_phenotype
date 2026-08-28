from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml

VARIABLE_MAP = {
    "temperature_2m_mean": "tmean_c",
    "temperature_2m_max": "tmax_c",
    "temperature_2m_min": "tmin_c",
    "precipitation_sum": "precip_mm",
    "relative_humidity_2m_mean": "relative_humidity_pct",
    "sunshine_duration": "sunshine_h",
    "shortwave_radiation_sum": "shortwave_radiation_mj_m2",
    "wind_speed_10m_mean": "wind_speed_mean_ms",
    "wind_speed_10m_max": "wind_speed_max_ms",
    "et0_fao_evapotranspiration": "et0_mm",
}


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError("Configuration root must be a mapping")
    return cfg


def request_json(url: str, params: dict[str, Any], attempts: int = 5) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=120)
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(str(payload.get("reason", payload)))
            return payload
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 16))
    raise RuntimeError(f"Open-Meteo request failed after {attempts} attempts: {last_error}")


def payload_to_frame(
    station_id: str,
    point_cfg: dict[str, Any],
    source_cfg: dict[str, Any],
    payload: dict[str, Any],
    request_params: dict[str, Any],
) -> pd.DataFrame:
    daily = payload.get("daily")
    units = payload.get("daily_units", {})
    if not isinstance(daily, dict) or "time" not in daily:
        raise ValueError(f"No daily data returned for {station_id}")

    frame = pd.DataFrame({"date": pd.to_datetime(daily["time"], errors="raise")})
    for source_name, target_name in VARIABLE_MAP.items():
        values = daily.get(source_name)
        if values is None:
            raise ValueError(f"Missing requested variable {source_name} for {station_id}")
        frame[target_name] = pd.to_numeric(pd.Series(values), errors="coerce")

    frame["sunshine_h"] = frame["sunshine_h"] / 3600.0
    request_fingerprint = hashlib.sha256(
        json.dumps(request_params, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    frame.insert(0, "station_id", station_id)
    frame.insert(1, "region_id", point_cfg["region_id"])
    frame["requested_latitude"] = float(point_cfg["latitude"])
    frame["requested_longitude"] = float(point_cfg["longitude"])
    frame["grid_latitude"] = payload.get("latitude")
    frame["grid_longitude"] = payload.get("longitude")
    frame["elevation_m"] = payload.get("elevation")
    frame["timezone"] = payload.get("timezone", source_cfg["timezone"])
    frame["source_provider"] = source_cfg["provider"]
    frame["source_dataset"] = source_cfg["dataset"]
    frame["source_model"] = source_cfg["model"]
    frame["coordinate_basis"] = point_cfg["coordinate_basis"]
    frame["request_fingerprint_sha256"] = request_fingerprint

    expected_units = {
        "temperature_2m_mean": "°C",
        "temperature_2m_max": "°C",
        "temperature_2m_min": "°C",
        "precipitation_sum": "mm",
        "relative_humidity_2m_mean": "%",
        "sunshine_duration": "s",
        "shortwave_radiation_sum": "MJ/m²",
        "et0_fao_evapotranspiration": "mm",
    }
    unit_mismatches = {
        key: {"returned": units.get(key), "expected": expected}
        for key, expected in expected_units.items()
        if units.get(key) not in {None, expected}
    }
    if unit_mismatches:
        raise ValueError(f"Unexpected units for {station_id}: {unit_mismatches}")

    return frame


def validate_complete(frame: pd.DataFrame, start_date: str, end_date: str) -> None:
    expected_dates = pd.date_range(start_date, end_date, freq="D")
    required = list(VARIABLE_MAP.values())
    for station_id, group in frame.groupby("station_id", sort=False):
        observed = pd.DatetimeIndex(group["date"].sort_values())
        missing_dates = expected_dates.difference(observed)
        duplicate_dates = group.loc[group["date"].duplicated(), "date"].tolist()
        if len(missing_dates) or duplicate_dates:
            raise ValueError(
                f"Date coverage failure for {station_id}: "
                f"missing={len(missing_dates)}, duplicates={len(duplicate_dates)}"
            )
        missing_values = group[required].isna().sum()
        if int(missing_values.sum()) > 0:
            raise ValueError(f"Missing ERA5 values for {station_id}: {missing_values.to_dict()}")
        if not (group["tmin_c"] <= group["tmean_c"]).all() or not (
            group["tmean_c"] <= group["tmax_c"]
        ).all():
            raise ValueError(f"Temperature order failure in ERA5 data for {station_id}")
        if not group["relative_humidity_pct"].between(0, 100).all():
            raise ValueError(f"Relative humidity outside 0-100 for {station_id}")
        if not (group["precip_mm"] >= 0).all():
            raise ValueError(f"Negative precipitation for {station_id}")
        if not group["sunshine_h"].between(0, 24).all():
            raise ValueError(f"Sunshine duration outside 0-24 h for {station_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download complete daily ERA5 weather for litchi regions")
    parser.add_argument("--config", default="configs/external_weather.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    source = cfg["source"]
    outputs = cfg["outputs"]
    variables = list(source["variables"])
    raw_dir = Path(outputs["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    Path(outputs["complete_csv"]).parent.mkdir(parents=True, exist_ok=True)

    downloaded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    frames: list[pd.DataFrame] = []
    metadata: dict[str, Any] = {
        "downloaded_at_utc": downloaded_at,
        "source": source,
        "points": {},
    }

    for station_id, point_cfg in cfg["points"].items():
        params = {
            "latitude": point_cfg["latitude"],
            "longitude": point_cfg["longitude"],
            "start_date": source["start_date"],
            "end_date": source["end_date"],
            "daily": ",".join(variables),
            "timezone": source["timezone"],
            "models": source["model"],
            "wind_speed_unit": "ms",
            "precipitation_unit": "mm",
            "temperature_unit": "celsius",
        }
        payload = request_json(source["api_base"], params)
        raw_path = raw_dir / f"{station_id}.json"
        raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()

        frame = payload_to_frame(station_id, point_cfg, source, payload, params)
        frames.append(frame)
        metadata["points"][station_id] = {
            "requested_latitude": point_cfg["latitude"],
            "requested_longitude": point_cfg["longitude"],
            "returned_grid_latitude": payload.get("latitude"),
            "returned_grid_longitude": payload.get("longitude"),
            "elevation_m": payload.get("elevation"),
            "coordinate_basis": point_cfg["coordinate_basis"],
            "raw_json_sha256": raw_hash,
            "n_days": len(frame),
            "daily_units": payload.get("daily_units", {}),
        }

    complete = pd.concat(frames, ignore_index=True)
    complete["downloaded_at_utc"] = downloaded_at
    complete = complete.sort_values(["station_id", "date"], kind="stable")
    validate_complete(complete, source["start_date"], source["end_date"])
    complete["date"] = complete["date"].dt.strftime("%Y-%m-%d")
    complete.to_csv(outputs["complete_csv"], index=False, encoding="utf-8-sig")

    metadata["complete_csv_sha256"] = hashlib.sha256(
        Path(outputs["complete_csv"]).read_bytes()
    ).hexdigest()
    metadata["expected_days_per_point"] = (
        pd.Timestamp(source["end_date"]) - pd.Timestamp(source["start_date"])
    ).days + 1
    metadata["total_rows"] = len(complete)
    Path(outputs["metadata_json"]).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "rows": len(complete),
                "points": complete["station_id"].nunique(),
                "date_start": complete["date"].min(),
                "date_end": complete["date"].max(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
