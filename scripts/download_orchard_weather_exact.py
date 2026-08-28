from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yaml

DAILY_MAP = {
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

HOURLY_MAP = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "relative_humidity_pct",
    "dew_point_2m": "dewpoint_c",
    "vapour_pressure_deficit": "vpd_kpa",
    "precipitation": "precip_mm",
    "rain": "rain_mm",
    "cloud_cover": "cloud_cover_pct",
    "sunshine_duration": "sunshine_h",
    "shortwave_radiation": "shortwave_radiation_w_m2",
    "wind_speed_10m": "wind_speed_ms",
    "wind_direction_10m": "wind_direction_deg",
    "et0_fao_evapotranspiration": "et0_mm",
    "soil_temperature_0_to_7cm": "soil_temperature_0_7cm_c",
    "soil_temperature_7_to_28cm": "soil_temperature_7_28cm_c",
    "soil_moisture_0_to_7cm": "soil_moisture_0_7cm_m3_m3",
    "soil_moisture_7_to_28cm": "soil_moisture_7_28cm_m3_m3",
    "soil_moisture_28_to_100cm": "soil_moisture_28_100cm_m3_m3",
}

OVERLAP_VARIABLES = {
    "tmean_c": "tmean_c",
    "tmin_c": "tmin_c",
    "tmax_c": "tmax_c",
    "precip_mm": "precip_mm",
    "relative_humidity_pct": "relative_humidity_mean_pct",
    "sunshine_h": "sunshine_h",
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
            response = requests.get(url, params=params, timeout=240)
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(str(payload.get("reason", payload)))
            return payload
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 20))
    raise RuntimeError(f"Open-Meteo request failed after {attempts} attempts: {last_error}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(a))


def add_identity_columns(
    frame: pd.DataFrame,
    point_key: str,
    point: dict[str, Any],
    payload: dict[str, Any],
    source: dict[str, Any],
) -> pd.DataFrame:
    requested_lat = float(point["latitude"])
    requested_lon = float(point["longitude"])
    grid_lat = float(payload["latitude"])
    grid_lon = float(payload["longitude"])
    identity = {
        "orchard_id": point["orchard_id"],
        "point_id": point["point_id"],
        "region_id": point["region_id"],
        "observed_station_id": point["observed_station_id"],
        "cultivar": point["cultivar"],
        "requested_latitude": requested_lat,
        "requested_longitude": requested_lon,
        "grid_latitude": grid_lat,
        "grid_longitude": grid_lon,
        "grid_distance_km": haversine_km(requested_lat, requested_lon, grid_lat, grid_lon),
        "elevation_m": payload.get("elevation"),
        "timezone": payload.get("timezone", source["timezone"]),
        "source_provider": source["provider"],
        "source_dataset": source["dataset"],
        "source_model": source["model"],
    }
    for position, (name, value) in enumerate(reversed(list(identity.items()))):
        frame.insert(0, name, value)
    return frame


def parse_resolution(
    payload: dict[str, Any],
    resolution: str,
    mapping: dict[str, str],
    point_key: str,
    point: dict[str, Any],
    source: dict[str, Any],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    block = payload.get(resolution)
    units = payload.get(f"{resolution}_units", {})
    time_key = "date" if resolution == "daily" else "time"
    if not isinstance(block, dict) or "time" not in block:
        raise ValueError(f"No {resolution} data returned for {point_key}")

    frame = pd.DataFrame({time_key: pd.to_datetime(block["time"], errors="raise")})
    dictionary_rows: list[dict[str, Any]] = []
    for source_name, target_name in mapping.items():
        values = block.get(source_name)
        if values is None:
            raise ValueError(f"Missing {resolution} variable {source_name} for {point_key}")
        frame[target_name] = pd.to_numeric(pd.Series(values), errors="coerce")
        returned_unit = units.get(source_name)
        standardized_unit = returned_unit
        transform = "identity"
        if source_name == "sunshine_duration":
            frame[target_name] = frame[target_name] / 3600.0
            standardized_unit = "h"
            transform = "seconds_to_hours"
        dictionary_rows.append(
            {
                "resolution": resolution,
                "source_variable": source_name,
                "standardized_variable": target_name,
                "returned_unit": returned_unit,
                "standardized_unit": standardized_unit,
                "transform": transform,
            }
        )

    frame = add_identity_columns(frame, point_key, point, payload, source)
    return frame, dictionary_rows


def validate_daily(frame: pd.DataFrame, start_date: str, end_date: str) -> None:
    expected = pd.date_range(start_date, end_date, freq="D")
    variables = list(DAILY_MAP.values())
    for orchard_id, group in frame.groupby("orchard_id", sort=False):
        observed = pd.DatetimeIndex(group["date"].sort_values())
        if len(expected.difference(observed)) or group["date"].duplicated().any():
            raise ValueError(f"Daily date coverage failure for {orchard_id}")
        missing = group[variables].isna().sum()
        if int(missing.sum()) > 0:
            raise ValueError(f"Missing daily values for {orchard_id}: {missing[missing > 0].to_dict()}")
        if not (group["tmin_c"] <= group["tmean_c"]).all() or not (
            group["tmean_c"] <= group["tmax_c"]
        ).all():
            raise ValueError(f"Daily temperature order failure for {orchard_id}")
        for column in [
            "relative_humidity_mean_pct",
            "relative_humidity_max_pct",
            "relative_humidity_min_pct",
            "cloud_cover_mean_pct",
        ]:
            if not group[column].between(0, 100).all():
                raise ValueError(f"Daily range failure for {orchard_id}: {column}")
        for column in ["precip_mm", "rain_mm", "precipitation_hours", "sunshine_h", "et0_mm", "vpd_max_kpa"]:
            if not (group[column] >= 0).all():
                raise ValueError(f"Negative daily value for {orchard_id}: {column}")
        if not group["sunshine_h"].between(0, 24).all():
            raise ValueError(f"Daily sunshine outside 0-24 h for {orchard_id}")
        if not group["precipitation_hours"].between(0, 24).all():
            raise ValueError(f"Daily precipitation hours outside 0-24 for {orchard_id}")
        for column in [c for c in group if c.startswith("soil_moisture_")]:
            if not group[column].between(0, 1).all():
                raise ValueError(f"Daily soil moisture outside 0-1 for {orchard_id}: {column}")


def validate_hourly(frame: pd.DataFrame, start_date: str, end_date: str) -> None:
    expected_days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days + 1
    expected_rows = expected_days * 24
    variables = list(HOURLY_MAP.values())
    for orchard_id, group in frame.groupby("orchard_id", sort=False):
        if len(group) != expected_rows:
            raise ValueError(f"Hourly row count failure for {orchard_id}: {len(group)} != {expected_rows}")
        if group["time"].duplicated().any():
            raise ValueError(f"Duplicate hourly timestamps for {orchard_id}")
        delta = group["time"].sort_values().diff().dropna()
        if not delta.eq(pd.Timedelta(hours=1)).all():
            raise ValueError(f"Non-hourly temporal gap for {orchard_id}")
        missing = group[variables].isna().sum()
        if int(missing.sum()) > 0:
            raise ValueError(f"Missing hourly values for {orchard_id}: {missing[missing > 0].to_dict()}")
        if not group["relative_humidity_pct"].between(0, 100).all():
            raise ValueError(f"Hourly humidity outside 0-100 for {orchard_id}")
        if not group["cloud_cover_pct"].between(0, 100).all():
            raise ValueError(f"Hourly cloud cover outside 0-100 for {orchard_id}")
        for column in ["vpd_kpa", "precip_mm", "rain_mm", "sunshine_h", "wind_speed_ms", "et0_mm"]:
            if not (group[column] >= 0).all():
                raise ValueError(f"Negative hourly value for {orchard_id}: {column}")
        if not group["sunshine_h"].between(0, 1).all():
            raise ValueError(f"Hourly sunshine outside 0-1 h for {orchard_id}")
        for column in [c for c in group if c.startswith("soil_moisture_")]:
            if not group[column].between(0, 1).all():
                raise ValueError(f"Hourly soil moisture outside 0-1 for {orchard_id}: {column}")


def safe_corr(x: pd.Series, y: pd.Series, method: str) -> float:
    if len(x) < 3 or x.nunique(dropna=True) < 2 or y.nunique(dropna=True) < 2:
        return float("nan")
    return float(x.corr(y, method=method))


def build_overlap_metrics(daily: pd.DataFrame, station_path: Path, config: dict[str, Any]) -> pd.DataFrame:
    if not station_path.exists():
        return pd.DataFrame()
    station = pd.read_csv(station_path, parse_dates=["date"])
    rows: list[dict[str, Any]] = []
    for point_key, point in config["points"].items():
        orchard = daily[daily["orchard_id"] == point["orchard_id"]].copy()
        station_group = station[station["station_id"] == point["observed_station_id"]].copy()
        joined = station_group.merge(orchard, on="date", how="inner", suffixes=("_station", "_era5"))
        temp_order = (
            pd.to_numeric(joined.get("tmin_c_station"), errors="coerce")
            <= pd.to_numeric(joined.get("tmean_c_station"), errors="coerce")
        ) & (
            pd.to_numeric(joined.get("tmean_c_station"), errors="coerce")
            <= pd.to_numeric(joined.get("tmax_c_station"), errors="coerce")
        )
        for station_variable, orchard_variable in OVERLAP_VARIABLES.items():
            station_col = f"{station_variable}_station"
            era5_col = orchard_variable if orchard_variable not in station_group.columns else f"{orchard_variable}_era5"
            if station_col not in joined or era5_col not in joined:
                continue
            x = pd.to_numeric(joined[station_col], errors="coerce")
            y = pd.to_numeric(joined[era5_col], errors="coerce")
            valid = x.notna() & y.notna()
            if station_variable in {"tmean_c", "tmin_c", "tmax_c"}:
                valid &= temp_order.fillna(False)
            elif station_variable == "precip_mm":
                valid &= x.ge(0)
            elif station_variable == "relative_humidity_pct":
                valid &= x.between(0, 100)
            elif station_variable == "sunshine_h":
                valid &= x.between(0, 24)
            x, y = x[valid], y[valid]
            if len(x) == 0:
                continue
            error = y - x
            rows.append(
                {
                    "orchard_id": point["orchard_id"],
                    "point_id": point["point_id"],
                    "observed_station_id": point["observed_station_id"],
                    "variable": station_variable,
                    "n_pairs": len(x),
                    "station_mean": x.mean(),
                    "era5_mean": y.mean(),
                    "era5_minus_station_bias": error.mean(),
                    "mae": error.abs().mean(),
                    "rmse": math.sqrt(float((error**2).mean())),
                    "pearson_r": safe_corr(x, y, "pearson"),
                    "spearman_r": safe_corr(x, y, "spearman"),
                }
            )
    return pd.DataFrame(rows)


def build_grid_distinction(daily: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    identities = (
        daily[["orchard_id", "requested_latitude", "requested_longitude", "grid_latitude", "grid_longitude", "elevation_m"]]
        .drop_duplicates("orchard_id")
        .set_index("orchard_id")
    )
    for orchard_a, orchard_b in combinations(sorted(identities.index), 2):
        a, b = identities.loc[orchard_a], identities.loc[orchard_b]
        view_a = daily[daily["orchard_id"] == orchard_a][["date", "tmean_c", "precip_mm"]]
        view_b = daily[daily["orchard_id"] == orchard_b][["date", "tmean_c", "precip_mm"]]
        joined = view_a.merge(view_b, on="date", suffixes=("_a", "_b"), validate="one_to_one")
        temp_diff = (joined["tmean_c_a"] - joined["tmean_c_b"]).abs()
        precip_diff = (joined["precip_mm_a"] - joined["precip_mm_b"]).abs()
        rows.append(
            {
                "orchard_a": orchard_a,
                "orchard_b": orchard_b,
                "requested_distance_km": haversine_km(
                    float(a.requested_latitude), float(a.requested_longitude),
                    float(b.requested_latitude), float(b.requested_longitude),
                ),
                "grid_distance_km": haversine_km(
                    float(a.grid_latitude), float(a.grid_longitude),
                    float(b.grid_latitude), float(b.grid_longitude),
                ),
                "same_returned_grid": bool(
                    math.isclose(float(a.grid_latitude), float(b.grid_latitude), abs_tol=1e-9)
                    and math.isclose(float(a.grid_longitude), float(b.grid_longitude), abs_tol=1e-9)
                ),
                "same_returned_elevation": bool(math.isclose(float(a.elevation_m), float(b.elevation_m), abs_tol=1e-9)),
                "tmean_identical_all_days": bool(temp_diff.eq(0).all()),
                "precip_identical_all_days": bool(precip_diff.eq(0).all()),
                "tmean_mean_abs_difference_c": temp_diff.mean(),
                "precip_mean_abs_difference_mm": precip_diff.mean(),
            }
        )
    return pd.DataFrame(rows)


def write_report(
    path: Path,
    config: dict[str, Any],
    daily: pd.DataFrame,
    hourly: pd.DataFrame,
    overlap: pd.DataFrame,
    distinction: pd.DataFrame,
) -> None:
    source = config["source"]
    point_rows = []
    for point_key, point in config["points"].items():
        row = daily[daily["orchard_id"] == point["orchard_id"]].iloc[0]
        point_rows.append(
            {
                "orchard_id": point["orchard_id"],
                "cultivar": point["cultivar"],
                "latitude_dms": point["latitude_dms"],
                "longitude_dms": point["longitude_dms"],
                "latitude_decimal": point["latitude"],
                "longitude_decimal": point["longitude"],
                "returned_grid_latitude": row.grid_latitude,
                "returned_grid_longitude": row.grid_longitude,
                "elevation_m": row.elevation_m,
                "request_to_grid_km": row.grid_distance_km,
            }
        )
    points_table = pd.DataFrame(point_rows).round(5).to_markdown(index=False)
    daily_vars = "\n".join(f"- `{value}`" for value in DAILY_MAP.values())
    hourly_vars = "\n".join(f"- `{value}`" for value in HOURLY_MAP.values())
    overlap_table = overlap.round(4).to_markdown(index=False) if not overlap.empty else "无可用重叠配对。"
    distinction_table = distinction.round(4).to_markdown(index=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# 三个荔枝果园精确坐标ERA5逐日与逐小时气象数据报告

## 坐标来源

三组坐标均从2024—2025和2025—2026两份《荔枝龙眼产业技术体系示范园年度工作总结》表1提取，两份文件记录一致。DMS坐标按WGS84十进制度公式转换，不改变原始秒数。

{points_table}

## 数据源与覆盖

- 数据源：{source['dataset']}，经{source['provider']}获取。
- 模型：`{source['model']}`；时区：`{source['timezone']}`。
- 日期：{source['start_date']}—{source['end_date']}。
- 逐日记录：{len(daily)}行；逐小时记录：{len(hourly)}行。
- 每个果园逐日{daily.groupby('orchard_id')['date'].nunique().min()}天、逐小时{hourly.groupby('orchard_id')['time'].nunique().min()}小时，覆盖连续且核心变量无缺失。
- 这些数据属于网格再分析数据，不是果园现场气象站实测。

## 逐日变量

{daily_vars}

## 逐小时变量

{hourly_vars}

逐小时变量主要用于计算夜间有效低温小时、连续低温过程、小时VPD、降雨过程和土壤水分背景；逐日变量用于物候阶段窗口、积温、辐射、水分平衡和产量建模。

## 果园网格区分检查

{distinction_table}

`same_returned_grid=true`并不一定意味着所有温度完全相同，因为API可能按请求点海拔进行统计降尺度；正式建模仍须保留返回网格、海拔和请求坐标。

## 与现有区域气象文件的重叠期验证

{overlap_table}

办内和红明均与现有海口区域序列比较，鲁宏与陵水区域序列比较。该比较只用于质量控制；区域气象文件不能被表述为果园现场站观测。

## 使用建议

1. 正式主分析优先使用同一来源、连续完整的果园级ERA5序列。
2. P1花芽诱导模型优先使用逐小时温度、相对湿度、VPD和降雨；P2/P3及产量模型使用逐日阶段特征。
3. 变量很多不等于全部进入小样本模型。每个阶段应预先限定少量生理相关指标，并在整年留出验证中比较。
4. 土壤水分是网格模型估计，且不知道果园灌溉过程，只能作为气象水分背景或敏感性变量。
5. 台风风害不能仅依赖ERA5日平均或日最大风速定量，应结合台风最佳路径、站点阵风和果园损伤记录另行分析。
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Download daily and hourly ERA5 data for exact litchi orchard coordinates")
    parser.add_argument("--config", default="configs/orchard_weather_exact.yaml")
    parser.add_argument("--station", default="data/processed/weather_daily.csv")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    source = cfg["source"]
    outputs = cfg["outputs"]
    raw_dir = Path(outputs["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    for key in ["daily_csv", "hourly_csv_gz", "metadata_json", "variable_dictionary_csv", "overlap_metrics_csv", "grid_distinction_csv", "report_md"]:
        Path(outputs[key]).parent.mkdir(parents=True, exist_ok=True)

    downloaded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    daily_frames: list[pd.DataFrame] = []
    hourly_frames: list[pd.DataFrame] = []
    dictionary_rows: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {"downloaded_at_utc": downloaded_at, "source": source, "points": {}}

    for point_key, point in cfg["points"].items():
        params = {
            "latitude": point["latitude"],
            "longitude": point["longitude"],
            "start_date": source["start_date"],
            "end_date": source["end_date"],
            "daily": ",".join(source["daily_variables"]),
            "hourly": ",".join(source["hourly_variables"]),
            "timezone": source["timezone"],
            "models": source["model"],
            "cell_selection": source.get("cell_selection", "land"),
            "wind_speed_unit": "ms",
            "precipitation_unit": "mm",
            "temperature_unit": "celsius",
        }
        payload = request_json(source["api_base"], params)
        raw_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        raw_path = raw_dir / f"{point_key}.json.gz"
        with gzip.open(raw_path, "wb", compresslevel=9) as fh:
            fh.write(raw_bytes)

        daily, daily_dict = parse_resolution(payload, "daily", DAILY_MAP, point_key, point, source)
        hourly, hourly_dict = parse_resolution(payload, "hourly", HOURLY_MAP, point_key, point, source)
        daily_frames.append(daily)
        hourly_frames.append(hourly)
        dictionary_rows.extend(daily_dict + hourly_dict)
        metadata["points"][point_key] = {
            "orchard_id": point["orchard_id"],
            "point_id": point["point_id"],
            "latitude_dms": point["latitude_dms"],
            "longitude_dms": point["longitude_dms"],
            "requested_latitude": point["latitude"],
            "requested_longitude": point["longitude"],
            "returned_grid_latitude": payload.get("latitude"),
            "returned_grid_longitude": payload.get("longitude"),
            "elevation_m": payload.get("elevation"),
            "coordinate_basis": point["coordinate_basis"],
            "coordinate_source_files": point["coordinate_source_files"],
            "coordinate_source_sha256": point["coordinate_source_sha256"],
            "raw_json_gz_sha256": sha256_bytes(raw_path.read_bytes()),
            "raw_payload_sha256": sha256_bytes(raw_bytes),
            "n_daily": len(daily),
            "n_hourly": len(hourly),
            "daily_units": payload.get("daily_units", {}),
            "hourly_units": payload.get("hourly_units", {}),
        }

    daily_all = pd.concat(daily_frames, ignore_index=True).sort_values(["orchard_id", "date"], kind="stable")
    hourly_all = pd.concat(hourly_frames, ignore_index=True).sort_values(["orchard_id", "time"], kind="stable")
    validate_daily(daily_all, source["start_date"], source["end_date"])
    validate_hourly(hourly_all, source["start_date"], source["end_date"])

    overlap = build_overlap_metrics(daily_all, Path(args.station), cfg)
    distinction = build_grid_distinction(daily_all)
    variable_dictionary = pd.DataFrame(dictionary_rows).drop_duplicates().sort_values(["resolution", "source_variable"])

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

    metadata["expected_days_per_point"] = (pd.Timestamp(source["end_date"]) - pd.Timestamp(source["start_date"])).days + 1
    metadata["expected_hours_per_point"] = metadata["expected_days_per_point"] * 24
    metadata["total_daily_rows"] = len(daily_all)
    metadata["total_hourly_rows"] = len(hourly_all)
    metadata["daily_csv_sha256"] = sha256_bytes(Path(outputs["daily_csv"]).read_bytes())
    metadata["hourly_csv_gz_sha256"] = sha256_bytes(Path(outputs["hourly_csv_gz"]).read_bytes())
    Path(outputs["metadata_json"]).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "orchards": daily_all["orchard_id"].nunique(),
        "daily_rows": len(daily_all),
        "hourly_rows": len(hourly_all),
        "daily_start": daily_write["date"].min(),
        "daily_end": daily_write["date"].max(),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
