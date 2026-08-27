# 实验继续执行结果：跨年日期已修复，完成日历基线

## 1. 完整P1/P2/P3样本

| 任务 | 全部完整日期对 | 主分析完整日期对 | 完整日温度样本 | 状态 |
| --- | --- | --- | --- | --- |
| P1 | 14 | 12 | 0 | baseline_only |
| P2 | 13 | 12 | 0 | baseline_only |
| P3 | 13 | 12 | 0 | baseline_only |

## 2. 正常产量独立样本

原始15个果园—产季，14个非零亩产，保守正常候选12个（5年）；固定绝收1个，红明损伤待核实2个。45个类别行不是45个独立环境样本。

## 3. 2025办内物候处理

主分析排除，仅将其可用早期P1纳入日历基线敏感性。不是普通正常物候样本。具体台风日期未知，年度资料已记载诱导/抽穗受损状态。

## 4. P1预测目标、基线与LOYO

目标是秋梢成熟之后的抽穗完整日期。气象最佳模型未产生；下面只报告天气独立的历史基线：

| model_id | n | MAE_days | RMSE_days | mean_bias_days | Spearman_r |
| --- | --- | --- | --- | --- | --- |
| P1-B0 | 12 | 4.833 | 6.11 | -0.1667 | 0.7463 |
| P1-B1 | 12 | 8.417 | 10.05 | -0.4167 | 0.2531 |
| P2-B0 | 12 | 6.75 | 7.544 | 0.5833 | 0.8787 |
| P3-B0 | 12 | 4.917 | 6.238 | 1.25 | 0.6829 |

## 5. P2/P3是否稳定可预测

在同一保守主分析集合上，P1-B0 MAE=4.83天，P2-B0=6.75天，P3-B0=4.92天。P2历史持续天数基线的误差较大；P1和P3误差相近。这里只能比较本次历史基线误差，不能据此判定气象预测稳定或可部署。 没有可用完整天气去验证GDD模型。见逐模型、逐折表，不能只看汇总相关。

## 6. 非线性温度是否优于低温日数

未检验，缺少从真实秋梢起点开始的连续天气。

## 7. 水分增益

未检验；降水也不能代表未知灌溉/土壤水分。

## 8. W2是否优于W1

已得到66个W2日期边界，但完整天气特征0个，未进行预测优劣比较。

## 9. W3是否优于W1

未检验；W3尚未构建，不把日历基线当作已验证气象模型。

## 10. 正常产量是否优于历史均值

尚不可评估；样本数量够最低门槛，天气特征仍不完整。

## 11. 预测物候能否改善产量

未检验。

## 12. 2025办内基线和损失参照

实际=0 kg/亩，正常生产基线及预测区间、差额全部NA，没有获准正常产量模型。

## 13. 暖冬/秋梢推迟影响多少天

未运行，不能给出0或其他模拟数值。

## 14. 当前证据等级

用户确认已解除A39与日期归年阻塞；当前支持报告**回顾性的历史日历基线**，尚不支持气象驱动物候/正常产量预测结论。核心H1—H3未检验，不能据此否定假设。LOYO仅5年，未提供可靠预测区间。

## 15. 下一步数据需求

优先补齐每个P1实际秋梢日开始的8—9月逐日天气，以及2月至采收的连续天气。精确区间见 `results/qc/weather_missing_by_transition.csv`。再核对陵水31条温度顺序异常及其他天气QC项、红明损伤恢复资格、缺失物候与测产类别。A39和年度归年无需再次确认。

## 执行记录

147个完整日期均按A列产季授权重建，月日不改。2022办内2021-09-25至2022-01-20为117天；原始11文件哈希未变。补充规则见 `experiments_guide/2026-08-27_USER_CLARIFICATION.md`。

| experiment_id | status | reason |
| --- | --- | --- |
| QC-0 | executed | standardization_and_data_gate |
| DESC-Y | executed | raw_yield_description |
| DESC-W | executed | weather_coverage_description |
| W1-QC | executed | fixed_window_coverage_audit |
| W2-QC | executed | normalized_observed_stage_boundaries_and_weather_coverage |
| TYPHOON-DESC | executed | source_evidence_and_zero_vs_NA_coding |
| P1-B0 | executed | weather_independent_LOYO_baselines_only |
| P1-B1 | executed | weather_independent_LOYO_baselines_only |
| P2-B0 | executed | weather_independent_LOYO_baselines_only |
| P3-B0 | executed | weather_independent_LOYO_baselines_only |
| PHENO-TYPHOON-SENSITIVITY | executed | weather_independent_LOYO_baselines_only |
| W2 | partial | date_windows_available_but_stage_weather_incomplete |
| P1-B2 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P1-M1 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P1-M2 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P1-M3 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P1-M4 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P2-M1 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P2-M2 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P3-M1 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P3-M2 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| P1-white-tip | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| W3 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| Y-B0 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| Y-B1 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| Y-W1 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| Y-W2 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| Y-W3 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| Y-W3P | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| Y-PREV | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| Y-DEC | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| TYPHOON-BASELINE | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| TYPHOON-INCLUSION | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| S1 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| S2 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| S3 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |
| S4 | blocked | continuous_stage_weather_unavailable_or_required_weather_model_not_validated |

运行 `python -m src.cli all --config configs/base.yaml` 可重建当前允许阶段；尚有天气阻塞时返回退出码2。`python scripts/verify.py` 记录真实pytest与重复重建结果。阶段0先单独提交，然后执行允许的基线。

主要产物：`data/processed/phenology_event_long.csv`、`results/qc/phenology_date_normalization.csv`、`results/phenology/P1_cv_predictions.csv`、`results/windows/observed_dynamic_features.csv`、`results/figures/`。
