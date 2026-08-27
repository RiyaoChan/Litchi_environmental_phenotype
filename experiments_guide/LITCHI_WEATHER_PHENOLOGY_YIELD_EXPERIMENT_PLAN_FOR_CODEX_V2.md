# 荔枝气象—物候—产量研究执行计划 V2（交由 Codex 执行）

> 仓库：`RiyaoChan/Litchi_environmental_phenotype`  
> 基线分支：`main`  
> 建议工作分支：`codex/litchi-phenology-yield-r2`  
> 本轮定位：**先建立并验证气象驱动的关键物候日期预测模型，再判断现有数据是否足以支撑正常产年的产量预测；2025年办内台风绝收作为独立灾害案例，不进入正常产量关系拟合。**

---

# 0. 本轮必须锁定的研究对象

本轮不是建立一个“气象直接预测产量”的黑箱模型，也不是根据物候倒推出历史天气。

必须建立以下顺序模型：

```text
日气象 + 已发生的前一物候阶段
                ↓
        预测下一个关键物候日期
                ↓
  依据实际或预测物候划分动态气象窗口
                ↓
      预测正常生产条件下的产量
                ↓
   对暖冬、秋梢老熟推迟等情景做敏感性推演
```

本轮包含三个物候预测任务和一个有条件执行的产量预测任务。

## 0.1 物候模型 P1：花芽诱导与抽穗日期预测（主模型）

- 起始事件：`autumn_flush_mature`，秋梢老熟日期；
- 主要预测目标：`inflorescence_emergence`，抽穗日期；
- 辅助预测目标：`white_tip`，露白点日期，仅在定义一致且完整样本足够时执行；
- 输入：秋梢老熟后逐日温度和降雨条件；
- 输出：
  - 预测抽穗完整日期；
  - 从秋梢老熟到抽穗的预测天数；
  - 有效诱导累积曲线；
  - LOYO日期误差，单位为天。

P1是本研究第一优先级，也是后续情景推演的核心。

## 0.2 物候模型 P2：抽穗至盛花日期预测

- 起始事件：`inflorescence_emergence`；
- 预测目标：`full_bloom`；
- 输入：抽穗后逐日温度，必要时加入降雨或日照；
- 主体模型：低参数积温/GDD阈值模型；
- 输出：预测盛花日期、阶段持续天数和LOYO误差。

## 0.3 物候模型 P3：盛花至成熟日期预测

- 起始事件：`full_bloom`；
- 预测目标：`maturity`；
- 输入：盛花后的积温、降雨、高温日数等少量变量；
- 主体模型：低参数GDD模型及其有限扩展；
- 输出：预测成熟日期、阶段持续天数和LOYO误差。

## 0.4 产量模型 Y：正常产年的产量预测（通过闸门后才执行）

- 主要目标：果园—产季层面的亩产；
- 次要目标：加权平均单株产量；
- 探索性目标：果实数量代理值和单果重；
- 输入：不同物候阶段的气象指标，以及实际或交叉拟合预测物候日期；
- 输出：正常生产条件下的产量预测值、预测区间和LOYO误差。

产量模型必须回答：

```text
动态物候窗口是否比固定月份窗口更能预测正常产量？
预测物候能否替代未来尚未观测到的真实物候？
```

---

# 1. 已确认事实与禁止擅自修改项

Codex必须把以下内容视为项目约束：

1. `物候期.xlsx` 的“年份”表示产季年份/收获年份，物候横跨两个公历年是正常现象。
2. 用户将把物候日期统一转换为真实完整日期；代码只接受完整日期，不得只比较月、日。
3. `测产.xlsx!A39 = 2025` 已确认正确，禁止自动修改为2026。
4. 同一果园、同一2025产季若出现多个数据区块，必须保留 `source_block_id`，不得把它们视为独立气象样本。
5. 2025产季办内果园因台风结构性损毁而无产量：
   - 最终产量为真实数值 `0`；
   - 未测单株产量、果数、单果重和后续物候仍为 `NA`；
   - 不得把未测构成统一填成0；
   - 不得把该样本作为普通低产年进入正常产量模型。
