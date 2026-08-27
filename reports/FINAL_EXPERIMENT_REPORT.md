# V2实验执行结果：完成阶段0，建模按闸门停止

## 1. P1/P2/P3完整样本

| 任务 | 原始端点成对记录 | 通过日期审计 | 正常主分析完整转换 | 气象完整可建模样本 | 状态 |
| --- | --- | --- | --- | --- | --- |
| P1 | 14 | 0 | 0 | 0 | blocked |
| P2 | 13 | 0 | 0 | 0 | blocked |
| P3 | 13 | 0 | 0 | 0 | blocked |

## 2. 正常产年独立产量样本

15个原始果园—产季，14个非零亩产记录；扣除年份冲突及其他损伤待核实记录后，10个保守正常候选样本。固定灾害样本1个。45个类别行不是45个独立样本。

## 3. 2025办内是否进主物候分析

不进入。年度资料记载受损枝梢及弱树势已影响诱导/抽穗过程。确切台风日期不明。仅保留敏感性资格，日期未通过故敏感性本轮也不运行。

## 4. P1目标、最佳模型和LOYO误差

目标是秋梢老熟之后的抽穗完整日期。最佳模型与LOYO误差NA：Stop 1，未拟合，不能把未运行写为性能差或误差0。

## 5. P2/P3是否稳定可预测

尚不可评估：日期及2月后气象不足。

## 6. 非线性是否优于低温日数

未检验。

## 7. 水分调节增益

未检验；降雨并不能替代未知灌溉/土壤水分。

## 8. W2是否优于W1

未检验。W1仅完成覆盖审计，W2未构建。

## 9. W3是否优于W1

未检验。没有LOYO物候预测，未构建W3。

## 10. 正常产量是否优于历史均值

未检验。样本数量是必要条件，不足以跨过日期、年份及完整天气闸门。

## 11. 加入预测物候是否改善产量

未检验。

## 12. 2025办内正常基线、区间和差额

实际=0 kg/亩；正常基线、预测区间、绝对/相对差全部NA（无获准正常模型）。不得解释为已识别的台风因果损失。

## 13. 暖冬和秋梢推迟改变多少天

NA；S1—S4未运行。

## 14. 当前证据等级

**当前数据尚不支持可验证预测结论（数据闸门阻塞），不能据此否定研究假设。** 也未拟合关联模型。所有原始文件哈希与快照一致；`测产.xlsx!A39`原样为2026，方案锁定2025仍需确认。

## 15. 最应补充/确认的观测

1. 先修订为真实完整日期，尤其秋梢老熟的前一年，以及每一历史产季的抽穗/盛花/成熟年份；不要只改显示格式。提供红明2026缺失物候及各事件定义。
2. 确认A39到底对应2025还是2026；若是2025，确认各区块调查批次/小区。核对类别均值和缺测类别。
3. 补齐至少2021年秋至2026年采收期连续逐日天气（尤其每年2—9月），核对陵水异常温度，不自动交换最高/最低列。
4. 提供办内台风日期、损毁比例、管理放弃投产说明；确认红明2025/2026是否满足正常年定义。记录后续恢复年份和灌溉/药物调花管理。
5. 下一年度持续记录秋梢成熟、露白点、抽穗、盛花、成熟的标准定义/重复观察；增加真正独立果园—年份、产量实际称重和果数，提供官方站号及园站距离。

## 执行状态清单

| experiment_id | status | reason |
| --- | --- | --- |
| QC-0 | executed | standardization_and_data_gate |
| DESC-Y | executed | raw_yield_description |
| DESC-W | executed | weather_coverage_description |
| W1-QC | executed | fixed_window_coverage_audit |
| TYPHOON-DESC | executed | source_evidence_and_zero_vs_NA_coding |
| P1-B0 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P1-B1 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P1-B2 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P1-M1 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P1-M2 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P1-M3 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P1-M4 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P2-B0 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P2-M1 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P2-M2 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P3-B0 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P3-M1 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P3-M2 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| P1-white-tip | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| W2 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| W3 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| Y-B0 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| Y-B1 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| Y-W1 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| Y-W2 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| Y-W3 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| Y-W3P | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| Y-PREV | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| Y-DEC | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| TYPHOON-BASELINE | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| TYPHOON-INCLUSION | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| PHENO-TYPHOON-SENSITIVITY | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| S1 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| S2 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| S3 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |
| S4 | blocked | Stop 1 / unresolved chronology / incomplete weather; not fitted |

## 重建与测试

`python -m src.cli all --config configs/base.yaml` 重建当前输入允许的审计和非模型描述；遇到数据闸门按约定退出码2，输出blocked报告，不运行后续模型。

`python -m pytest -q -ra` 执行安全性和数据处理测试。A39=2025约束应显示明确的预期失败（xfail），不能冒充满足；尚未实现/运行的模型专属测试明确skip。实际运行结果见 `results/logs/verification.json`。

代码范围为阶段0和非模型描述；阶段0已作为独立提交保存。数据修订并确认新输入快照后，须先重新审计，再实现允许的后续模型，不能仅通过改闸门数值强行运行。

主要结果：`results/qc/analysis_gate.json`、`reports/00_DATA_FEASIBILITY_REPORT.md`、`results/qc/phenology_date_review.csv`、`results/qc/source_block_review.csv`、`results/qc/weather_coverage_by_orchard_season.csv`、`results/figures/`。
