# P1：嵌套按年验证与前向滚动

主分析12个果园—产季，5年；同任务所有模型使用相同测试样本。每折内选择候选温度/形状，事件累计阈值只用训练样本。扩展进入条件：False。

## LOYO留出预测

| validation | model_id | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days | delta_MAE_days | relative_MAE_reduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LOYO | P1-B0 | 12 | 12 | 0 | 4.833 | 6.11 | 4 | -0.1667 | 0.7463 | 4.833 | 0 | 0 |
| LOYO | P1-B1 | 12 | 12 | 0 | 8.417 | 10.05 | 9.5 | -0.4167 | 0.2531 | 8.417 | 3.583 | -74.14 |
| LOYO | P1-D1 | 12 | 12 | 0 | 6.25 | 6.886 | 6.5 | 0.25 | 0.6979 | 6.25 | 1.417 | -29.31 |
| LOYO | P1-D2 | 12 | 10 | 2 | 72.42 | 149.8 | 16.5 | -0.3 | 0.3853 | 13.9 | 67.58 | -1398 |
| LOYO | P1-H1 | 12 | 12 | 0 | 11.25 | 12.85 | 11.5 | -2.083 | 0.4356 | 11.25 | 6.417 | -132.8 |
| LOYO | P1-H2 | 12 | 12 | 0 | 12.25 | 14.42 | 12 | 1.417 | 0.315 | 12.25 | 7.417 | -153.4 |
| LOYO | P1-H3 | 12 | 12 | 0 | 6.75 | 8.088 | 6.5 | 0.75 | 0.6678 | 6.75 | 1.917 | -39.66 |

## 前向滚动

| validation | model_id | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days | delta_MAE_days | relative_MAE_reduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rolling | P1-B0 | 6 | 6 | 0 | 7.333 | 8.145 | 7.5 | -3.333 | 0.5374 | 7.333 | 0 | 0 |
| rolling | P1-B1 | 6 | 6 | 0 | 12 | 12.17 | 12.5 | -5.667 | 0.1213 | 12 | 4.667 | -63.64 |
| rolling | P1-D1 | 6 | 6 | 0 | 13.83 | 20.05 | 8 | 11.5 | 0.5218 | 13.83 | 6.5 | -88.64 |
| rolling | P1-D2 | 6 | 4 | 2 | 131.3 | 211.2 | 23 | 3 | 0.9487 | 14.5 | 124 | -1691 |
| rolling | P1-H1 | 6 | 6 | 0 | 10.5 | 11.39 | 12 | 6.5 | 0.6667 | 10.5 | 3.167 | -43.18 |
| rolling | P1-H2 | 6 | 6 | 0 | 10.5 | 12.05 | 10.5 | 3.833 | 0.7206 | 10.5 | 3.167 | -43.18 |
| rolling | P1-H3 | 6 | 6 | 0 | 8.167 | 8.935 | 7.5 | 3.833 | 0.7537 | 8.167 | 0.8333 | -11.36 |

## 稳定性与按年不确定性

| model_id | MAE_improvement_vs_B0_days | nonworse_loyo_years | best_improvement_holdout_year | improvement_without_best_year_days | fragile | rolling_delta_MAE_vs_B0_days | selected_specs_across_loyo | parameter_validity_check_pass | stable_superiority | improvement_cluster_bootstrap_95_low_days | improvement_cluster_bootstrap_95_high_days | uncertainty_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1-B0 | 0 | 5 | 2022 | 0 | False | 0 | 1 | True | False | 0 | 0 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P1-B1 | -3.583 | 1 | 2023 | -4.889 | False | 4.667 | 1 | True | False | -6 | -1.286 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P1-D1 | -1.417 | 1 | 2024 | -3.333 | False | 6.5 | 1 | True | False | -4.3 | 1.929 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P1-D2 | -67.58 | 1 | 2024 | -90.89 | False | 124 | 2 | True | False | -216.6 | -3.933 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P1-H1 | -6.417 | 1 | 2024 | -8.889 | False | 3.167 | 2 | True | False | -12.8 | -1.4 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P1-H2 | -7.417 | 1 | 2024 | -11.44 | False | 3.167 | 1 | True | False | -13.73 | -0.1429 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P1-H3 | -1.917 | 1 | 2024 | -3.778 | False | 0.8333 | 2 | True | False | -5.444 | 1.25 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |

stable_superiority需同时满足：汇总MAE更低、至少3个留出年不差、去掉最佳改善年仍更好、rolling方向不冲突、参数检查通过。表中最小误差只是候选集合内的最小值，不是额外独立验证后的赢家。五个年份自助区间仅为描述性不确定性。

小时指标从实际起点00:00按每小时温度计算，再聚合每日响应；这保持了首次越阈值日期，不能将日精度物候评价解释成小时精度实测。历史B0沿用同园训练持续天数中位数。累计到6月30日仍未达阈值，日期为NA且计预注册365天失败惩罚，未丢弃失败样本。

本任务的单阶段预测以已观测阶段起点为输入。W3将另行使用预测起点串联；不能把条件单阶段误差直接当完整链式误差。天气是事后ERA5再分析，不是当时可获得的未来天气预报。果园与品种混杂，不能据此作独立品种生理阈值比较。

## 办内2025早期物候敏感性

| model_id | main_n | including_early_n | main_MAE_days | same_main_sample_sensitivity_MAE_days | all_sensitivity_MAE_days |
| --- | --- | --- | --- | --- | --- |
| P1-B0 | 12 | 13 | 4.833 | 6.333 | 6.769 |
| P1-B1 | 12 | 13 | 8.417 | 9.917 | 10.08 |
| P1-D1 | 12 | 13 | 6.25 | 9.833 | 9.769 |
| P1-D2 | 12 | 13 | 72.42 | 74.83 | 70.77 |
| P1-H1 | 12 | 13 | 11.25 | 7.917 | 8.385 |
| P1-H2 | 12 | 13 | 12.25 | 72.5 | 68.54 |
| P1-H3 | 12 | 13 | 6.75 | 7.083 | 7.692 |

仅增加早期物候，未将零产量加入正常产量拟合；共同12个样本与全部13个样本的误差分开报告。
