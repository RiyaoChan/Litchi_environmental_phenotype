"""Evidence-led Chinese synthesis of the frozen V3 experiment, including stops."""
from __future__ import annotations
import importlib.metadata
import json
import platform
import pandas as pd

from .io_utils import write_csv,write_json,sha256
from .reporting import markdown_table


def final_report(root,cfg,weather_gate,window_gate,yield_gate,scenario_status,scenario_summary,figures):
    base=root/cfg['outputs']
    def csv(name): return pd.read_csv(base/name)
    def js(name): return json.loads((base/name).read_text(encoding='utf-8'))
    comparisons={task:csv(f'phenology/{task}_model_comparison.csv') for task in ['P1','P2','P3']}
    primary={task:table[table.validation=='LOYO'].set_index('model_id') for task,table in comparisons.items()}
    stability={task:csv(f'phenology/{task}_stability_diagnostics.csv').set_index('model_id') for task in primary}
    executions={task:js(f'phenology/{task}_execution.json') for task in primary}
    yield_table=csv('yield/model_comparison.csv')
    ym=yield_table[(yield_table.cohort=='MAIN')&(yield_table.validation=='LOYO')].set_index('model_id')
    p1=primary['P1']; daily=p1.loc[['P1-D1','P1-D2']].MAE_days.idxmin()
    hourly=p1.loc[['P1-H1','P1-H2','P1-H3']].MAE_days.idxmin()
    statuses=[{'experiment_id':'R4-QC','status':weather_gate['status'],'reason':'daily_hourly_continuity_grid_and_source_hash_checks'}]
    for task,execution in executions.items():
        statuses.extend({'experiment_id':model,'status':'executed','reason':'nested_LOYO_and_forward_rolling'} for model in execution['primary_models'])
        statuses.append({'experiment_id':execution['extension'],
                         'status':'executed' if execution['extension_executed'] else 'blocked',
                         'reason':'temperature_only_pooled_MAE_gate; no_posthoc_expansion'})
    statuses.extend({'experiment_id':task,'status':'executed_exploratory','reason':'duration_baseline_only; no_validated_P1_weather_form'} for task in ['P1A','P1B'])
    statuses.append({'experiment_id':'R3-regional-daily','status':'executed_sensitivity','reason':'auxiliary_only_never_replaces_R4'})
    statuses.append({'experiment_id':'P1-bannei2025-early','status':'executed_sensitivity','reason':'13_total_and_common_12_reported_separately'})
    for row in window_gate['evaluation_completeness']:
        statuses.append({'experiment_id':row['window_type'],'status':'limited' if row['window_type']=='W3-PRED' else 'executed',
                         'reason':f"outer_boundaries_{row['n_complete']}/{row['n_test_seasons']}; inner_features_rechecked_separately"})
    statuses.extend({'experiment_id':r.model_id,'status':r.status,'reason':f'main_LOYO_predictions_{r.n_predictions}/12'} for r in ym.reset_index().itertuples())
    statuses.extend({'experiment_id':r.experiment_id,'status':r.status,'reason':r.reason} for r in scenario_status.itertuples())
    statuses.append({'experiment_id':'bannei2025-normal-reference','status':'blocked','reason':'no_validated_normal_W3_yield_model; actual_zero_retained'})
    write_csv(base/'qc/experiment_status.csv',statuses)

    # Export the real failure lineage, rather than guessing why a partial score arose.
    lineage=csv('yield/feature_partition_manifest.csv').fillna('')
    invalid=lineage[(lineage.model_id=='Y-W3P')&lineage.context.str.startswith('MAIN_')&lineage.feature_status.ne('complete')]
    failures=[]
    for row in invalid.itertuples():
        failed=next((s for s in json.loads(row.chain_trace) if s['status']!='predicted'),{})
        failures.append({'context':row.context,'season_id':row.season_id,'role':row.role,
                         'boundary_training_years':row.boundary_training_years,'first_failed_task':failed.get('task'),
                         'model_id':failed.get('model_id','no_fit'),'temperature_c':failed.get('spec',{}).get('temperature'),
                         'fitted_threshold':failed.get('threshold'),'prediction_status':failed.get('status')})
    failures=pd.DataFrame(failures).drop_duplicates()
    write_csv(base/'yield/W3_incomplete_boundary_diagnostics.csv',failures)
    loyo_failures=failures[failures.context.str.startswith('MAIN_LOYO')]

    # A completed gated workflow is different from a successful scientific hypothesis.
    state={'workflow_status':'completed_with_scientific_stop_rules','data_gate_pass':weather_gate['status']=='pass',
           'P1_stable_weather_models':executions['P1']['stable_weather_models'],
           'P2_stable_weather_models':executions['P2']['stable_weather_models'],
           'P3_stable_weather_models':executions['P3']['stable_weather_models'],
           'normal_yield_sample_gate_pass':yield_gate['sample_gate_pass'],
           'formal_yield_comparison_complete':yield_gate['formal_yield_comparison_complete'],
           'Y_W3P_success':yield_gate['Y_W3P_success'],'scenario_model_refits':0,
           'paper_position':'C','figure_pdf_pages':len(figures),
           'forecast_scope':'conditional_on_realized_ERA5; not operational future-weather forecast',
           'raw_data_changed':False,'reproducibility_record':'results/r4/logs/verification.json',
           'visual_review_record':'results/r4/logs/visual_qa.json'}
    write_json(base/'qc/execution_summary.json',state)
    final_gate=dict(weather_gate)
    final_gate.update(yield_gate='blocked_incomplete_nested_W3_partitions',
                      normal_yield_sample_gate_pass=yield_gate['sample_gate_pass'],
                      formal_yield_comparison_complete=yield_gate['formal_yield_comparison_complete'],
                      workflow_status=state['workflow_status'])
    write_json(base/'qc/analysis_gate_r4.json',final_gate)
    package_names=['numpy','pandas','scipy','scikit-learn','matplotlib','openpyxl','PyYAML','pytest']
    write_json(base/'logs/environment.json',{'python':platform.python_version(),'platform':platform.platform(),
        'packages':{p:importlib.metadata.version(p) for p in package_names},'seed':cfg['seed']})
    implementation=list((root/'configs').glob('r4_*.yaml'))+list((root/'src').glob('r4_*.py'))
    implementation += [root/'src'/p for p in ['phenology_models.py','phenology_cv.py','yield_models.py','yield_cv.py','scenario_simulation.py']]
    write_csv(base/'qc/implementation_hashes.csv',[{'path':p.relative_to(root).as_posix(),'sha256':sha256(p)} for p in sorted(set(implementation))])

    questions=[
        ('1. R4日/小时是否连续？','是。三园均覆盖2021-08-01至2026-06-30，共5385日行和129240小时行；时间戳、核心变量和重复检查通过。'),
        ('2. 是否不同ERA5网格/序列？','是。三个不同返回网格，温度/降水序列不完全相同；高度相关仍不代表独立气候重复。'),
        ('3. P1历史持续时间基线？',f"P1-B0 LOYO MAE={p1.loc['P1-B0','MAE_days']:.2f}天，同一12个正常产季。"),
        ('4. 最佳日尺度P1？',f"候选中{daily}误差最低，{p1.loc[daily,'MAE_days']:.2f}天，仍差于历史基线。"),
        ('5. 最佳小时尺度P1？',f"候选中{hourly}误差最低，{p1.loc[hourly,'MAE_days']:.2f}天；不是独立测试集确认的赢家。"),
        ('6. 小时尺度稳定优于日尺度和历史？','否。主LOYO中最佳小时模型也未胜过最佳日模型或B0；增加小时记录没有增加独立产季样本数。'),
        ('7. P1水分有独立增益？','未检验，不可回答有或没有。温度模型没有胜过B0，按预定门槛停止P1-W1，不再扩大变量搜索。'),
        ('8. P2/P3 GDD优于基线？','P2初步支持：6.75→5.08天，4/5年非劣；P3仅4.92→4.83天，改善依赖单年，不稳定。'),
        ('9. W2比两个W1更好？','当前相同12样本、同一Ridge流程不支持。W2 MAE 515.75，W1-C 465.84，W1-M 471.01 kg/亩；仅限当前变量和验证设置。'),
        ('10. W3保留W2的大部分优势？','无法成立：W2未显示该优势，W3内层部分不可用，仅8/12条LOYO预测；不能靠删掉困难样本证明优势。'),
        ('11. Y-W3P稳定胜过产量历史基线？','未验证。样本量门槛通过，但完整嵌套特征/比较门槛未通过，停止正式产量情景。'),
        ('12. 论文定位A/B/C？','C最合适：气象—物候阶段响应/机制假说检验，产量仅探索性。不是已证明因果机制，也不是完整业务预测系统。')]
    answers='\n\n'.join('### '+q+'\n\n'+a for q,a in questions)
    model_labels={'P1-B0':'果园历史持续天数','P1-B1':'果园历史目标日历日期','P1-D1':'低温日数（Tmean/Tmin有限候选）',
                  'P1-D2':'冷度日CDD','P1-H1':'低温小时数','P1-H2':'冷度小时CDH','P1-H3':'低参数非线性低温响应'}
    p1_display=p1.reset_index()[['model_id','n_samples','n_predictions','MAE_days','MAE_valid_only_days']]
    p1_display.insert(1,'model_definition',p1_display.model_id.map(model_labels))
    later=pd.concat([primary[t].reset_index().assign(task=t) for t in ['P2','P3']],ignore_index=True)
    later=later[['task','model_id','n_samples','MAE_days','RMSE_days']]
    complete_y=ym[ym.status=='complete'].reset_index()[['model_id','n_predictions','MAE_kg_mu','RMSE_kg_mu','Spearman_r']]
    partial_y=ym[ym.status!='complete'].reset_index()[['model_id','status','n_predictions','MAE_kg_mu','baseline_MAE_same_seasons_kg_mu']]
    ci=stability['P2'].loc['P2-M1']
    regional=csv('phenology/R3_vs_R4_daily_sensitivity.csv')
    early=csv('phenology/P1_bannei_early_sensitivity.csv')
    report=f'''# 荔枝R4 V3实验最终报告

## 结论先行

本轮完成了V3允许执行的证据链，并实际触发Stop-P1、Stop-Y和对应情景停止规则；“流程执行完成”不等于“所有科学假设成立”。当前最合理定位为 **C：阶段性气象—物候响应研究，产量仅探索性**。P2热量模型有初步留出证据，P1小时低温没有优于历史规律，P3增益脆弱；尚不能形成经过验证的整链物候—产量预测。

工作分支：`codex/litchi-r4-phenology-yield-v3`。方案来源提交：`{cfg['baseline_commit']}`。本报告与代码、冻结配置、逐折结果同版本提交；最新提交以仓库分支HEAD为准。旧R2/R3输出与原Excel/Word保留，不改main。

## 一、十二个研究问题的直接答案

{answers}

## 二、观察事实与数据边界（observed fact）

R4为按果园坐标请求的ERA5格点再分析，不是果园现场站实测。精确请求坐标不等于原生空间分辨率提高；本次返回格点与请求点距离约10–14 km。每日/每小时是在地Asia/Shanghai时间轴，小时转日均温最大偏差约0.067℃，符合预注册0.1℃舍入容差。ERA5空间尺度与本地时区含义见[Open-Meteo官方历史天气文档](https://open-meteo.com/en/docs/historical-weather-api)；API elevation字段为返回地点/下尺度使用高度，不当作原生格点平均海拔。

{markdown_table(csv('qc/grid_identity.csv'))}

独立观测单位是果园×收获年：总计15个产季，主物候/正常产量各12个，覆盖5年；129240小时不能充当129240个带物候标签的样本。三个果园中办内与红明距离较近，不能把其气象相关性忽略。

继续使用A列收获年跨年规则：2022办内秋梢老熟2021-09-25，抽穗2022-01-20；保留月日和群体物候允许的交叠。`测产.xlsx!A39=2026`以用户确认的本地文件为准。原始11文件及R4输入8文件用SHA-256快照核验，未重新改写Excel。完整检查见[00数据闸门报告](00_R4_DATA_GATE_REPORT.md)。

## 三、P1逐日与逐小时模型（held-out prediction）

以下均为同一12个主产季的整年外层LOYO；模型家族内部阈值只在训练年份的内层留年验证中选择，不做随机日/小时拆分。

{markdown_table(p1_display)}

P1-D2有2个未达到累计阈值的样本。全样本72.42天是预注册的“未预测=365天”惩罚评分，不是成功10个样本的普通MAE；成功子集MAE为13.90天，仅作失败诊断，不能与全12个基线直接比较。所有候选都保留，不删除失败模型。

P1-B0为候选总体误差最低者（4.83天）；日模型D1为6.25天，小时H3为6.75天。没有气象模型达到稳定优越标准；滚动验证中B0/D1/H3分别约7.33/13.83/8.17天，结论不支持小时气象带来稳定增益。不能从这一负结果断言温度对荔枝无作用；它只说明当前有限产季、格点天气和预定响应形式没有提供超过历史规律的预测信息。

未开展P1水分扩展与P1暖冬/秋梢推迟情景，不等价于已证明水分或秋梢管理无效。选中的低温阈值是模型参数，不是已测得的组织分化生理阈值。逐年/逐果园误差、参数、全部训练候选和失败标记均在`results/r4/phenology/`。

## 四、P2/P3及露白辅助分析

{markdown_table(later)}

P2-M1（GDD）相对B0改善1.67天：4/5个LOYO年份非劣，删去最佳改善年2024仍改善1.22天；滚动MAE由8.67降到7.17天。按方案操作性稳定标准获准进入P2条件敏感性，但仅5年按年聚类自助的改善95%区间为[{ci.improvement_cluster_bootstrap_95_low_days:.3f}, {ci.improvement_cluster_bootstrap_95_high_days:.3f}]天，跨0，不能写成稳健显著效果。辐射扩展P2-M2为5.17天，不优于较简单M1，因此不以扩展模型作主模型。

P3-M1只改善0.08天，仅2/5年非劣；删去2024后反而更差约0.89天，标记fragile。高温/辐射/水分受限扩展为6.50天，没有挽救结果，不再增加模型复杂度。

露白P1A/P1B各12个日期对，历史持续时间基线LOYO约7.92/5.33天。由于P1未验证出温度形式，本轮只作分段辅助诊断，不把露白等同于未观测的组织学分化时间，不开启新一轮候选搜索。见[露白报告](04_WHITE_TIP_EXPLORATORY_REPORT.md)。

## 五、动态窗口与产量：必须分开两道闸门

W1-CALENDAR为预注册固定日历，W1-MEDIAN为训练年份典型物候日期；W2-OBS使用真实未来物候，是回顾性信息上限（retrospective upper bound），不保证任何拟合算法都更好。W3-PRED仅以已知秋梢起点开始，递推预测抽穗、盛花、成熟。

四类窗口的外层评估样本均12/12完整，外层训练特征完整。但产量调参内层需要重新构建窗口；W3训练样本还要排除自身收获年进行物候校准，不能复用外层一次预测结果。这一更严格检查暴露了真实边界失败：

{markdown_table(loyo_failures)}

在2022/2025相应外层与内层组合中，2026办内/鲁宏训练行只能使用2023、2024年校准；所选P1-H2在2026截止6月30日仍未达到其阈值，后续起点不可用。外层2022与2025的Y-W3P因此停止，没有用真实日期、临时基线回退或删行掩盖失败。早期滚动内层另有历史不足问题。完整追踪见`yield/W3_incomplete_boundary_diagnostics.csv`和`feature_partition_manifest.csv`。

### 完整主样本比较（同一12个产季，kg/亩）

{markdown_table(complete_y)}

只有低维Ridge，最多6个连续变量+固定果园编码；所有窗口共用alpha网格及训练集均值/标准差缩放，每个内层重新生成依赖训练的特征。PHENO扩展用4个气象指标+2个预测日期，总数仍为6。没有RF、XGBoost或深度学习补救。

W2当前未优于两个W1，因此不能声称真实动态物候窗口增强了产量预测。W1-C相对历史亩产基线的微小MAE改善也不足以证明可部署：主LOYO排序相关为负，且滚动MAE为442.89，反而差于B0的422.71 kg/亩；误差规模和跨年稳定性仍不足。

### 不完整W3的审计子集（不是主性能比较）

{markdown_table(partial_y)}

8个可运行样本的W3误差431.31 kg/亩只可与同8个基线445.90作诊断，不能拿去和完整12个基线493.44相比，更不能据此宣称预测成立；缺失的4个样本是验证失败导致，非随机缺失。其主LOYO正常产量比较未完成，S5停止。

结论：正常样本量门槛（12≥10、5年≥4年）通过；完整嵌套特征和正式W3产量门槛未通过。产量部分保留为探索性、回顾性结果，不输出产量预报。

## 六、敏感性分析（sensitivity analysis）

### R3仅作区域代理对照

{markdown_table(regional)}

R3不替换R4主数据。R3-D1的LOYO略低于R4-D1，但仍差于同样B0；不能见到较小误差后改换“主气象”。D2的惩罚评分亦不能当作成功样本普通MAE。

### 加入办内2025早期P1

{markdown_table(early)}

单列13样本结果和原12样本上的重评估；不会拿不同n的分数直接排优劣。该敏感性改变部分参数/误差，但没有把办内2025的0产量纳入正常产量训练。

红明2025、2026及两年同时纳入均按预定敏感性单独运行。恢复样本加入后，固定窗口相对基线的优势不保持；红明2026缺定量物候，相关W2/W3敏感性阻塞，不填日期。详见[产量报告完整敏感性表](06_YIELD_MODEL_REPORT.md)。次级目标仅报告完整度，果数代理不冒充独立实测果数。

## 七、2025办内灾害案例

最终亩产0作为事实保留；未测单株产量、单果重、果数仍为NA。2025-03-01是放弃投产决定日，不是台风发生日。本例不用于正常亩产模型训练，仅允许早期物候敏感性。

本轮没有经过验证的正常W3产量模型，因此正常生产参照和“参照缺口”均为NA；NA不表示损失为0。即使将来有参照，也不是因果台风损失，不能凭一个灾害案例区分气象、管理变化和恢复效应。见[案例报告](07_TYPHOON_CASE_REPORT.md)。

## 八、获准情景（scenario simulation）与停止项

{markdown_table(scenario_status)}

{markdown_table(scenario_summary)}

仅P2-M1的+1/+2℃固定模型敏感性获准。每个样本沿用其原LOYO训练折参数，不重拟合；变化为“扰动后预测−未扰动预测”，负值代表提前。以实际抽穗起点为条件，不通过未验证的P1外推起点，不称完整秋梢到成熟链的响应。

温度扰动同步改变日均/日高/日低与小时气温，其他天气变量保持原值；这是受控模型输入分析，不是包含湿度、辐射、土壤反馈的真实未来气候。P1 S1/S2/S3、P3 S4和产量S5均未获准；不生成暖冬×秋梢二维响应图，不输出对应“影响多少天/多少公斤”的强结论。

## 九、可写入论文与不能写入论文（unsupported claim）

可以写：完成按果园定位的日/小时再分析质量审计；在整年嵌套验证下，小时低温未显示超过历史P1规律的预测增益；P2阶段GDD有初步支持、P3不稳定；动态窗口的当前正常产量证据不足；严格无泄漏验证暴露小样本模型链的可用性限制。

不能写：已证明温度/低温小时对产量的因果效应；发现通用荔枝生理低温阈值；反演了不可观测的真实花芽分化时刻；建成完整物候—产量业务预测系统；小时记录等价于扩大标签样本；P1模型验证成功；量化了因果台风损失。

最合适是C定位，且“机制”限于有生理动机的假说检验，不是机制已确证。可考虑标题方向：“果园定位再分析气象对荔枝多阶段物候预测的增量信息及动态产量窗口的验证边界”。发表前仍需外部年份/果园及管理记录验证；建议下一轮预先固定候选与回退政策，补充产季标签、秋梢/花芽状态、修剪灌溉控梢等记录，并用未来年份检验，不能回头利用本轮成绩修改阈值再称验证。

## 十、交付与复现

科学电子表格技能用于强调源值追溯、独立样本单位与同样本比较；PDF流程用于逐页检查图件。没有改写输入工作簿，没有用展示标准化替代模型训练内缩放。

10份规定报告及P2/P3分报告已生成。共{len(figures)}页[图集](../../results/r4/figures/R4_FIGURE_ATLAS.pdf)，逐图PNG与[中文图注](../../results/r4/figures/FIGURE_CAPTIONS_ZH.md)配套；产量图只展示完整12样本的可比柱，W3明确标不完整。图件视觉核验与哈希记录在`results/r4/logs/visual_qa.json`。

```bash
python -m src.cli r4-all --config configs/r4_experiment_v3.yaml
python scripts/verify_r4.py --stage r4-all --repeat
```

`r4-all`在所有允许阶段执行并记录停止规则后返回0，不代表各科学模型验证通过。单独`r4-yield`在完整比较未通过时返回2。旧`src.cli all`仍使用R2配置/闸门，不混用。验证脚本检查两次产物逐字节一致、源文件哈希和真实pytest结果；[测试/重建日志](../../results/r4/logs/verification.json)是通过/skip数量的唯一即时记录，不能把旧R2两个明确skip当作R4成功验证。各R4测试实际覆盖日/小时累计、训练折隔离、内外层W3边界追踪、缩放、产量损伤排除与情景不重拟合。

固定候选与决策见`configs/r4_*.yaml`、[实施决策记录](../../experiments_guide/R4_V3_IMPLEMENTATION_DECISIONS.md)。数值结果、逐折模型JSON、候选评分、窗口训练血缘、阶段状态和环境版本均保存在`results/r4/`。主数据快照`data/metadata/r4_input_hashes.json`与原始快照`input_hashes.json`保持不可自动更新；数据有正式修订时必须另立版本，不可删除哈希保护。
'''
    (root/cfg['reports']/'FINAL_R4_EXPERIMENT_REPORT_ZH.md').write_text(report,encoding='utf-8')
    return state
