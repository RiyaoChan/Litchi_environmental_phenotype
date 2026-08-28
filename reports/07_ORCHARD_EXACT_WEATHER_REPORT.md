# 三个荔枝果园精确坐标ERA5逐日与逐小时气象数据报告

## 坐标来源

三组坐标均从2024—2025和2025—2026两份《荔枝龙眼产业技术体系示范园年度工作总结》表1提取，两份文件记录一致。DMS坐标按WGS84十进制度公式转换，不改变原始秒数。

| orchard_id   | cultivar   | latitude_dms     | longitude_dms     |   latitude_decimal |   longitude_decimal |   returned_grid_latitude |   returned_grid_longitude |   elevation_m |   request_to_grid_km |
|:-------------|:-----------|:-----------------|:------------------|-------------------:|--------------------:|-------------------------:|--------------------------:|--------------:|---------------------:|
| bannei       | 妃子笑        | N 19° 53' 57.63" | E 110° 29' 58.18" |            19.8993 |             110.499 |                    20    |                     110.5 |            27 |              11.1928 |
| hongming     | 白糖罂        | N 19° 41' 54.98" | E 110° 34' 49.95" |            19.6986 |             110.581 |                    19.75 |                     110.5 |            78 |              10.1848 |
| luhong       | 妃子笑        | N 18° 36' 34.77" | E 109° 56' 32.26" |            18.6097 |             109.942 |                    18.5  |                     110   |            42 |              13.6266 |

## 数据源与覆盖

- 数据源：ERA5 reanalysis，经Open-Meteo Historical Weather API获取。
- 模型：`era5`；时区：`Asia/Shanghai`。
- 日期：2021-08-01—2026-06-30。
- 逐日记录：5385行；逐小时记录：129240行。
- 每个果园逐日1795天、逐小时43080小时，覆盖连续且核心变量无缺失。
- 这些数据属于网格再分析数据，不是果园现场气象站实测。

## 逐日变量

- `tmean_c`
- `tmax_c`
- `tmin_c`
- `dewpoint_mean_c`
- `dewpoint_max_c`
- `dewpoint_min_c`
- `relative_humidity_mean_pct`
- `relative_humidity_max_pct`
- `relative_humidity_min_pct`
- `precip_mm`
- `rain_mm`
- `precipitation_hours`
- `sunshine_h`
- `shortwave_radiation_mj_m2`
- `cloud_cover_mean_pct`
- `wind_speed_mean_ms`
- `wind_speed_max_ms`
- `wind_speed_min_ms`
- `wind_direction_dominant_deg`
- `et0_mm`
- `vpd_max_kpa`
- `soil_moisture_0_7cm_mean_m3_m3`
- `soil_moisture_7_28cm_mean_m3_m3`
- `soil_moisture_28_100cm_mean_m3_m3`
- `soil_moisture_0_100cm_mean_m3_m3`
- `soil_temperature_0_7cm_mean_c`
- `soil_temperature_7_28cm_mean_c`
- `soil_temperature_28_100cm_mean_c`
- `soil_temperature_0_100cm_mean_c`

## 逐小时变量

- `temperature_c`
- `relative_humidity_pct`
- `dewpoint_c`
- `vpd_kpa`
- `precip_mm`
- `rain_mm`
- `cloud_cover_pct`
- `sunshine_h`
- `shortwave_radiation_w_m2`
- `wind_speed_ms`
- `wind_direction_deg`
- `et0_mm`
- `soil_temperature_0_7cm_c`
- `soil_temperature_7_28cm_c`
- `soil_moisture_0_7cm_m3_m3`
- `soil_moisture_7_28cm_m3_m3`
- `soil_moisture_28_100cm_m3_m3`

逐小时变量主要用于计算夜间有效低温小时、连续低温过程、小时VPD、降雨过程和土壤水分背景；逐日变量用于物候阶段窗口、积温、辐射、水分平衡和产量建模。

## 果园网格区分检查

| orchard_a   | orchard_b   |   requested_distance_km |   grid_distance_km | same_returned_grid   | same_returned_elevation   | tmean_identical_all_days   | precip_identical_all_days   |   tmean_mean_abs_difference_c |   precip_mean_abs_difference_mm |
|:------------|:------------|------------------------:|-------------------:|:---------------------|:--------------------------|:---------------------------|:----------------------------|------------------------------:|--------------------------------:|
| bannei      | hongming    |                 23.8772 |            27.7988 | False                | False                     | False                      | False                       |                        0.5412 |                          2.2717 |
| bannei      | luhong      |                154.876  |           174.856  | False                | False                     | False                      | False                       |                        0.8128 |                          3.7785 |
| hongming    | luhong      |                138.405  |           148.588  | False                | False                     | False                      | False                       |                        0.984  |                          4.1761 |