6. 谢花、初始坐果和生理落果等群体阶段允许重叠，代码只能审计，不得自动改日期。
7. 原始Excel和Word文件不得被覆盖或改写。

---

# 2. 关于2025年办内台风样本的统一处理

## 2.1 产量分析

强制编码：

```text
orchard_id = bannei
harvest_year = 2025
typhoon_damage = 1
normal_production_year = 0
final_yield_kg_per_mu = 0
```

该样本：

- 不进入正常产量模型训练；
- 保留在描述性图表中；
- 作为模型外灾害案例；
- 可用于包含/排除的敏感性分析；
- 不得用于训练绝收分类器、hurdle模型或零膨胀模型。

## 2.2 物候分析

台风可能改变树体结构、秋梢状态和正常生殖过程，因此2025年办内不能自动视为普通物候样本。

Codex必须先建立：

```text
typhoon_event_date
structural_damage_stage
phenology_main_eligible
phenology_sensitivity_eligible
```

规则：

1. 优先从年度示范园资料和用户已提供说明中确定台风发生时间及受损阶段；
2. 若无法明确台风发生时间或其对秋梢、抽穗的影响，则：

```text
phenology_main_eligible = 0
phenology_sensitivity_eligible = 1
```

3. 只有明确确认某一物候转换发生在结构性损毁前，且观测仍代表正常生理过程时，才允许该转换进入主物候模型；
4. 最终报告必须分别给出“排除2025办内”和“纳入可用早期物候”的敏感性结果。

---

# 3. 研究假设

本轮只检验以下四个预注册假设。

## H1：温度累积能够预测抽穗日期

从秋梢老熟日开始计算的有效温度诱导量，达到阶段阈值后发生抽穗。

## H2：非线性温度响应优于简单低温日数

适宜低温贡献较高，过高或过低温度贡献较低；非线性响应模型应在LOYO验证中优于历史平均日期和简单阈值模型。

## H3：动态物候窗口优于固定日历窗口

按每个果园—产季的实际或预测物候日期提取阶段气象，比固定月份汇总更能解释和预测物候及正常产量。

## H4：2025年办内的零产量属于结构性灾害偏离

正常产年模型对2025年办内给出的只是“正常生产基线预测”，实际0产量与其差额只能作为灾害损失参照，不得宣称为已识别的因果台风效应。

---

# 4. 分析单位与数据结构

## 4.1 独立环境样本

主要独立单位：

```text
果园 × 产季年份
```

同一果园—产季中的不同树类、树数、调查批次或小区属于嵌套重复，不得随机拆到训练和测试两侧。

## 4.2 推荐主键

```text
region_id
station_id
orchard_id
cultivar
harvest_year
source_block_id
plot_id
tree_class
tree_id
```

## 4.3 同一年多个区块

对于 `A39=2025` 及同年其他区块：

1. 原样保留；
2. 生成区块对照表；
3. 尝试从字段、树数和年度资料判断其是重复调查、不同小区还是其他批次；
4. 未确认前不得简单删除或合并；
5. 即使保留多个区块，交叉验证仍必须按完整 `harvest_year` 分组。

输出：

```text
results/qc/source_block_review.csv
reports/01_SOURCE_BLOCK_REVIEW.md
```

---

# 5. 推荐目录结构

