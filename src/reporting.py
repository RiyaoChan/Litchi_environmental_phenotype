from __future__ import annotations

import pandas as pd


def markdown_table(df, columns=None, limit=None):
    if columns:
        df=df[columns]
    if limit:
        df=df.head(limit)
    if df.empty:
        return '无记录。'
    def fmt(v):
        if pd.isna(v): return 'NA'
        return str(v).replace('|',' / ').replace('\n',' ')
    lines=['| '+' | '.join(df.columns)+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    lines += ['| '+' | '.join(map(fmt,row))+' |' for row in df.itertuples(index=False,name=None)]
    return '\n'.join(lines)


def write_reports(root, gate, events, master, coverage, fixed, weather_issues, doc_evidence, transitions, status, numeric_matches):
    counts=gate['counts']
    count_table=pd.DataFrame([{'任务':t,'原始端点成对记录':v['raw_endpoint_pairs'],
                              '通过日期审计':v['validated_date_pairs'],
                              '正常主分析完整转换':v['main_complete_pairs'],
                              '气象完整可建模样本':v['weather_complete_model_samples'],
                              '状态':v['status']} for t,v in gate['phenology'].items()])
    pheno_count=markdown_table(count_table)
    weather_short=coverage[['orchard_id','harvest_year','expected_days','observed_days','date_coverage_ratio','tmean_c_coverage_ratio']].copy()
    weather_short[['date_coverage_ratio','tmean_c_coverage_ratio']]=weather_short[['date_coverage_ratio','tmean_c_coverage_ratio']].round(4)
    blocks=master[['season_id','source_block_id','normal_production_year','typhoon_damage','yield_main_eligible','exclusion_reason']]
    text=f'''# 阶段0：数据标准化与可行性审计

## 结论

**执行状态：blocked（方案 Stop 1）。未拟合任何物候、产量或情景模型。**

本报告是本次审计的阶段性成果，不表示实验方案全部完成。原始 Excel/Word 文件按当前工作区快照冻结；未修改任何原始数值。当前 `测产.xlsx` 是用户修改后的版本（A39=2026），不是把该单元格自动改为2025。方案与实际输入冲突必须由用户确认。

## 数据量与独立单位

- 11 个正式原始文件：4 个 Excel、7 个 Word；根目录与示范园目录的 2026 Word 完全相同，按哈希识别，不能算两套样本。
- 物候：{counts['phenology_orchard_seasons']} 个果园—产季，2022—2026 共5个收获年份；{counts['phenology_event_slots']} 个事件槽位；{counts['unformatted_excel_serials']} 个未格式化日期序号。
- 测产：{counts['yield_class_rows']} 个 A/B/C 类别行、{counts['yield_source_blocks']} 个区块、{counts['yield_orchard_seasons']} 个独立果园—产季。三棵测产树和类别不是独立天气样本。
- 原始表中有 {counts['raw_nonzero_yield_seasons']} 个非零亩产记录；在排除固定灾害、年份冲突及其他结构损伤待核实记录后，{counts['normal_yield_eligible_seasons_before_weather_gate']} 个正常候选样本、年份 {counts['normal_eligible_years']}。这是**气象及全局闸门之前**的数量，不表示正式模型已获准。
- {counts['protocol_disaster_seasons']} 个方案定义的绝收样本；另有 {counts['other_damage_review_seasons']} 个红明产季的正常生产资格待核实。

上述标准化样本数来自两份主Excel；年度Word用于来源、管理与灾害证据审计。未把Word中的历史回顾表重复计入样本，也未从只有月日的Word表格猜年份扩充2021产季。

## 完整转换样本

{pheno_count}

“原始端点成对”仅表示两端有可解码数值，不表示年份、先后顺序或正常生理状态正确。未经日期确认的数值不会进入 `event_date`，仅保存到 `decoded_candidate_date`。

## 阻塞1：日期未正确准备

例如 `物候期.xlsx!Sheet1!E2=46290` 解码为 `2026-09-25`，但该行产季为2022；`G2=46042` 解码为 `2026-01-20`。2026办内的 `E14` 同样解码为 `2026-09-25`，晚于 `G14` 的 `2026-01-10`。代码没有推测正确年份，也没有用月日重新拼接。

日期规则：接受真实 Excel 日期类型或明确的 `YYYY-MM-DD` 完整日期文本。General 数值序号只做解码审计；即使用户确认序号表达日期，产季和阶段先后冲突仍需解决。正常允许跨年；谢花、坐果和生理落果的重叠只列入审计，不自动修正。

详见 `results/qc/phenology_date_review.csv`、`results/qc/transition_review.csv`、`results/qc/phenology_overlap_review.csv`。

## 阻塞2：A39 与预注册事实冲突

方案锁定 A39=2025，实际当前文件 A39={gate['a39']['actual_a39']}。保留真实输入和各自区块 ID，不合并、不删除、不把2026改回2025。当前标签下没有同果园—同年的重复区块；如果用户确认该组应归2025，则会形成三个重复果园—产季，必须进一步确认调查批次/小区或保守聚合。

2026 年 Word 的测产表包含与最后三个区块相符的数值线索（见 `results/qc/annual_source_numeric_matches.csv`），这支持核对2026来源，但不能擅自推翻用户指定方案的锁定事实。

## 阻塞3：日气象并非全年

按源文件“年、月、日”解析，不能按工作表名替代日期。两地主要覆盖每个产季上一年10月至当年1月；2—9月缺失，盛花和果实发育天气无法构建。无降水不等于缺测；不存在的风速保持NA。海口与陵水的湿度/日照列顺序不同，且陵水2026年列顺序改变，读取按表头映射。

下表分母固定为上一年10月1日至当年6月30日（两端包含）；不是单个真实物候窗口的覆盖率。主表的 `weather_coverage_ratio` 明确沿用这一参考窗口。

{markdown_table(weather_short)}

另发现 {len(weather_issues)} 条气象数值 QC 记录。温度不满足 Tmin≤Tmean≤Tmax 的记录不交换列名，原始值保留在原始列/中间表；处理表对应温度置NA并记录原因。降水、湿度和日照等独立字段仍按自身有效性保留。

## 地点、品种和共享天气

办内与红明共用海口地区气象序列；鲁宏使用陵水地区序列。`station_id` 是内部来源别名，不是已核实的官方站号，`source_station_code=NA`。地点和站点距离/代表性待核实。同地区两果园不能当作两个独立气象实现；年份是交叉验证分组单位。白糖罂仅红明一园，品种与果园效应混杂。

## 台风与正常年资格

2025办内：最终亩产按用户方案记0；未测单株产量、单果重、真实果数、果数代理全部NA；不进正常产量训练。年度资料明确描述受损枝梢、不整齐生长及弱树势，故早期物候不进主分析，仅保留敏感性资格。确切台风发生日期未给出，`typhoon_event_date=NA`；`2025-03-01` 是放弃投产决定日期，不能当作台风发生日期。

红明2025年度资料记载台风折枝，2026资料记载树冠仍在恢复。暂将两季正常状态设NA并排除候选主分析，而非新增已确认绝收样本；需用户定义其是否符合“正常生产条件”。

{markdown_table(blocks)}

## 测产核验

按类别株数对原表J列类别均值和单果重加权；有正株数但测量缺失的类别存在时，不把它填0，也不将剩余类别的均值冒充全园均值。报告 `weighted_mean_tree_coverage_ratio`。亩产使用原表K列，不擅自按种植密度重算。原始三棵树均值与J列不一致项列在 `results/qc/yield_class_mean_review.csv`，本轮不自动替换。

## 本次允许范围及停止规则

完成只读抽取、标准化、原始哈希冻结、数值/来源冲突审计、覆盖率和非模型描述。P1/P2/P3基线也不得利用错误日期运行；W2/W3、正式产量模型、灾害正常基线和情景均阻塞。没有生成虚构LOYO误差或模型预测区间。

先确认日期与 A39，再补充连续逐日气象，最后重新审计样本闸门。即使日期修好，P2/P3仍受2月以后气象缺失限制。
'''
    write=lambda name,value:(root/'reports'/name).write_text(value,encoding='utf-8')
    write('00_DATA_FEASIBILITY_REPORT.md',text)
    write('01_SOURCE_BLOCK_REVIEW.md',f'''# 测产区块与年份核对

原始行、合并单元格锚点及 `source_block_id` 均保留。当前A39=2026与方案=2025冲突；不自动改年、不删除或合并最后三个区块。当前标签下每个果园—产季只有一个区块，方案中所述同年多区块尚无法与当前文件对齐。

{markdown_table(master[['season_id','source_block_id','year_source_cell','year_protocol_conflict','final_yield_kg_per_mu']])}

## 年度Word数值对照（证据线索，不自动判定年份）

按同一Word表格行与Excel首个测产类别的三棵树数值匹配；不把文档副本视为独立证据。

{markdown_table(numeric_matches)}

请确认 A39 是方案旧版本中的笔误，还是本地工作簿与计划所指版本不同；如果确为2025，请进一步提供区块用途。所有验证将按整个产季分组，绝不把类别/调查树随机分入训练和测试。
''')
    write('01_PHENOLOGY_MODEL_REPORT.md',f'''# 物候模型报告（阻塞）

{pheno_count}

P1预测秋梢老熟后的抽穗完整日期；P2预测抽穗后的盛花日期；P3预测盛花后的成熟日期。由于Stop 1，所有拟合、历史中位数基线与LOYO均未执行。最佳模型、MAE、RMSE、bias、Spearman和区间覆盖均为NA（未运行），不是0。不能比较哪个任务最可预测、非线性响应或水分增益。包括/排除2025办内的物候敏感性也未运行。
''')
    write('02_DYNAMIC_WINDOW_REPORT.md','''# 动态气象窗口报告（阻塞）

W1只执行固定窗口覆盖审计；完整的诱导窗口可汇总，不完整窗口的阶段统计为NA。W2因真实完整物候日期未通过审计而阻塞；W3因无LOYO预测日期而阻塞。因此不存在W1/W2/W3的预测性能比较，也没有用全数据物候拟合构造W3。

窗口统计本轮未进入任何产量模型。即使以后使用W3，基于完整阶段实际天气的结果仍属于“给定后续天气”的条件预测；未提供天气预报或明确预测时点时，不能宣称提前生产部署性能。
''')
    write('03_YIELD_MODEL_REPORT.md',f'''# 正常产量模型报告（阻塞）

气象闸门前保守候选样本{counts['normal_yield_eligible_seasons_before_weather_gate']}个，覆盖{len(counts['normal_eligible_years'])}个收获年份。原表非零记录{counts['raw_nonzero_yield_seasons']}个不等于可训练样本数。A39和正常年定义存在待确认项；日期未通过，W2不可构建，2月后天气缺失。因此所有Y实验未运行，极简关联也暂不拟合，避免在未解决的年份基础上给出误导结果。

预测判据：未能评估，不是已经证明模型失败。没有训练/测试拆分或回归预处理被执行；R²、LOYO误差和区间覆盖均NA。
''')
    write('04_TYPHOON_CASE_REPORT.md',f'''# 2025年办内灾害案例（仅事实与资格审计）

实际最终亩产=0（用户方案确认）。未测单株产量、单果重、果数及后续物候保持NA。台风具体日期NA；年度报告记载2025-03-01决定放弃投产，该日期不能替代台风日期。

主物候分析排除2025办内；保留早期物候敏感性资格但未执行。正常产量拟合排除该季。由于正常模型未建成，“正常生产基线预测”、预测区间、绝对差和相对差均NA；包含/排除灾害的稳健回归敏感性也未运行。一个绝收样本不能训练通用灾害预测模型，不能把差额认定为已识别的因果效应。

## 年度资料原文线索

{markdown_table(doc_evidence)}
''')
    write('05_SCENARIO_REPORT.md','''# 情景推演报告（阻塞）

S1暖冬(+0.5/+1/+2℃)、S2秋梢推迟(+7/+14/+21天)、S3水分情景及S4产量情景全部未运行。没有通过验证的P1、水分模型或产量模型，故不输出抽穗偏移天数、产量变化或概率。也未执行模型重拟合式“情景”。
''')
    write('FINAL_EXPERIMENT_REPORT.md',f'''# V2实验执行结果：完成阶段0，建模按闸门停止

## 1. P1/P2/P3完整样本

{pheno_count}

## 2. 正常产年独立产量样本

15个原始果园—产季，14个非零亩产记录；扣除年份冲突及其他损伤待核实记录后，{counts['normal_yield_eligible_seasons_before_weather_gate']}个保守正常候选样本。固定灾害样本1个。45个类别行不是45个独立样本。

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

{markdown_table(status)}

## 重建与测试

`python -m src.cli all --config configs/base.yaml` 重建当前输入允许的审计和非模型描述；遇到数据闸门按约定退出码2，输出blocked报告，不运行后续模型。

`python -m pytest -q -ra` 执行安全性和数据处理测试。A39=2025约束应显示明确的预期失败（xfail），不能冒充满足；尚未实现/运行的模型专属测试明确skip。实际运行结果见 `results/logs/verification.json`。

代码范围为阶段0和非模型描述；阶段0已作为独立提交保存。数据修订并确认新输入快照后，须先重新审计，再实现允许的后续模型，不能仅通过改闸门数值强行运行。

主要结果：`results/qc/analysis_gate.json`、`reports/00_DATA_FEASIBILITY_REPORT.md`、`results/qc/phenology_date_review.csv`、`results/qc/source_block_review.csv`、`results/qc/weather_coverage_by_orchard_season.csv`、`results/figures/`。
''')
