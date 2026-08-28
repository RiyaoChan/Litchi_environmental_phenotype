# R4 Phase 0：精确坐标数据接管与闸门

状态：**pass**。逐日5385行，逐小时129240行；每园1795日、43080小时。覆盖2021-08-01至2026-06-30，本地时区Asia/Shanghai。完整检查见data_integrity_checks.csv，不以文件行数替代连续性检查。

## 实际网格身份

| orchard_id | requested_latitude | requested_longitude | grid_latitude | grid_longitude | elevation_m | grid_distance_km |
| --- | --- | --- | --- | --- | --- | --- |
| bannei | 19.9 | 110.5 | 20 | 110.5 | 27 | 11.19 |
| hongming | 19.7 | 110.6 | 19.75 | 110.5 | 78 | 10.18 |
| luhong | 18.61 | 109.9 | 18.5 | 110 | 42 | 13.63 |

| orchard_a | orchard_b | variable | exactly_identical | mean_absolute_difference | pearson_r |
| --- | --- | --- | --- | --- | --- |
| bannei | hongming | tmean_c | False | 0.5412 | 0.9858 |
| bannei | hongming | precip_mm | False | 2.272 | 0.9087 |
| bannei | luhong | tmean_c | False | 0.8128 | 0.9829 |
| bannei | luhong | precip_mm | False | 3.778 | 0.5322 |
| hongming | luhong | tmean_c | False | 0.984 | 0.9725 |
| hongming | luhong | precip_mm | False | 4.176 | 0.5315 |

请求坐标精确不等于网格空间分辨率达到果园尺度。三园落在3个返回网格；相邻园天气仍有空间相关性。数据必须称为“按果园坐标提取的ERA5网格再分析”，不能称现场气象站实测。API elevation是降尺度使用的返回高程，不能自动称为原生网格平均地形高度。[Open-Meteo官方说明](https://open-meteo.com/en/docs/historical-weather-api)

## 日小时对齐

| orchard_id | mean_abs_tmean_difference_c | max_abs_tmean_difference_c | daily_hourly_days_compared |
| --- | --- | --- | --- |
| bannei | 0.02603 | 0.06667 | 1795 |
| hongming | 0.0252 | 0.0625 | 1795 |
| luhong | 0.02636 | 0.06667 | 1795 |

小时标签按API元数据的上海本地时间读取，不再重复加8小时；每日24小时温度均值与API日均的微小差异按0.1℃舍入容差核验。小时雨量是前一小时累计，不能把它解释为瞬时雨强。主实验沿用API日聚合的降水指标。

## 独立终点与资格

主分析P1/P2/P3各12条；正常产量候选12个，5年。129240小时不是独立标签数。2025办内最终产量0，未测构成NA；办内2025、红明2025/2026不入正常产量主训练。沿用已确认A列跨年物候，不改月日、A39或原始文件。

## 下阶段

通过天气QC后先执行预注册候选的嵌套LOYO及前向滚动；产量仍须检查各折动态特征完整性。全部配置须先提交，不能看到外层结果后改候选网格。R4结果独立写入results/r4与reports/r4，不覆盖R2/R3。