```text
configs/
  base.yaml
  phenology_models.yaml
  weather_windows.yaml
  yield_models.yaml
  scenario_simulation.yaml

data/
  interim/
  processed/
  metadata/

src/
  data_ingest.py
  data_qc.py
  build_master.py
  weather_features.py
  phenology_models.py
  phenology_validation.py
  dynamic_windows.py
  yield_models.py
  yield_validation.py
  typhoon_case.py
  scenario_simulation.py
  plots.py
  reporting.py
  cli.py

scripts/
  run_stage_0_qc.py
  run_stage_1_phenology.py
  run_stage_2_windows.py
  run_stage_3_yield.py
  run_stage_4_typhoon.py
  run_stage_5_scenarios.py
  run_all.py

results/
  inventory/
  qc/
  descriptive/
  phenology/
  windows/
  yield/
  typhoon_case/
  scenarios/
  figures/
  tables/
  logs/

reports/
  00_DATA_FEASIBILITY_REPORT.md
  01_PHENOLOGY_MODEL_REPORT.md
  02_DYNAMIC_WINDOW_REPORT.md
  03_YIELD_MODEL_REPORT.md
  04_TYPHOON_CASE_REPORT.md
  05_SCENARIO_REPORT.md
  FINAL_EXPERIMENT_REPORT.md

tests/
```

全局随机种子：`20260827`。

一条命令应能重建全部允许执行的阶段：

```bash
python -m src.cli all --config configs/base.yaml
```

---

# 6. 阶段0：数据标准化和可行性审计

本阶段完成后必须先提交报告，任何模型不得跳过本阶段直接运行。

## 6.1 读取文件

至少读取：

```text
物候期.xlsx
测产.xlsx
气象数据原/海口市2021-2026气象数据.xlsx
气象数据原/陵水县2021-2026气象数据.xlsx
示范园/ 下年度资料
```

## 6.2 输出标准表

### A. 物候长表

```text
data/processed/phenology_event_long.csv
```

字段至少包括：

```text
orchard_id
region_id
cultivar
harvest_year
source_block_id
event_name
event_date
calendar_year
day_of_year
source_file
source_sheet
source_row
source_column
raw_value
qc_flag
```

事件名称：

```text
autumn_flush_mature
white_tip
inflorescence_emergence
initial_bloom
full_bloom
end_bloom
initial_fruit_set
fruit_drop_1
fruit_drop_2
color_break
maturity
preharvest_drop
```

### B. 日气象表

```text
data/processed/weather_daily.csv
```

至少包括：

```text
station_id
region_id
date
tmean_c
tmin_c
tmax_c
precip_mm
relative_humidity_pct
sunshine_h
wind_speed
source_file
source_sheet
source_row
```

不存在的字段保留缺失，不得伪造。

### C. 测产长表和果园—产季表

```text
data/processed/yield_observation_long.csv
data/processed/orchard_season_master.csv
```

果园—产季表至少包括：

```text
season_id
orchard_id
region_id
station_id
cultivar
harvest_year
source_block_id
normal_production_year
typhoon_damage
final_yield_kg_per_mu
mean_yield_per_tree_kg
mean_single_fruit_weight_g
fruit_number_proxy
weather_coverage_ratio
phenology_main_eligible
yield_main_eligible
exclusion_reason
```

若A/B/C类有树数和类别均值，按树数加权：

\[
\bar Y=\frac{\sum_c n_c\bar Y_c}{\sum_c n_c}
\]

果实数量代理：

\[
\widehat N_{fruit}=\frac{1000\times Y_{tree,kg}}{W_{fruit,g}}
\]

已有真实果数时，真实果数优先，代理值仅用于核验。

## 6.3 必须输出的数据闸门

生成：

```text
results/qc/analysis_gate.json
reports/00_DATA_FEASIBILITY_REPORT.md
```

报告必须给出：

1. 每个物候转换的完整样本数；
2. 正常产年的独立果园—产季样本数；
3. 每个年份、地区和果园的气象覆盖率；
4. 同一地区多个果园是否共享同一气象序列；
5. 2025办内是否可进入任何主物候转换；
6. 同年重复区块如何解释；
7. 哪些任务可执行、简化执行或阻塞。

建议闸门：

