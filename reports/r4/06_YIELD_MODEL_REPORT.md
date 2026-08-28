# 正常产量：相同算法、分区重建特征

正常主样本12个、5年；办内2025和红明2025/2026不入主训练。主目标kg/亩，树类行不是独立样本。

## 主LOYO比较

| cohort | validation | model_id | status | n_predictions | MAE_kg_mu | RMSE_kg_mu | median_AE_kg_mu | mean_bias_kg_mu | Spearman_r | normalized_MAE | negative_predictions | baseline_MAE_same_seasons_kg_mu | delta_MAE_same_seasons_kg_mu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAIN | LOYO | Y-B0 | complete | 12 | 493.4 | 630.1 | 369.3 | -13.75 | -0.6454 | 0.4491 | 0 | 493.4 | 0 |
| MAIN | LOYO | Y-W1C | complete | 12 | 465.8 | 560.9 | 366.7 | 31.75 | -0.3678 | 0.424 | 0 | 493.4 | -27.6 |
| MAIN | LOYO | Y-W1M | complete | 12 | 471 | 622.6 | 347.2 | -16.98 | -0.4694 | 0.4287 | 0 | 493.4 | -22.43 |
| MAIN | LOYO | Y-W2O | complete | 12 | 515.8 | 646.8 | 367.4 | -80.04 | -0.711 | 0.4694 | 0 | 493.4 | 22.31 |
| MAIN | LOYO | Y-W3P | partial_not_matched_main | 8 | 431.3 | 525.2 | 346.8 | 222.6 | -0.5952 | 0.4605 | 0 | 445.9 | -14.59 |
| MAIN | LOYO | Y-W3P+PHENO | partial_not_matched_main | 8 | 433.7 | 526 | 350.1 | 221.3 | -0.5952 | 0.463 | 0 | 445.9 | -12.24 |

partial_not_matched_main的模型只保留审计记录，不可拿其子集误差与完整主样本比较。未达阈值或缺物候造成特征不可用时，不填真实未来日期、不插补。

## 产量验证闸门

{
  "formal_yield_comparison_complete": false,
  "Y_W3P_success": false,
  "checks": {},
  "reasons": [
    "one_or_more_required_models_lack_complete_nested_partitions"
  ],
  "forecast_scope": "conditional_on_realized_reanalysis_weather; not operational forecast",
  "normal_eligible_seasons": 12,
  "normal_eligible_years": 5,
  "sample_gate_pass": true
}

所有Ridge共用训练均值/标准差缩放与同一alpha网格；每次内层按年验证重新生成窗口。W3训练行还会排除自身产季的物候校准数据。最多六个连续指标+果园编码；PHENO扩展用四个天气指标+两个预测日期。负预测不截断，单独计数，不能解释为可部署生产值。

## 前向滚动和恢复样本敏感性