`same_returned_grid=true`并不一定意味着所有温度完全相同，因为API可能按请求点海拔进行统计降尺度；正式建模仍须保留返回网格、海拔和请求坐标。

## 与现有区域气象文件的重叠期验证

| orchard_id   | point_id              | observed_station_id   | variable   |   n_pairs |   station_mean |   era5_mean |   era5_minus_station_bias |    mae |    rmse |   pearson_r |   spearman_r |
|:-------------|:----------------------|:----------------------|:-----------|----------:|---------------:|------------:|--------------------------:|-------:|--------:|------------:|-------------:|
| bannei       | bannei_orchard_era5   | haikou_region_proxy   | tmean_c    |       615 |        21.8595 |     22.4411 |                    0.5816 | 0.8356 |  1.0554 |      0.9701 |       0.9691 |
| bannei       | bannei_orchard_era5   | haikou_region_proxy   | tmin_c     |       615 |        19.7872 |     21.5454 |                    1.7582 | 1.8015 |  2.2015 |      0.9329 |       0.9376 |
| bannei       | bannei_orchard_era5   | haikou_region_proxy   | tmax_c     |       615 |        25.3343 |     23.5356 |                   -1.7987 | 2.1447 |  2.5274 |      0.9224 |       0.9173 |
| bannei       | bannei_orchard_era5   | haikou_region_proxy   | precip_mm  |       615 |         6.2013 |      3.6654 |                   -2.5359 | 4.9567 | 19.5235 |      0.6162 |       0.7251 |
| bannei       | bannei_orchard_era5   | haikou_region_proxy   | sunshine_h |       552 |         3.5504 |      8.2225 |                    4.6721 | 4.6904 |  5.6135 |      0.6075 |       0.7256 |
| hongming     | hongming_orchard_era5 | haikou_region_proxy   | tmean_c    |       615 |        21.8595 |     22.1524 |                    0.2928 | 0.5189 |  0.6585 |      0.9869 |       0.9875 |
| hongming     | hongming_orchard_era5 | haikou_region_proxy   | tmin_c     |       615 |        19.7872 |     20.1272 |                    0.34   | 0.8971 |  1.1471 |      0.9548 |       0.9622 |
| hongming     | hongming_orchard_era5 | haikou_region_proxy   | tmax_c     |       615 |        25.3343 |     24.8141 |                   -0.5202 | 1.0486 |  1.2706 |      0.9698 |       0.9647 |
| hongming     | hongming_orchard_era5 | haikou_region_proxy   | precip_mm  |       615 |         6.2013 |      3.2291 |                   -2.9722 | 5.2463 | 20.4645 |      0.5765 |       0.6074 |
| hongming     | hongming_orchard_era5 | haikou_region_proxy   | sunshine_h |       552 |         3.5504 |      8.045  |                    4.4946 | 4.5264 |  5.4818 |      0.6162 |       0.7316 |
| luhong       | luhong_orchard_era5   | lingshui_region_proxy | tmean_c    |       583 |        22.5254 |     23.3861 |                    0.8607 | 1.0494 |  1.3197 |      0.9337 |       0.9393 |
| luhong       | luhong_orchard_era5   | lingshui_region_proxy | tmin_c     |       583 |        19.5648 |     21.9815 |                    2.4166 | 2.4787 |  2.9612 |      0.8402 |       0.8457 |
| luhong       | luhong_orchard_era5   | lingshui_region_proxy | tmax_c     |       583 |        27.522  |     25.041  |                   -2.481  | 2.612  |  2.9055 |      0.8904 |       0.8701 |
| luhong       | luhong_orchard_era5   | lingshui_region_proxy | precip_mm  |       612 |         5.3828 |      3.7673 |                   -1.6155 | 4.3492 | 15.218  |      0.6596 |       0.7268 |
| luhong       | luhong_orchard_era5   | lingshui_region_proxy | sunshine_h |       545 |         4.985  |      8.7861 |                    3.8012 | 3.8388 |  4.6992 |      0.6621 |       0.6973 |

办内和红明均与现有海口区域序列比较，鲁宏与陵水区域序列比较。该比较只用于质量控制；区域气象文件不能被表述为果园现场站观测。

## 使用建议

1. 正式主分析优先使用同一来源、连续完整的果园级ERA5序列。
2. P1花芽诱导模型优先使用逐小时温度、相对湿度、VPD和降雨；P2/P3及产量模型使用逐日阶段特征。
3. 变量很多不等于全部进入小样本模型。每个阶段应预先限定少量生理相关指标，并在整年留出验证中比较。
4. 土壤水分是网格模型估计，且不知道果园灌溉过程，只能作为气象水分背景或敏感性变量。
5. 台风风害不能仅依赖ERA5日平均或日最大风速定量，应结合台风最佳路径、站点阵风和果园损伤记录另行分析。