```text
某物候转换完整样本 < 8：只做描述和历史平均基线
8—11：允许简单阈值/GDD模型
>= 12：允许非线性温度模型
>= 12且水分信息完整：允许温度×水分扩展

正常产年独立样本 < 10：不做正式产量预测，只做描述和极简关联
10—14：允许岭回归/PLS等低参数产量模型
>= 15：允许补充Elastic Net，但仍不得使用复杂黑箱作为主模型
```

若完整日期仍未准备好，物候模型必须标记为 `blocked`，停止后续建模，不得猜测年份。

---

# 7. 阶段1：描述性分析

输出：

```text
results/descriptive/phenology_duration.csv
results/descriptive/weather_by_stage.csv
results/descriptive/yield_summary.csv
results/figures/phenology_timeline.*
results/figures/weather_phenology_overlay.*
results/figures/yield_by_orchard_year.*
```

必须展示：

1. 各果园、各产季完整跨年物候时间轴；
2. 日温度、降雨和物候事件叠加；
3. P1、P2、P3阶段持续天数；
4. 正常产年产量变化；
5. 2025办内以独立符号标记“台风绝收”；
6. 物候和产量缺失模式；
7. 不得把简单相关写成因果关系。

---

# 8. 阶段2：物候模型 P1——预测抽穗日期

## 8.1 预测形式

对每个样本，从实际秋梢老熟日期开始逐日读取气象。

预测目标同时保存为：

```text
observed_event_date
predicted_event_date
observed_duration_days
predicted_duration_days
error_days
```

## 8.2 P1模型矩阵

| 实验ID | 模型 | 说明 |
|---|---|---|
| `P1-B0` | 果园历史中位持续天数 | 不使用天气的最低基线 |
| `P1-B1` | 历史中位抽穗DOY | 日期基线 |
| `P1-B2` | 简单低温日数阈值 | 训练折内选择有限候选温度阈值 |
| `P1-M1` | 简单有效低温累积 | 分段温度响应 + 累积阈值 |
| `P1-M2` | 非线性单峰温度响应 | 估计 Tmin、Topt、Tmax 和累积阈值 |
| `P1-M3` | P1-M2 + 水分调节 | 仅在样本和覆盖闸门通过时执行 |
| `P1-M4` | 部分汇聚模型 | 仅允许少量果园偏移，禁止每果园独立拟合全部参数 |

## 8.3 非线性温度响应

实现有界单峰响应：

```text
T <= Tmin 或 T >= Tmax：响应为0
Tmin < T < Tmax：响应在0—1之间
Topt处响应最大
```

累积达到阈值时预测抽穗：

\[
\widehat D_{panicle}=\min\left\{t:\sum_{d=D_{flush}}^t r(T_d,M_d)\ge C\right\}
\]

其中水分修正项 `M_d` 只能在 `P1-M3` 中使用。

所有参数边界写入配置文件，不得散落于代码。

## 8.4 验证

主验证：按完整产季年份进行LOYO。

每一折：

1. 留出一个 `harvest_year` 的所有果园和区块；
2. 仅在其他年份拟合参数和选择阈值；
3. 对留出年份预测抽穗日期；
4. 保存逐样本预测和累积曲线。

指标：

```text
MAE_days
RMSE_days
mean_bias_days
Spearman_r
prediction_interval_coverage
```

## 8.5 P1成功判据

将P1分为三种结论等级：

### 可用于预测

同时满足：

1. 最佳气象模型LOYO MAE低于 `P1-B0`；
2. 相对 `P1-B0` 的MAE改善率至少10%；
3. 改善不是由单一留出年份贡献；
4. 参数在留一年敏感性分析中方向稳定；
5. 没有严重系统性提前或滞后。

### 仅支持气象关联

气象模型能解释部分变化，但LOYO性能未稳定优于基线。

### 当前数据不支持

样本不足、参数不可辨识或性能明显差于基线。

输出：

