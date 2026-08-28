# P2/P3：分阶段证据而非整链成功

## P2

| validation | model_id | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days | delta_MAE_days | relative_MAE_reduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LOYO | P2-B0 | 12 | 12 | 0 | 6.75 | 7.544 | 6 | 0.5833 | 0.8787 | 6.75 | 0 | 0 |
| LOYO | P2-M1 | 12 | 12 | 0 | 5.083 | 7.159 | 3 | 1.417 | 0.8841 | 5.083 | -1.667 | 24.69 |
| LOYO | P2-M2 | 12 | 12 | 0 | 5.167 | 7.106 | 3.5 | 1.667 | 0.9002 | 5.167 | -1.583 | 23.46 |
| rolling | P2-B0 | 6 | 6 | 0 | 8.667 | 9.434 | 9 | 6 | 0.871 | 8.667 | 0 | 0 |
| rolling | P2-M1 | 6 | 6 | 0 | 7.167 | 8.935 | 6 | 4.5 | 0.6983 | 7.167 | -1.5 | 17.31 |
| rolling | P2-M2 | 6 | 6 | 0 | 7.167 | 8.935 | 6 | 4.5 | 0.6983 | 7.167 | -1.5 | 17.31 |

| model_id | MAE_improvement_vs_B0_days | nonworse_loyo_years | best_improvement_holdout_year | improvement_without_best_year_days | fragile | rolling_delta_MAE_vs_B0_days | selected_specs_across_loyo | parameter_validity_check_pass | stable_superiority | improvement_cluster_bootstrap_95_low_days | improvement_cluster_bootstrap_95_high_days | uncertainty_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P2-B0 | 0 | 5 | 2022 | 0 | False | 0 | 1 | True | False | 0 | 0 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P2-M1 | 1.667 | 4 | 2024 | 1.222 | False | -1.5 | 2 | True | True | -0.125 | 2.643 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P2-M2 | 1.583 | 4 | 2024 | 1.111 | False | -1.5 | 3 | True | True | -0.125 | 2.643 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |

## P3

| validation | model_id | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days | delta_MAE_days | relative_MAE_reduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LOYO | P3-B0 | 12 | 12 | 0 | 4.917 | 6.238 | 4 | 1.25 | 0.6829 | 4.917 | 0 | 0 |
| LOYO | P3-M1 | 12 | 12 | 0 | 4.833 | 6.124 | 5 | 1 | 0.7165 | 4.833 | -0.08333 | 1.695 |
| LOYO | P3-M2 | 12 | 12 | 0 | 6.5 | 7.958 | 6 | 2.833 | 0.5729 | 6.5 | 1.583 | -32.2 |
| rolling | P3-B0 | 6 | 6 | 0 | 6 | 7.506 | 5.5 | 2.333 | 0.5508 | 6 | 0 | 0 |
| rolling | P3-M1 | 6 | 6 | 0 | 5.5 | 6.57 | 5.5 | -0.8333 | 0.5429 | 5.5 | -0.5 | 8.333 |
| rolling | P3-M2 | 6 | 6 | 0 | 6.333 | 6.976 | 7 | 1 | 0.4857 | 6.333 | 0.3333 | -5.556 |

| model_id | MAE_improvement_vs_B0_days | nonworse_loyo_years | best_improvement_holdout_year | improvement_without_best_year_days | fragile | rolling_delta_MAE_vs_B0_days | selected_specs_across_loyo | parameter_validity_check_pass | stable_superiority | improvement_cluster_bootstrap_95_low_days | improvement_cluster_bootstrap_95_high_days | uncertainty_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P3-B0 | 0 | 5 | 2022 | 0 | False | 0 | 1 | True | False | 0 | 0 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P3-M1 | 0.08333 | 2 | 2024 | -0.8889 | True | -0.5 | 1 | True | False | -1.667 | 1.8 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |
| P3-M2 | -1.583 | 1 | 2024 | -2.667 | False | 0.3333 | 4 | True | False | -4.1 | 0.6429 | five_year_descriptive_cluster_bootstrap_not_independent_external_validation |

P2日热量模型若通过稳定性门槛，可进入对应条件情景；不将轻微汇总误差改善自动等同于稳健优越性。P3若改善依赖单一年份则保留负结果。R4日/小时数据为事后天气，不是业务天气预报。
