# P3：嵌套按年验证与前向滚动

主分析12个果园—产季，5年；同任务所有模型使用相同测试样本。每折内选择候选温度/形状，事件累计阈值只用训练样本。扩展进入条件：True。

## LOYO留出预测

| validation | model_id | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days | delta_MAE_days | relative_MAE_reduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LOYO | P3-B0 | 12 | 12 | 0 | 4.917 | 6.238 | 4 | 1.25 | 0.6829 | 4.917 | 0 | 0 |
| LOYO | P3-M1 | 12 | 12 | 0 | 4.833 | 6.124 | 5 | 1 | 0.7165 | 4.833 | -0.08333 | 1.695 |
| LOYO | P3-M2 | 12 | 12 | 0 | 6.5 | 7.958 | 6 | 2.833 | 0.5729 | 6.5 | 1.583 | -32.2 |

## 前向滚动

| validation | model_id | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days | delta_MAE_days | relative_MAE_reduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rolling | P3-B0 | 6 | 6 | 0 | 6 | 7.506 | 5.5 | 2.333 | 0.5508 | 6 | 0 | 0 |
| rolling | P3-M1 | 6 | 6 | 0 | 5.5 | 6.57 | 5.5 | -0.8333 | 0.5429 | 5.5 | -0.5 | 8.333 |
| rolling | P3-M2 | 6 | 6 | 0 | 6.333 | 6.976 | 7 | 1 | 0.4857 | 6.333 | 0.3333 | -5.556 |

## 稳定性与按年不确定性

| model_id | MAE_improvement_vs_B0_days | nonworse_loyo_years | best_improvement_holdout_year | improvement_without_best_year_days | fragile | rolling_delta_MAE_vs_B0_days | selected_specs_across_loyo | parameter_validity_check_pass | stable_superiority | improvement_cluster_bootstrap_95_low_days | improvement_cluster_bootstrap_95_high_days | uncertainty_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P3-B0 | 0 | 5 | 2022 | 0 | False | 0 | 1 | True | False | 0 | 0 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P3-M1 | 0.08333 | 2 | 2024 | -0.8889 | True | -0.5 | 1 | True | False | -1.667 | 1.8 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P3-M2 | -1.583 | 1 | 2024 | -2.667 | False | 0.3333 | 4 | True | False | -4.1 | 0.6429 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |

stable_superiority需同时满足：汇总MAE更低、至少3个留出年不差、去掉最佳改善年仍更好、rolling方向不冲突、参数检查通过。表中最小误差只是候选集合内的最小值，不是额外独立验证后的赢家。五个年份自助区间仅为描述性不确定性。

小时指标从实际起点00:00按每小时温度计算，再聚合每日响应；这保持了首次越阈值日期，不能将日精度物候评价解释成小时精度实测。历史B0沿用同园训练持续天数中位数。累计到6月30日仍未达阈值，日期为NA且计预注册365天失败惩罚，未丢弃失败样本。

本任务的单阶段预测以已观测阶段起点为输入。W3将另行使用预测起点串联；不能把条件单阶段误差直接当完整链式误差。天气是事后ERA5再分析，不是当时可获得的未来天气预报。果园与品种混杂，不能据此作独立品种生理阈值比较。