```text
results/phenology/P1_model_comparison.csv
results/phenology/P1_cv_predictions.csv
results/phenology/P1_parameters.csv
results/phenology/P1_fold_metrics.csv
reports/01_PHENOLOGY_MODEL_REPORT.md
```

---

# 9. 阶段3：物候模型 P2 和 P3

P2、P3必须保持低参数，不能复制P1的全部复杂模型。

## 9.1 P2：抽穗至盛花

模型：

| 实验ID | 模型 |
|---|---|
| `P2-B0` | 历史中位持续天数 |
| `P2-M1` | GDD阈值模型 |
| `P2-M2` | GDD + 一个预注册降雨或低温指标 |

基础公式：

\[
GDD=\sum\max(0,T_{mean}-T_{base})
\]

`Tbase`只能从少量候选中在训练折内选择。

## 9.2 P3：盛花至成熟

模型：

| 实验ID | 模型 |
|---|---|
| `P3-B0` | 历史中位持续天数 |
| `P3-M1` | GDD阈值模型 |
| `P3-M2` | GDD + 一个预注册水分或高温指标 |

P3的目的主要是判断成熟期是否能由气象驱动预测，不要求建立高复杂度生理模型。

## 9.3 输出

```text
results/phenology/P2_*.csv
results/phenology/P3_*.csv
results/figures/observed_vs_predicted_dates.*
```

报告必须分别说明P1、P2、P3哪一个最可预测，不能只报告汇总平均值。

---

# 10. 阶段4：固定窗口、实测动态窗口和预测动态窗口

## 10.1 W1：固定日历窗口

只作为传统基线，初始窗口写入配置：

```yaml
floral_induction:
  start: "{Y-1}-10-01"
  end:   "{Y}-01-31"
flowering:
  start: "{Y}-02-01"
  end:   "{Y}-03-31"
fruit_set_drop:
  start: "{Y}-03-01"
  end:   "{Y}-04-30"
fruit_growth:
  start: "{Y}-04-01"
  end:   "{Y}-06-30"
```

固定窗口必须可配置，不得写死。

## 10.2 W2：实测动态窗口

构建：

```text
autumn_flush_mature -> inflorescence_emergence
inflorescence_emergence -> full_bloom
full_bloom -> end_bloom
end_bloom -> fruit_drop_2
fruit_drop_2 -> maturity
```

W2只代表事后解释上限，不能用于声称生产部署性能。

## 10.3 W3：交叉拟合预测动态窗口

W3必须来自LOYO训练折模型预测：

```text
训练年份拟合P1/P2/P3
        ↓
为留出年份生成预测物候日期
        ↓
按预测日期划分留出年份窗口
```

禁止在全数据上拟合物候模型后再生成W3。

输出：

```text
results/windows/fixed_window_features.csv
results/windows/observed_dynamic_features.csv
results/windows/cross_fitted_dynamic_features.csv
results/windows/window_comparison.csv
reports/02_DYNAMIC_WINDOW_REPORT.md
```

---

# 11. 阶段5：产量模型执行闸门

只有阶段0和物候阶段完成后才判断是否执行正式产量预测。

## 11.1 必要条件

至少满足：

1. 正常产年独立果园—产季样本 `>= 10`；
2. 至少4个收获年份有正常产量；
3. 亩产字段定义和单位一致；
4. 同年重复区块的用途已确认，或已采用保守且可追溯的聚合方案；
5. 不存在训练/测试年份泄漏；
6. W1、W2可构建；
7. W3只能在对应物候模型可生成预测日期时执行。

若不满足，则停止正式产量预测，只输出描述性结果、极简回归和限制说明。

## 11.2 正常产量训练集

```text
normal_production_year == 1
typhoon_damage == 0
yield_main_eligible == 1
```

2025办内必须被测试确认不在该集合中。

---

# 12. 阶段6：正常产年的产量预测

## 12.1 预测目标

主目标：

```text
final_yield_kg_per_mu
```

次目标：

```text
mean_yield_per_tree_kg
```

探索目标：

