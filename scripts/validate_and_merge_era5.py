from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

PAIR_VARIABLES = [
    "tmean_c",
    "tmin_c",
    "tmax_c",
    "precip_mm",
    "relative_humidity_pct",
    "sunshine_h",
]
ALL_FILL_VARIABLES = [
    "tmean_c",
    "tmin_c",
    "tmax_c",
    "precip_mm",
    "relative_humidity_pct",
    "sunshine_h",
    "shortwave_radiation_mj_m2",
    "wind_speed_mean_ms",
    "wind_speed_max_ms",
    "et0_mm",
]


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def safe_corr(x: pd.Series, y: pd.Series, method: str) -> float:
    if len(x) < 3 or x.nunique(dropna=True) < 2 or y.nunique(dropna=True) < 2:
        return float("nan")
    return float(x.corr(y, method=method))


def valid_station_masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    numeric = {col: pd.to_numeric(frame.get(col), errors="coerce") for col in PAIR_VARIABLES}
    temperature_order = (
        numeric["tmin_c"].notna()
        & numeric["tmean_c"].notna()
        & numeric["tmax_c"].notna()
        & (numeric["tmin_c"] <= numeric["tmean_c"])
        & (numeric["tmean_c"] <= numeric["tmax_c"])
    )
    return {
        "tmean_c": numeric["tmean_c"].notna() & temperature_order,
        "tmin_c": numeric["tmin_c"].notna() & temperature_order,
        "tmax_c": numeric["tmax_c"].notna() & temperature_order,
        "precip_mm": numeric["precip_mm"].notna() & (numeric["precip_mm"] >= 0),
        "relative_humidity_pct": numeric["relative_humidity_pct"].between(0, 100),
        "sunshine_h": numeric["sunshine_h"].between(0, 24),
    }


