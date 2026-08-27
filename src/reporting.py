"""Current reports generated from audit/results; historical decisions live in git."""
from __future__ import annotations
import pandas as pd


def markdown_table(df,columns=None,limit=None):
    if columns: df=df[columns]
    if limit: df=df.head(limit)
    if df.empty: return '无记录。'
    def fmt(value):
        if pd.isna(value): return 'NA'
        if isinstance(value,float): return f'{value:.4g}'
        return str(value).replace('|',' / ').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(df.columns)+' |','| '+' | '.join(['---']*len(df.columns))+' |']+
                      ['| '+' | '.join(map(fmt,row))+' |' for row in df.itertuples(index=False,name=None)])


def write_reports(root,gate,events,master,coverage,fixed,weather_issues,doc_evidence,transitions,status,numeric_matches,
                  dynamic,comparison=None):
    counts=gate['counts']
    tasks=pd.DataFrame([{'任务':task,'全部完整日期对':v['validated_date_pairs'],
                         '主分析完整日期对':v['main_complete_pairs'],'完整日温度样本':v['weather_complete_model_samples'],
                         '状态':v['status']} for task,v in gate['phenology'].items()])
    summary=markdown_table(tasks)
    baselines='本次仅运行阶段0；基线尚未执行。'
    sensitivity_summary='本次仅运行阶段0；敏感性基线尚未执行。'
    baseline_interpretation='尚未评估基线误差。'
    if comparison is not None:
        baselines=markdown_table(comparison[['model_id','n','MAE_days','RMSE_days','mean_bias_days','Spearman_r']])
        sensitivity_summary=markdown_table(pd.read_csv(root/'results/phenology/P1_typhoon_sensitivity.csv')[
            ['model_id','main_n','sensitivity_all_n','main_MAE_days','sensitivity_common_normal_MAE_days','sensitivity_all_MAE_days']])
        scores=comparison.set_index('model_id').MAE_days
        baseline_interpretation=(f'在同一保守主分析集合上，P1-B0 MAE={scores["P1-B0"]:.2f}天，'
            f'P2-B0={scores["P2-B0"]:.2f}天，P3-B0={scores["P3-B0"]:.2f}天。'
            'P2历史持续天数基线的误差较大；P1和P3误差相近。这里只能比较本次历史基线误差，不能据此判定气象预测稳定或可部署。')
    write=lambda name,text:(root/'reports'/name).write_text(text,encoding='utf-8')
    examples=events[events.source_cell.isin(['E2','F2','G2','E14','F13'])][['source_cell','harvest_year','event_name','decoded_candidate_date','event_date']]
    weather_short=coverage[['orchard_id','harvest_year','expected_days','observed_days','date_coverage_ratio','tmean_c_coverage_ratio']]
    stage_weather=transitions[transitions.complete_date_pair==1][['season_id','task','observed_start_date','observed_end_date','observed_duration_days','expected_days','observed_weather_days','missing_tmean_days']]
    normal_n=counts['normal_yield_eligible_seasons_before_weather_gate']
    weather_reasons='\n'.join('- '+reason for reason in gate['yield']['reasons'])
    write('00_DATA_FEASIBILITY_REPORT.md',f'''# 阶段0：用户确认后的重新审计

## 当前结论

**A39与跨年日期阻塞已解除；当前状态为partial，后续气象模型仍受连续天气覆盖限制。**

用户确认 `测产.xlsx!A39=2026`，且物候A列是产季年份。秋梢老熟属于上一年，冬春生殖事件按跨年周期归入该产季。前次对序号自带年份的阻塞是归年规则未获确认，不应理解为跨年物候本身错误。本次按用户授权只重建派生日期，11个原始文件哈希保持不变。

权威补充说明：`experiments_guide/2026-08-27_USER_CLARIFICATION.md`，优先于V2旧A39约束。

## 归年方法与示例

从原始序号/日期中提取月日，以A列产季Y归年：7—12月归Y−1，1—6月归Y；秋梢必须属于Y−1。7月1日是实现边界，当前无7月记录。原始解码日期仅作来源记录，不再当作实际物候年份。保留 `event_date`、`decoded_candidate_date`、`date_derivation`、`date_year_rebased` 和来源单元格。

{markdown_table(examples)}

2022办内P1为2021-09-25至2022-01-20，持续117天；逐日累计窗口两端包含，共118天。12月露白点归上一年，1月露白点归当年，不能把所有露白点统一减一年。保留月日，未为消除重叠而改动阶段日期。

## 标准化数量与独立单位

- 4个Excel、7个Word（2026根目录Word为同文件副本，共6个不同Word哈希）。
- {counts['phenology_orchard_seasons']}个物候果园—产季，{counts['phenology_event_slots']}个事件槽位；{counts['validated_event_dates']}个完整日期，其中{counts['dates_year_rebased']}个按A列重建了年份；其余为缺测或定性“轻微”。
- 测产{counts['yield_class_rows']}个类别行，{counts['yield_source_blocks']}个来源区块，{counts['yield_orchard_seasons']}个独立果园—产季。三棵树/类别/Word历史表不另算环境样本。
- 原表非零亩产{counts['raw_nonzero_yield_seasons']}个；保守正常候选{normal_n}个，年份{counts['normal_eligible_years']}；固定灾害1个，红明2025/2026仍因损伤恢复资格待确认而排除。

## 每个物候转换的完整样本

{summary}

日期完整与天气完整是不同条件。主分析排除2025办内及红明损伤待核实产季。P1/P2/P3可运行天气独立的历史基线；没有完整天气样本，不运行低温/GDD或非线性累积模型。

## 真实阶段的天气缺口

{markdown_table(stage_weather)}

原文件主要只有每年10月至次年1月。P1从实际8—9月秋梢成熟开始，缺少起始阶段天气；部分抽穗在2月1日还缺少末日。P2盛花在2—3月，P3成熟在4—5月，后段天气缺失。**不把P1起点强行截到10月1日，不补0、不插值、不拿别年天气替代。**

精确需要补齐的逐阶段区间：`results/qc/weather_missing_by_transition.csv`。注意缺测包含源表没有该日期，以及有该日期但对应变量无效两种情况。

## 固定参考窗口覆盖

下表仅是上一年10月1日至产季6月30日的参考窗口，两端包含，不代替上述实际阶段覆盖。

{markdown_table(weather_short)}

气象数值QC记录{len(weather_issues)}条；温度顺序不一致不自动交换列，异常温度置NA，原值留存；其他变量独立核验。海口两个园共用一条区域气象序列；鲁宏用陵水序列。station_id为内部来源别名，官方站号、园站距离仍未知。红明白糖罂与果园效应混杂。

## 测产与灾害

A39已确认2026，旧年份冲突不再排除2026办内与鲁宏。原表J列类别均值按株数加权；有正株数而均值缺测的类别不补0，不能只用其余类别冒充全园均值。亩产保留原表K列。J列与3棵测产树算术均值的不一致仍只列为核对项。

2025办内最终亩产=0，未测产量构成NA，主物候/正常产量排除；只对可用早期P1运行日历基线包含/排除敏感性。2025-03-01是放弃投产决定日，不是台风日期，台风具体日期仍NA。

## 下游闸门

{weather_reasons}

本次允许范围：标准化、日期/天气审计、真实时间轴、历史基线LOYO、W2实际边界及天气覆盖。W3、正式产量与暖冬等情景仍未获准。基线表现不等于验证了气象驱动物候模型。
''')
    write('01_SOURCE_BLOCK_REVIEW.md',f'''# 来源区块：A39已按用户确认解除冲突

当前A39=2026，与最新用户确认一致；V2写定2025的约束已被补充说明替代。未改Excel，也未删除/合并任何区块。目前每个果园—产季只有一个来源区块，不存在旧方案预期的2025多区块。2026 Word数值匹配是补充核对线索，不是擅自改年的依据。

{markdown_table(master[['season_id','source_block_id','year_source_cell','year_protocol_conflict','final_yield_kg_per_mu','yield_main_eligible']])}

## Word同一行三棵测产树数值匹配

{markdown_table(numeric_matches)}

树级类别与调查批次仍是嵌套观测，LOYO始终留出完整harvest_year。
''')
    write('01_PHENOLOGY_MODEL_REPORT.md',f'''# 物候历史基线及气象模型闸门

{summary}

P1目标：从秋梢成熟开始预测抽穗日期；P2：抽穗至盛花；P3：盛花至成熟。

## LOYO基线

{baselines}

{baseline_interpretation}

B0是训练年份内同果园的历史中位持续天数；P1-B1是训练年份内同果园的抽穗日期基线。中位数按半天向上取整到整天；缺少同园训练记录时回退到训练集总体中位数。实际起始事件是已观测输入。

每折留出该产季所有果园，拟合只用其他年份；每条预测保存training_years和fit_season_ids。LOYO是回顾验证，训练可包含留出年之后的年份，不等于按时间滚动的生产预报。Spearman使用相对于收获年1月1日的日期偏移，避免把不同公历年份带来的相关误当性能。误差=预测−观测，正值为偏晚。

样本只有5个产季，每折训练仅4个独立年份，未估计可靠预测区间，覆盖率NA，不能声称已验证区间性能。P1包含2025办内早期物候的敏感性仅限日历基线，并在相同正常样本集合比较MAE，避免样本变化造成误读。

## 2025办内早期物候的包含/排除敏感性

{sensitivity_summary}

common_normal指标保留相同的12个主分析测试样本，只允许其他年份训练折中增加办内2025早期观测；all指标另含办内2025的留出预测。二者不能混为同一评价集合。此结果不识别台风的因果影响。

**低温日数、非线性温度响应、水分模型及P2/P3 GDD均未运行：完整阶段日气象不足。** 因此不能据此检验H1/H2、认定某气象模型最佳，或判断某任务已被气象稳定预测。
''')
    dc=gate['dynamic_window_counts']
    write('02_DYNAMIC_WINDOW_REPORT.md',f'''# 固定与实测动态窗口

W1保留固定窗口覆盖审计。W2现已构建：共{dc['total']}个候选窗口，其中{dc['valid_date_boundaries']}个有完整有效边界；完整温度+降水特征窗口{dc['complete_weather_features']}个。窗口两端包含，邻接阶段会共享边界日，这是本次明确的统计约定。

缺失窗口不以部分观测的均值/和冒充完整阶段统计。表中日期边界可用不代表气象特征可用。

W3尚未构建：本次只有天气独立日历基线，没有可验证的气象驱动物候模型，且预测阶段内的天气仍缺失。未在全数据拟合后冒充交叉拟合窗口；也未用真实下游物候补齐预测边界来声称部署性能。

W1/W2/W3产量预测性能比较仍未执行。基于实际后续天气的模型即使以后建成，也需说明其条件预测性质，不能等同于提前天气预报。
''')
    write('03_YIELD_MODEL_REPORT.md',f'''# 正常产量模型：天气特征仍阻塞

当前有{normal_n}个保守正常候选果园—产季、{len(counts['normal_eligible_years'])}个年份；A39及产季归年问题已解决。数量达到方案最低门槛，但完整W1/W2气象特征没有达到要求，所有Y模型未执行。基线与动态窗口的产量预测优劣、LOYO误差和区间NA。

{weather_reasons}

2025办内排除，红明2025/2026正常年资格待确认。原表均值与类别缺测核对项仍保留。不能用仅有秋冬天气解释为已覆盖全部产量形成阶段。
''')
    write('04_TYPHOON_CASE_REPORT.md',f'''# 2025办内：模型外灾害案例

最终亩产=0，未测单株产量、单果重、果数及代理NA。主分析排除；早期P1日期按A列归年后可用于“包含/排除”的日历基线敏感性，结果在 `results/phenology/P1_typhoon_sensitivity.csv`（仅all运行后生成）。P2/P3无后续观测，不能补齐。

{sensitivity_summary}

2025-03-01是放弃投产决定日，具体台风发生日NA。正常产量模型尚未建立，所以正常生产基线、区间、绝对与相对差均NA；没有输出因果台风损失。

{markdown_table(doc_evidence)}
''')
    write('05_SCENARIO_REPORT.md','''# 情景推演仍未执行

日期规则已修复，但没有获得验证的气象P1、水分或产量模型。S1暖冬、S2秋梢推迟、S3水分、S4产量扰动全部未运行。不得用历史中位日期基线对温度扰动给出伪生理响应，也不能把未运行写为变化0天。
''')
    execution_title='完成日历基线' if comparison is not None else '阶段0重新审计完成'
    write('FINAL_EXPERIMENT_REPORT.md',f'''# 实验继续执行结果：跨年日期已修复，{execution_title}

## 1. 完整P1/P2/P3样本

{summary}

## 2. 正常产量独立样本

原始15个果园—产季，14个非零亩产，保守正常候选{normal_n}个（{len(counts['normal_eligible_years'])}年）；固定绝收1个，红明损伤待核实2个。45个类别行不是45个独立环境样本。

## 3. 2025办内物候处理

主分析排除，仅将其可用早期P1纳入日历基线敏感性。不是普通正常物候样本。具体台风日期未知，年度资料已记载诱导/抽穗受损状态。

## 4. P1预测目标、基线与LOYO

目标是秋梢成熟之后的抽穗完整日期。气象最佳模型未产生；下面只报告天气独立的历史基线：

{baselines}

## 5. P2/P3是否稳定可预测

{baseline_interpretation} 没有可用完整天气去验证GDD模型。见逐模型、逐折表，不能只看汇总相关。

## 6. 非线性温度是否优于低温日数

未检验，缺少从真实秋梢起点开始的连续天气。

## 7. 水分增益

未检验；降水也不能代表未知灌溉/土壤水分。

## 8. W2是否优于W1

已得到{dc['valid_date_boundaries']}个W2日期边界，但完整天气特征{dc['complete_weather_features']}个，未进行预测优劣比较。

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

{markdown_table(status)}

运行 `python -m src.cli all --config configs/base.yaml` 可重建当前允许阶段；尚有天气阻塞时返回退出码2。`python scripts/verify.py` 记录真实pytest与重复重建结果。阶段0先单独提交，然后执行允许的基线。

主要产物：`data/processed/phenology_event_long.csv`、`results/qc/phenology_date_normalization.csv`、`results/phenology/P1_cv_predictions.csv`、`results/windows/observed_dynamic_features.csv`、`results/figures/`。
''')
