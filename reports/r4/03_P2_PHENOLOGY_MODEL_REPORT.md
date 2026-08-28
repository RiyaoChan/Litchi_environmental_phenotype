# P2：嵌套按年验证与前向滚动

主分析12个果园—产季，5年；同任务所有模型使用相同测试样本。每折内选择候选温度/形状，事件累计阈值只用训练样本。扩展进入条件：True。

## LOYO留出预测

| validation | model_id | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days | delta_MAE_days | relative_MAE_reduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LOYO | P2-B0 | 12 | 12 | 0 | 6.75 | 7.544 | 6 | 0.5833 | 0.8787 | 6.75 | 0 | 0 |
| LOYO | P2-M1 | 12 | 12 | 0 | 5.083 | 7.159 | 3 | 1.417 | 0.8841 | 5.083 | -1.667 | 24.69 |
| LOYO | P2-M2 | 12 | 12 | 0 | 5.167 | 7.106 | 3.5 | 1.667 | 0.9002 | 5.167 | -1.583 | 23.46 |

## 前向滚动

| validation | model_id | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days | delta_MAE_days | relative_MAE_reduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rolling | P2-B0 | 6 | 6 | 0 | 8.667 | 9.434 | 9 | 6 | 0.871 | 8.667 | 0 | 0 |
| rolling | P2-M1 | 6 | 6 | 0 | 7.167 | 8.935 | 6 | 4.5 | 0.6983 | 7.167 | -1.5 | 17.31 |
| rolling | P2-M2 | 6 | 6 | 0 | 7.167 | 8.935 | 6 | 4.5 | 0.6983 | 7.167 | -1.5 | 17.31 |

## 稳定性与按年不确定性

| model_id | MAE_improvement_vs_B0_days | nonworse_loyo_years | best_improvement_holdout_year | improvement_without_best_year_days | fragile | rolling_delta_MAE_vs_B0_days | selected_specs_across_loyo | parameter_validity_check_pass | stable_superiority | improvement_cluster_bootstrap_95_low_days | improvement_cluster_bootstrap_95_high_days | uncertainty_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P2-B0 | 0 | 5 | 2022 | 0 | False | 0 | 1 | True | False | 0 | 0 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P2-M1 | 1.667 | 4 | 2024 | 1.222 | False | -1.5 | 2 | True | True | -0.125 | 2.643 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P2-M2 | 1.583 | 4 | 2024 | 1.111 | False | -1.5 | 3 | True | True | -0.125 | 2.643 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |

stable_superiority需同时满足：汇总MAE更低、至少3个留出年不差、去掉最佳改善年仍更好、rolling方向不冲突、参数检查通过。表中最小误差只是候选集合内的最小值，不是额外独立验证后的赢家。五个年份自助区间仅为描述性不确定性。

小时指标从实际起点00:00按每小时温度计算，再聚合每日响应；这保持了首次越阈值日期，不能将日精度物候评价解释成小时精度实测。历史B0沿用同园训练持续天数中位数。累计到6月30日仍未达阈值，日期为NA且计预注册365天失败惩罚，未丢弃失败样本。

本任务的单阶段预测以已观测阶段起点为输入。W3将另行使用预测起点串联；不能把条件单阶段误差直接当完整链式误差。天气是事后ERA5再分析，不是当时可获得的未来天气预报。果园与品种混杂，不能据此作独立品种生理阈值比较。