def build_overlap_metrics(station: pd.DataFrame, era5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    joined = station.merge(
        era5,
        on=["station_id", "date"],
        how="inner",
        suffixes=("_station", "_era5"),
        validate="many_to_one",
    )
    rows: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []

    for station_id, group in joined.groupby("station_id", sort=True):
        station_view = pd.DataFrame(
            {col: group[f"{col}_station"] for col in PAIR_VARIABLES}, index=group.index
        )
        masks = valid_station_masks(station_view)
        for variable in PAIR_VARIABLES:
            x = pd.to_numeric(group.loc[masks[variable], f"{variable}_station"], errors="coerce")
            y = pd.to_numeric(group.loc[masks[variable], f"{variable}_era5"], errors="coerce")
            valid = x.notna() & y.notna()
            x, y = x[valid], y[valid]
            if len(x) == 0:
                continue
            error = y - x
            rows.append(
                {
                    "station_id": station_id,
                    "variable": variable,
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
            if variable == "precip_mm":
                era5_total = float(y.sum())
                ratio = float(x.sum() / era5_total) if era5_total > 0 else 1.0
                ratio_capped = min(max(ratio, 0.25), 4.0)
                coefficients.append(
                    {
                        "station_id": station_id,
                        "variable": variable,
                        "method": "multiplicative_total_ratio",
                        "coefficient": ratio_capped,
                        "raw_coefficient": ratio,
                        "n_pairs": len(x),
                        "scope": "all_valid_overlap_days; sensitivity_only",
                    }
                )
            else:
                offset = float((x - y).mean())
                coefficients.append(
                    {
                        "station_id": station_id,
                        "variable": variable,
                        "method": "additive_mean_offset",
                        "coefficient": offset,
                        "raw_coefficient": offset,
                        "n_pairs": len(x),
                        "scope": "all_valid_overlap_days; sensitivity_only",
                    }
                )

    return pd.DataFrame(rows), pd.DataFrame(coefficients)


def apply_adjustment(series: pd.Series, variable: str, method: str, coefficient: float) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if method == "additive_mean_offset":
        values = values + coefficient
    elif method == "multiplicative_total_ratio":
        values = values * coefficient
    else:
        raise ValueError(f"Unknown adjustment method: {method}")
    if variable == "relative_humidity_pct":
        values = values.clip(0, 100)
    elif variable == "sunshine_h":
        values = values.clip(0, 24)
    elif variable == "precip_mm":
        values = values.clip(lower=0)
    return values


def build_hybrid(
    station: pd.DataFrame,
    era5: pd.DataFrame,
    coefficients: pd.DataFrame,
    adjusted: bool,
) -> pd.DataFrame:
    station = station.copy()
    station["date"] = pd.to_datetime(station["date"])
    era5 = era5.copy()
    era5["date"] = pd.to_datetime(era5["date"])

    base_cols = ["station_id", "region_id", "date"] + ALL_FILL_VARIABLES
    output = era5[base_cols].copy()
    output = output.rename(columns={v: f"{v}_era5" for v in ALL_FILL_VARIABLES})
    station_cols = ["station_id", "date"] + [v for v in PAIR_VARIABLES if v in station.columns]
    output = output.merge(station[station_cols], on=["station_id", "date"], how="left")

    coefficient_lookup = {
        (row.station_id, row.variable): (row.method, float(row.coefficient))
        for row in coefficients.itertuples(index=False)
    }

    station_masks = valid_station_masks(output[[v for v in PAIR_VARIABLES]])
    for variable in ALL_FILL_VARIABLES:
        era5_col = f"{variable}_era5"
        fill_values = output[era5_col]
        if adjusted and variable in PAIR_VARIABLES:
            adjusted_parts = []
            for station_id, idx in output.groupby("station_id").groups.items():
                method_coef = coefficient_lookup.get((station_id, variable))
                values = output.loc[idx, era5_col]
                if method_coef is not None:
                    values = apply_adjustment(values, variable, *method_coef)
                adjusted_parts.append(values)
            fill_values = pd.concat(adjusted_parts).sort_index()

        if variable in PAIR_VARIABLES:
            valid_station = station_masks[variable]
            output[variable] = output[variable].where(valid_station, fill_values)
            output[f"{variable}_source"] = np.where(
                valid_station,
                "station_observed",
                "era5_bias_adjusted_gapfill" if adjusted else "era5_raw_gapfill",
            )
        else:
            output[variable] = fill_values
            output[f"{variable}_source"] = "era5_complete_covariate"

    keep = ["station_id", "region_id", "date"]
    for variable in ALL_FILL_VARIABLES:
        keep.extend([variable, f"{variable}_source"])
    output = output[keep].sort_values(["station_id", "date"])
    output["date"] = output["date"].dt.strftime("%Y-%m-%d")
    return output


def write_report(
    path: Path,
    era5: pd.DataFrame,
    metrics: pd.DataFrame,
    coefficients: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source = config["source"]
    point_lines = [
        f"- `{station_id}`: ({point['latitude']}, {point['longitude']}), {point['coordinate_basis']}"
        for station_id, point in config["points"].items()
    ]
    metrics_table = metrics.round(4).to_markdown(index=False) if not metrics.empty else "无可用重叠配对。"
    coefficients_table = (
        coefficients.round(4).to_markdown(index=False) if not coefficients.empty else "未估计校正系数。"
    )
    text = f"""# ERA5逐日气象补齐与重叠期验证报告

## 数据源与范围

- 数据集：{source['dataset']}，通过 {source['provider']} 下载。
- 时间：{source['start_date']}—{source['end_date']}，北京时间自然日。
- 每个区域理论日数：{era5.groupby('station_id')['date'].nunique().min()}。
- ERA5完整序列作为正式模型的候选主气象源；混合序列仅用于敏感性分析。
- 原始站点文件和 `data/processed/weather_daily.csv` 未覆盖或改写。

## 区域代理点

{chr(10).join(point_lines)}

这些坐标是区域代理点，不是果园精确GPS。获得果园GPS后应重新下载并版本化。

## 产物语义

1. `weather_daily_era5.csv`：同一来源、时间连续的ERA5序列，适合主分析。
2. `weather_daily_hybrid_raw.csv`：有效站点观测优先，缺口使用原始ERA5，适合敏感性分析。
3. `weather_daily_hybrid_bias_adjusted.csv`：有效站点观测优先，缺口使用基于重叠期的简易校正ERA5，仅作敏感性分析。
4. 降水的网格—站点差异可能明显；不得把重分析值表述为果园现场实测。

## 重叠期验证

{metrics_table}

## 简易校正系数

{coefficients_table}

温度、湿度和日照采用全重叠期均值偏差；降水采用累计量比值并截断至0.25—4.0。由于现有站点数据主要集中在10月至次年1月，这些系数外推到2—9月存在不确定性，因此校正混合序列不能替代完整ERA5主序列。
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ERA5 against station overlap and build gap-filled sensitivity series")
    parser.add_argument("--config", default="configs/external_weather.yaml")
    parser.add_argument("--station", default="data/processed/weather_daily.csv")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    outputs = cfg["outputs"]
    era5 = pd.read_csv(outputs["complete_csv"], parse_dates=["date"])
    station = pd.read_csv(args.station, parse_dates=["date"])

    metrics, coefficients = build_overlap_metrics(station, era5)
    Path(outputs["overlap_metrics_csv"]).parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(outputs["overlap_metrics_csv"], index=False, encoding="utf-8-sig")
    coefficients.to_csv(outputs["bias_coefficients_csv"], index=False, encoding="utf-8-sig")

    hybrid_raw = build_hybrid(station, era5, coefficients, adjusted=False)
    hybrid_adjusted = build_hybrid(station, era5, coefficients, adjusted=True)
    Path(outputs["hybrid_raw_csv"]).parent.mkdir(parents=True, exist_ok=True)
    hybrid_raw.to_csv(outputs["hybrid_raw_csv"], index=False, encoding="utf-8-sig")
    hybrid_adjusted.to_csv(outputs["hybrid_adjusted_csv"], index=False, encoding="utf-8-sig")

    write_report(Path(outputs["overlap_report_md"]), era5, metrics, coefficients, cfg)
    print(
        json.dumps(
            {
                "status": "ok",
                "era5_rows": len(era5),
                "overlap_metric_rows": len(metrics),
                "hybrid_raw_rows": len(hybrid_raw),
                "hybrid_adjusted_rows": len(hybrid_adjusted),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
