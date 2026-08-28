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
    "dew_point_2m_mean": "dewpoint_mean_c",
    "dew_point_2m_max": "dewpoint_max_c",
    "dew_point_2m_min": "dewpoint_min_c",
    "relative_humidity_2m_mean": "relative_humidity_mean_pct",
    "relative_humidity_2m_max": "relative_humidity_max_pct",
    "relative_humidity_2m_min": "relative_humidity_min_pct",
    "precipitation_sum": "precip_mm",
    "rain_sum": "rain_mm",
    "precipitation_hours": "precipitation_hours",
    "sunshine_duration": "sunshine_h",
    "shortwave_radiation_sum": "shortwave_radiation_mj_m2",
    "cloud_cover_mean": "cloud_cover_mean_pct",
    "wind_speed_10m_mean": "wind_speed_mean_ms",
    "wind_speed_10m_max": "wind_speed_max_ms",
    "wind_speed_10m_min": "wind_speed_min_ms",
    "wind_direction_10m_dominant": "wind_direction_dominant_deg",
    "et0_fao_evapotranspiration": "et0_mm",
    "vapour_pressure_deficit_max": "vpd_max_kpa",
    "soil_moisture_0_to_7cm_mean": "soil_moisture_0_7cm_mean_m3_m3",
    "soil_moisture_7_to_28cm_mean": "soil_moisture_7_28cm_mean_m3_m3",
    "soil_moisture_28_to_100cm_mean": "soil_moisture_28_100cm_mean_m3_m3",
    "soil_moisture_0_to_100cm_mean": "soil_moisture_0_100cm_mean_m3_m3",
    "soil_temperature_0_to_7cm_mean": "soil_temperature_0_7cm_mean_c",
    "soil_temperature_7_to_28cm_mean": "soil_temperature_7_28cm_mean_c",
    "soil_temperature_28_to_100cm_mean": "soil_temperature_28_100cm_mean_c",
    "soil_temperature_0_to_100cm_mean": "soil_temperature_0_100cm_mean_c",
}


def request_json(url: str, params: dict[str, Any], attempts: int = 4) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=150)
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(str(payload.get("reason", payload)))
            return payload
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Open-Meteo request failed: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/orchard_weather_exact.yaml")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    source = cfg["source"]
    output_dir = Path("data/external/open_meteo_era5_orchards_daily")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[pd.DataFrame] = []
    metadata: dict[str, Any] = {
        "downloaded_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "provider": source["provider"],
            "dataset": source["dataset"],
            "model": source["model"],
            "timezone": source["timezone"],
            "start_date": source["start_date"],
            "end_date": source["end_date"],
            "license": source["license"],
            "daily_variables": list(VARIABLE_MAP),
        },
        "points": {},
    }

    for orchard_id, point in cfg["points"].items():
        params = {
            "latitude": point["latitude"],
            "longitude": point["longitude"],
            "start_date": source["start_date"],
            "end_date": source["end_date"],
            "daily": ",".join(VARIABLE_MAP),
            "timezone": source["timezone"],
            "models": source["model"],
            "cell_selection": source.get("cell_selection", "land"),
            "wind_speed_unit": "ms",
            "precipitation_unit": "mm",
            "temperature_unit": "celsius",
        }
        payload = request_json(source["api_base"], params)
        daily = payload["daily"]
        frame = pd.DataFrame({"date": pd.to_datetime(daily["time"])})
        for source_name, target_name in VARIABLE_MAP.items():
            frame[target_name] = pd.to_numeric(pd.Series(daily[source_name]), errors="raise")
        frame["sunshine_h"] = frame["sunshine_h"] / 3600.0
        frame.insert(0, "orchard_id", orchard_id)
        frame.insert(1, "point_id", point["point_id"])
        frame.insert(2, "region_id", point["region_id"])
        frame.insert(3, "cultivar", point["cultivar"])
        frame["requested_latitude"] = float(point["latitude"])
        frame["requested_longitude"] = float(point["longitude"])
        frame["grid_latitude"] = payload["latitude"]
        frame["grid_longitude"] = payload["longitude"]
        frame["elevation_m"] = payload["elevation"]
        frame["source_dataset"] = source["dataset"]
        frame["source_model"] = source["model"]
        rows.append(frame)
        raw_path = output_dir / f"raw_{orchard_id}.json"
        raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        metadata["points"][orchard_id] = {
            "latitude_dms": point["latitude_dms"],
            "longitude_dms": point["longitude_dms"],
            "requested_latitude": point["latitude"],
            "requested_longitude": point["longitude"],
            "returned_grid_latitude": payload["latitude"],
            "returned_grid_longitude": payload["longitude"],
            "elevation_m": payload["elevation"],
            "coordinate_basis": point["coordinate_basis"],
            "coordinate_source_files": point["coordinate_source_files"],
            "n_days": len(frame),
            "raw_json_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            "daily_units": payload.get("daily_units", {}),
        }

    data = pd.concat(rows, ignore_index=True).sort_values(["orchard_id", "date"])
    expected = pd.date_range(source["start_date"], source["end_date"], freq="D")
    required = list(VARIABLE_MAP.values())
    for orchard_id, group in data.groupby("orchard_id"):
        assert len(group) == len(expected)
        assert pd.DatetimeIndex(group["date"]).equals(expected)
        assert not group[required].isna().any().any()
        assert (group["tmin_c"] <= group["tmean_c"]).all()
        assert (group["tmean_c"] <= group["tmax_c"]).all()
        assert group["sunshine_h"].between(0, 24).all()
        assert group["relative_humidity_mean_pct"].between(0, 100).all()
        assert group["precip_mm"].ge(0).all()

    csv_path = output_dir / "weather_daily_era5_exact_orchards.csv"
    data["date"] = data["date"].dt.strftime("%Y-%m-%d")
    data.to_csv(csv_path, index=False, encoding="utf-8-sig")
    metadata["total_rows"] = len(data)
    metadata["expected_days_per_point"] = len(expected)
    metadata["csv_sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    (output_dir / "download_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    dictionary = pd.DataFrame(
        [{"source_variable": k, "standardized_variable": v} for k, v in VARIABLE_MAP.items()]
    )
    dictionary.to_csv(output_dir / "variable_dictionary.csv", index=False, encoding="utf-8-sig")
    print(json.dumps({"status": "ok", "rows": len(data), "orchards": 3}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
