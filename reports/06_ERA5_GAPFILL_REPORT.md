# ERA5逐日气象补齐与重叠期验证报告

## 数据源与范围

- 数据集：ERA5 reanalysis，通过 Open-Meteo Historical Weather API 下载。
- 时间：2021-08-01—2026-06-30，北京时间自然日。
- 每个区域理论日数：1795。
- ERA5完整序列作为正式模型的候选主气象源；混合序列仅用于敏感性分析。
- 原始站点文件和 `data/processed/weather_daily.csv` 未覆盖或改写。

## 区域代理点

- `haikou_region_proxy`: (19.75, 110.55), regional proxy for the Yunlong/Bannei and Sanmenpo/Hongming production area; not an exact orchard coordinate
- `lingshui_region_proxy`: (18.55, 110.0), regional proxy near Timeng Township, Lingshui; not an exact orchard coordinate

这些坐标是区域代理点，不是果园精确GPS。获得果园GPS后应重新下载并版本化。

## 产物语义

1. `weather_daily_era5.csv`：同一来源、时间连续的ERA5序列，适合主分析。
2. `weather_daily_hybrid_raw.csv`：有效站点观测优先，缺口使用原始ERA5，适合敏感性分析。
3. `weather_daily_hybrid_bias_adjusted.csv`：有效站点观测优先，缺口使用基于重叠期的简易校正ERA5，仅作敏感性分析。
4. 降水的网格—站点差异可能明显；不得把重分析值表述为果园现场实测。

## 重叠期验证

| station_id            | variable              |   n_pairs |   station_mean |   era5_mean |   era5_minus_station_bias |    mae |    rmse |   pearson_r |   spearman_r |
|:----------------------|:----------------------|----------:|---------------:|------------:|--------------------------:|-------:|--------:|------------:|-------------:|
| haikou_region_proxy   | tmean_c               |       615 |        21.8595 |     22.1263 |                    0.2668 | 0.5124 |  0.6463 |      0.9869 |       0.9877 |
| haikou_region_proxy   | tmin_c                |       615 |        19.7872 |     20.0776 |                    0.2904 | 0.8839 |  1.1329 |      0.9549 |       0.9621 |
| haikou_region_proxy   | tmax_c                |       615 |        25.3343 |     24.7633 |                   -0.5711 | 1.0624 |  1.2906 |      0.9699 |       0.965  |
| haikou_region_proxy   | precip_mm             |       615 |         6.2013 |      3.2291 |                   -2.9722 | 5.2463 | 20.4645 |      0.5765 |       0.6074 |
| haikou_region_proxy   | relative_humidity_pct |       615 |        82.3283 |     79.8569 |                   -2.4714 | 3.6727 |  4.6721 |      0.9134 |       0.8932 |
| haikou_region_proxy   | sunshine_h            |       552 |         3.5504 |      8.045  |                    4.4946 | 4.5264 |  5.4818 |      0.6162 |       0.7316 |
| lingshui_region_proxy | tmean_c               |       583 |        22.5254 |     23.4981 |                    0.9727 | 1.1168 |  1.3956 |      0.9337 |       0.9392 |
| lingshui_region_proxy | tmin_c                |       583 |        19.5648 |     22.0815 |                    2.5166 | 2.5702 |  3.0434 |      0.8402 |       0.8457 |
| lingshui_region_proxy | tmax_c                |       583 |        27.522  |     25.141  |                   -2.381  | 2.5261 |  2.8206 |      0.8904 |       0.8701 |
| lingshui_region_proxy | precip_mm             |       612 |         5.3828 |      3.7673 |                   -1.6155 | 4.3492 | 15.218  |      0.6596 |       0.7268 |
| lingshui_region_proxy | relative_humidity_pct |       614 |        79.4594 |     80.7801 |                    1.3207 | 6.1155 | 10.2292 |      0.6392 |       0.774  |
| lingshui_region_proxy | sunshine_h            |       545 |         4.985  |      8.7861 |                    3.8012 | 3.8388 |  4.6992 |      0.6621 |       0.6973 |

## 简易校正系数

| station_id            | variable              | method                     |   coefficient |   raw_coefficient |   n_pairs | scope                                    |
|:----------------------|:----------------------|:---------------------------|--------------:|------------------:|----------:|:-----------------------------------------|
| haikou_region_proxy   | tmean_c               | additive_mean_offset       |       -0.2668 |           -0.2668 |       615 | all_valid_overlap_days; sensitivity_only |
| haikou_region_proxy   | tmin_c                | additive_mean_offset       |       -0.2904 |           -0.2904 |       615 | all_valid_overlap_days; sensitivity_only |
| haikou_region_proxy   | tmax_c                | additive_mean_offset       |        0.5711 |            0.5711 |       615 | all_valid_overlap_days; sensitivity_only |
| haikou_region_proxy   | precip_mm             | multiplicative_total_ratio |        1.9204 |            1.9204 |       615 | all_valid_overlap_days; sensitivity_only |
| haikou_region_proxy   | relative_humidity_pct | additive_mean_offset       |        2.4714 |            2.4714 |       615 | all_valid_overlap_days; sensitivity_only |
| haikou_region_proxy   | sunshine_h            | additive_mean_offset       |       -4.4946 |           -4.4946 |       552 | all_valid_overlap_days; sensitivity_only |
| lingshui_region_proxy | tmean_c               | additive_mean_offset       |       -0.9727 |           -0.9727 |       583 | all_valid_overlap_days; sensitivity_only |
| lingshui_region_proxy | tmin_c                | additive_mean_offset       |       -2.5166 |           -2.5166 |       583 | all_valid_overlap_days; sensitivity_only |
| lingshui_region_proxy | tmax_c                | additive_mean_offset       |        2.381  |            2.381  |       583 | all_valid_overlap_days; sensitivity_only |
| lingshui_region_proxy | precip_mm             | multiplicative_total_ratio |        1.4288 |            1.4288 |       612 | all_valid_overlap_days; sensitivity_only |
| lingshui_region_proxy | relative_humidity_pct | additive_mean_offset       |       -1.3207 |           -1.3207 |       614 | all_valid_overlap_days; sensitivity_only |
| lingshui_region_proxy | sunshine_h            | additive_mean_offset       |       -3.8012 |           -3.8012 |       545 | all_valid_overlap_days; sensitivity_only |

温度、湿度和日照采用全重叠期均值偏差；降水采用累计量比值并截断至0.25—4.0。由于现有站点数据主要集中在10月至次年1月，这些系数外推到2—9月存在不确定性，因此校正混合序列不能替代完整ERA5主序列。