| cohort | validation | model_id | status | n_predictions | MAE_kg_mu | RMSE_kg_mu | median_AE_kg_mu | mean_bias_kg_mu | Spearman_r | normalized_MAE | negative_predictions | baseline_MAE_same_seasons_kg_mu | delta_MAE_same_seasons_kg_mu |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAIN | rolling | Y-B0 | complete | 6 | 422.7 | 560.2 | 263 | 228.3 | -0.9276 | 0.4552 | 0 | 422.7 | 0 |
| MAIN | rolling | Y-W1C | complete | 6 | 442.9 | 560.1 | 278.7 | 208 | -0.8117 | 0.4769 | 0 | 422.7 | 20.18 |
| MAIN | rolling | Y-W1M | complete | 6 | 394.2 | 541.9 | 197.6 | 292.6 | -0.2319 | 0.4246 | 0 | 422.7 | -28.47 |
| MAIN | rolling | Y-W2O | complete | 6 | 410.1 | 546.9 | 238.5 | 238.9 | -0.7247 | 0.4416 | 0 | 422.7 | -12.62 |
| MAIN | rolling | Y-W3P | partial_not_matched_main | 3 | 171.9 | 178.1 | 155.5 | -171.9 | 0 | 0.1387 | 0 | 194.5 | -22.55 |
| MAIN | rolling | Y-W3P+PHENO | partial_not_matched_main | 3 | 186.7 | 191.3 | 186.9 | -186.7 | 0 | 0.1506 | 0 | 194.5 | -7.799 |
| SENS-HM25 | LOYO | Y-B0 | complete | 13 | 444.7 | 547.6 | 316.2 | -67.14 | -0.08357 | 0.424 | 0 | 444.7 | 0 |
| SENS-HM25 | LOYO | Y-W1C | complete | 13 | 516.4 | 657.7 | 461.3 | -73.95 | -0.4429 | 0.4923 | 0 | 444.7 | 71.68 |
| SENS-HM25 | LOYO | Y-W1M | complete | 13 | 478.6 | 611.3 | 293.2 | -54.76 | -0.4484 | 0.4564 | 0 | 444.7 | 33.96 |
| SENS-HM25 | LOYO | Y-W2O | complete | 13 | 508.3 | 635.9 | 449.3 | -93.5 | -0.5337 | 0.4846 | 0 | 444.7 | 63.62 |
| SENS-HM25 | LOYO | Y-W3P | partial_not_matched_main | 8 | 401 | 478.7 | 294.1 | 145.2 | -0.3571 | 0.4281 | 0 | 392.9 | 8.12 |
| SENS-HM25 | LOYO | Y-W3P+PHENO | partial_not_matched_main | 8 | 409.2 | 495.1 | 339.5 | 24.97 | -0.2143 | 0.4369 | 0 | 392.9 | 16.32 |
| SENS-HM25-26 | LOYO | Y-B0 | complete | 14 | 401.8 | 497.4 | 316.2 | -51.74 | 0 | 0.3911 | 0 | 401.8 | 0 |
| SENS-HM25-26 | LOYO | Y-W1C | complete | 14 | 455.8 | 528.7 | 475.5 | -55.22 | -0.2464 | 0.4436 | 0 | 401.8 | 53.95 |
| SENS-HM25-26 | LOYO | Y-W1M | complete | 14 | 452.1 | 582.1 | 278.4 | -48.31 | -0.3124 | 0.44 | 0 | 401.8 | 50.22 |
| SENS-HM25-26 | LOYO | Y-W2O | blocked | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| SENS-HM25-26 | LOYO | Y-W3P | blocked | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| SENS-HM25-26 | LOYO | Y-W3P+PHENO | blocked | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| SENS-HM26 | LOYO | Y-B0 | complete | 13 | 375.4 | 479.6 | 316.2 | -44.05 | -0.1337 | 0.3502 | 0 | 375.4 | 0 |
| SENS-HM26 | LOYO | Y-W1C | complete | 13 | 388.6 | 480.9 | 315.3 | -21.86 | -0.1761 | 0.3625 | 0 | 375.4 | 13.16 |
| SENS-HM26 | LOYO | Y-W1M | complete | 13 | 438.8 | 584.7 | 298 | -14.25 | -0.3906 | 0.4093 | 0 | 375.4 | 63.33 |
| SENS-HM26 | LOYO | Y-W2O | blocked | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| SENS-HM26 | LOYO | Y-W3P | blocked | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| SENS-HM26 | LOYO | Y-W3P+PHENO | blocked | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA |

滚动早期仅两训练年时，W3在内层的再交叉拟合可能没有历史，须标blocked而非用未来年补齐。红明2026没有定量物候，W2/W3敏感性可能被缺日期阻止，必须与可执行的固定窗口敏感性分开解读。恢复敏感性仅增加相应产量行，主物候校准资格不偷偷改变。2025办内绝收始终排除。

窗口优劣只能看共同完整样本的held-out误差；W2是回顾性上限。即使W3优于基线，输入仍是已实现ERA5天气，只支持条件预测，不等于实际发行日拥有未来天气预报。次级/代理目标只报告完整度，未新增一轮自动模型搜索。