```text
fruit_number_proxy
mean_single_fruit_weight_g
```

## 12.2 产量模型矩阵

| 实验ID | 输入 | 作用 |
|---|---|---|
| `Y-B0` | 训练折果园历史均值 | 最低基线 |
| `Y-B1` | 果园效应 + 年份趋势 | 低参数统计基线 |
| `Y-W1` | 固定日历窗口气象 | 传统气象模型 |
| `Y-W2` | 实测动态窗口气象 | 事后解释性能上限 |
| `Y-W3` | 交叉拟合预测动态窗口气象 | 可部署动态窗口模型 |
| `Y-W3P` | W3气象 + 预测关键物候日期/持续时间 | 检验预测物候增益 |
| `Y-PREV` | Y-W3P + 前一年产量 | 探索大小年记忆，仅在样本允许时执行 |
| `Y-DEC` | 分别预测果数代理和单果重 | 探索产量构成分解 |

## 12.3 主模型

优先：

```text
岭回归
PLS回归
少参数线性/稳健回归
可选贝叶斯部分汇聚模型
```

Elastic Net仅作补充。随机森林和XGBoost不得作为主结论模型。

## 12.4 主特征限制

主模型最多使用3—5个预注册特征，例如：

```text
P1阶段有效低温累积
花期连续湿日
坐果/落果期高温日数
果实发育期GDD
预测抽穗或盛花日期
```

标准化、插补、特征选择和调参均只能在训练折内部完成。

## 12.5 验证

外层：LOYO。  
内层：按年份分组调参。

指标：

```text
MAE
RMSE
nRMSE
mean_bias
Spearman_r
prediction_interval_coverage
```

`R²`仅作补充。

## 12.6 产量预测结论等级

### 支持正常产量预测

满足：

1. `Y-W3` 或 `Y-W3P` 的LOYO MAE稳定低于 `Y-B0`；
2. 相对 `Y-B0` 的MAE改善至少10%；
3. 同时优于或不劣于 `Y-W1`；
4. 不依赖某一个年份；
5. 预测区间有合理覆盖率。

### 仅支持关联解释

动态窗口或物候特征方向有解释性，但LOYO性能不能稳定超越历史均值。

### 当前数据不支持产量预测

样本量、重复结构或误差不足以支持可推广预测。

即使未达到“支持预测”，仍必须完整报告，不得只展示训练集拟合。

输出：

```text
results/yield/model_comparison.csv
results/yield/cv_predictions.csv
results/yield/fold_metrics.csv
results/yield/coefficient_stability.csv
reports/03_YIELD_MODEL_REPORT.md
```

---

# 13. 阶段7：2025年办内台风案例

使用不包含2025办内的正常产量模型，对该样本生成：

```text
normal_production_baseline_prediction
prediction_interval
observed_yield = 0
absolute_gap
relative_gap_to_prediction
```

表述必须使用：

```text
正常生产基线预测
模型外灾害偏离
潜在产量损失参照
```

不得使用：

```text
已证明的台风因果损失
通用台风损失系数
台风风险预测模型
```

同时完成：

1. 排除2025办内的主模型；
2. 将其以0纳入稳健回归的敏感性模型；
3. 比较主要系数和误差变化；
4. 说明一个灾害样本不能训练灾害模型。

输出：

```text
results/typhoon_case/bannei_2025_case.csv
results/typhoon_case/inclusion_sensitivity.csv
reports/04_TYPHOON_CASE_REPORT.md
```

---

# 14. 阶段8：情景敏感性推演

情景推演不是天气预报，也不是未来气候预测，而是对已验证模型做“输入扰动—输出响应”实验。

## 14.1 物候情景 S1：暖冬温度平移

仅在P1达到“可用于预测”或至少参数稳定时执行。

对每个历史果园—产季的P1窗口，将逐日温度分别增加：

```text
+0.5 ℃
+1.0 ℃
+2.0 ℃
```

其他变量保持不变，输出：

