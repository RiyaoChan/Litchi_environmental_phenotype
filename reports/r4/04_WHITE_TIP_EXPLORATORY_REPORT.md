# 露白辅助任务：exploratory_only

| task | validation | n_samples | n_predictions | n_unreached_or_invalid | MAE_days | RMSE_days | median_AE_days | mean_bias_days | Spearman_r | MAE_valid_only_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1A | LOYO | 12 | 12 | 0 | 7.917 | 9.482 | 8 | -0.4167 | 0.08541 | 7.917 |
| P1A | rolling | 6 | 6 | 0 | 8.833 | 9.687 | 8.5 | -4.167 | 0 | 8.833 |
| P1B | LOYO | 12 | 12 | 0 | 5.333 | 6.506 | 5.5 | -0.5 | 0.6761 | 5.333 |
| P1B | rolling | 6 | 6 | 0 | 6.333 | 7.047 | 6 | 1 | 0.6471 | 6.333 |

两段各有12个主分析完整日期对。沿用同一露白字段，但没有独立组织学花芽分化观测，不能把露白直接等同于真实诱导终点。P1主气象模型未稳定优于历史规律，所以仅运行两段历史持续天数基线，不再搜索新的温度响应，不阻塞P2/P3。