```text
抽穗日期改变天数
有效诱导累积改变
达到阈值的概率或是否无法在观察窗口内达到阈值
果园间差异
```

## 14.2 物候情景 S2：秋梢老熟推迟

将秋梢老熟起始日期分别后移：

```text
+7天
+14天
+21天
```

使用后续实际天气序列重新累计，输出：

```text
预测抽穗日期变化
有效低温窗口缩短程度
是否出现低温积累不足
```

该情景可用于讨论晚秋梢或秋梢老熟偏迟的风险。

## 14.3 水分情景 S3

只有 `P1-M3` 在LOYO中稳定优于 `P1-M2` 时才执行。

采用预注册、可复现的水分扰动，不得随意手工制造降雨。建议选择：

```text
将阶段累计降雨或连续无雨指标设为历史25%、50%、75%分位情景
```

输出温度×水分交互下的抽穗日期变化。

## 14.4 产量情景 S4

只有产量模型达到“支持正常产量预测”时才执行。

一次只改变一个阶段指标：

```text
花期连续湿日 +2天、+4天
坐果/落果期高温日 +3天、+5天
果实发育期GDD ±10%
```

输出正常产量预测变化及区间。

必须称为“模型敏感性情景”，不能称为确定性生产预报。

输出：

```text
results/scenarios/phenology_temperature_shift.csv
results/scenarios/flush_delay.csv
results/scenarios/moisture_sensitivity.csv
results/scenarios/yield_sensitivity.csv
reports/05_SCENARIO_REPORT.md
```

---

# 15. 必须实现的自动化测试

至少包括：

1. `test_no_raw_mutation`；
2. `test_cross_year_dates`；
3. `test_a39_remains_2025`；
4. `test_source_blocks_preserved`；
5. `test_group_split_by_year`；
6. `test_no_tree_level_leakage`；
7. `test_train_only_preprocessing`；
8. `test_cross_fitted_windows`；
9. `test_typhoon_yield_is_zero`；
10. `test_typhoon_components_are_missing`；
11. `test_typhoon_excluded_from_normal_yield_fit`；
12. `test_typhoon_phenology_eligibility_rule`；
13. `test_weather_window_boundaries`；
14. `test_weighted_aggregation`；
15. `test_scenario_does_not_refit_model`；
16. `test_reproducibility`。

执行：

```bash
pytest -q
```

---

# 16. 分阶段停止规则

Codex不得为了“完成全部清单”而强行运行不适合的数据模型。

## Stop 1：完整日期未准备好

停止物候模型，提交数据阻塞报告。

## Stop 2：P1完整样本不足8个

只做描述和基线，不拟合非线性模型。

## Stop 3：P1非线性参数不可辨识

保留简单阈值/GDD模型，不强行输出Tmin、Topt、Tmax。

## Stop 4：正常产量样本不足10个或重复区块无法解释

停止正式产量预测，只做描述、极简关联和台风案例说明。

## Stop 5：产量模型不能稳定优于历史均值

不得宣称建立了有效产量预测模型；将论文定位改为“气象驱动物候及其与产量形成的关联”。

## Stop 6：P1未获得稳定验证

不执行暖冬和秋梢推迟的正式情景结论，仅可输出探索性敏感性结果并明确标记。

---

# 17. 图表输出

建议生成：

1. `Fig01_research_framework`：P1/P2/P3—动态窗口—产量模型链；
2. `Fig02_phenology_timeline`：跨年物候时间轴；
3. `Fig03_weather_phenology_overlay`：温度、降雨与事件叠加；
4. `Fig04_P1_temperature_response`：有效温度响应与累计示例；
5. `Fig05_phenology_cv_predictions`：P1/P2/P3观测与LOYO预测；
6. `Fig06_window_comparison`：W1、W2、W3比较；
7. `Fig07_yield_cv_predictions`：仅在产量闸门通过时生成；
8. `Fig08_typhoon_case`：2025办内基线预测与实际0产量；
9. `Fig09_scenario_sensitivity`：暖冬和秋梢老熟推迟响应。

所有图同时输出PNG和PDF，并生成图注文件。

---

# 18. 最终报告必须直接回答的问题

`reports/FINAL_EXPERIMENT_REPORT.md` 必须按以下顺序回答：

1. 有多少个完整P1、P2、P3转换样本？
2. 有多少个正常产年独立产量样本？
3. 2025办内在物候主分析中是否被使用，依据是什么？
4. P1到底预测什么，最佳模型是什么，LOYO误差是多少天？
5. P2和P3是否能稳定预测？
6. 非线性温度响应是否优于简单低温日数？
7. 水分调节是否带来稳定增益？
8. W2实测动态窗口是否优于W1固定窗口？
9. W3预测动态窗口是否仍优于W1？
10. 正常产量模型是否稳定优于果园历史均值？
11. 加入预测物候后，产量预测是否改善？
12. 2025办内的正常生产基线预测是多少，区间多宽，实际偏离多大？
13. 暖冬和秋梢老熟推迟分别让抽穗日期改变多少？
14. 当前证据应归类为“可预测”“关联解释”还是“当前不支持”？
15. 下一年度最应补充哪些观测？

---

# 19. 推荐执行顺序和提交节点

## Commit 1：工程骨架与原始数据冻结

```text
建立分支、目录、配置、输入哈希和运行入口
```

## Commit 2：数据标准化与可行性报告

```text
生成三张标准表、区块审计、台风编码、analysis_gate.json
```

**必须先提交本阶段结果，后续实验根据闸门执行。**

## Commit 3：描述性分析与P1基线

```text
生成时间轴、气象叠加图、P1-B0/P1-B1/P1-B2
```

## Commit 4：P1生理模型与LOYO验证

```text
完成P1-M1至允许执行的最高复杂度模型
输出参数稳定性和结论等级
```

## Commit 5：P2/P3与交叉拟合动态窗口

```text
完成P2/P3、W1/W2/W3及窗口比较
```

## Commit 6：有条件的产量模型

```text
仅在产量闸门通过时执行Y-B0至Y-W3P及允许的扩展
```

## Commit 7：台风案例和情景推演

```text
完成2025办内模型外案例；仅在模型通过对应闸门时执行情景
```

## Commit 8：图表、测试和最终报告

```text
pytest通过；一条命令可重建；完成FINAL_EXPERIMENT_REPORT.md
```

推送分支：

```text
codex/litchi-phenology-yield-r2
```

不得直接向 `main` 提交。

---

# 20. Codex最终回复格式

```text
1. 分支名称
2. 最新提交哈希
3. 运行命令
4. pytest结果
5. 数据清单和标准化样本数
6. P1、P2、P3完整样本数
7. 正常产量样本数和灾害样本数
8. 2025办内在各分析中的处理方式
9. analysis_gate.json结论
10. 已执行和被闸门阻止的实验ID
11. P1/P2/P3 LOYO指标
12. W1/W2/W3比较结果
13. 产量模型是否通过预测判据
14. 2025办内台风案例结果
15. 情景推演结果
16. 主要文件和图表路径
17. 未解决问题及原因
```

---

# 21. 本轮最重要的执行原则

本轮必须按以下优先级执行：

```text
第一优先：P1，预测秋梢老熟后的抽穗日期
第二优先：P2/P3，预测盛花和成熟日期
第三优先：验证动态物候窗口是否优于固定月份
第四优先：在样本闸门通过后预测正常产量
第五优先：把2025办内作为台风灾害偏离案例
第六优先：只对验证通过的模型做情景敏感性推演
```

不得因为产量模型未成功而判定整个研究失败。若P1物候预测可靠、动态窗口具有优势，本研究仍可形成一篇以“气象驱动的荔枝物候预测与动态窗口分析”为核心的论文。
