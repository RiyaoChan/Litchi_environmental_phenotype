# 荔枝 R4 精确果园气象—物候—产量实验执行计划 V3（交由 Codex 执行）

> 仓库：`RiyaoChan/Litchi_environmental_phenotype`  
> 基线分支：`codex/litchi-orchard-weather-r4`  
> 基线提交：`556d0293d3f162142f2a9f321489d620e500a7ce`  
> 建议新工作分支：`codex/litchi-r4-phenology-yield-v3`  
> 本轮核心原则：**先证明果园定位气象能否提供超越历史日期规律的物候预测信息，再研究动态物候窗口与正常产量；不以“多模型”本身作为论文贡献。**

---

# 0. 本轮研究的唯一主线

本轮研究必须围绕以下一个连续科学问题展开：

```text
果园定位的逐日/逐小时气象
        ↓
气象累积是否能够预测关键物候转换？
        ↓
预测出的物候能否用于构建无未来信息泄漏的动态气象窗口？
        ↓
动态窗口是否比固定日历窗口更能解释/预测正常产年的产量？
        ↓
若模型验证成立，再进行暖冬、秋梢推迟等气象情景推演
```

论文中的模型不是彼此独立的四个故事，而应组织为一个 **sequential phenology–weather–yield framework**：

```text
秋梢老熟
   │  P1：低温/水分诱导
   ↓
抽穗
   │  P2：热量积累
   ↓
盛花
   │  P3：热量/高温/辐射
   ↓
成熟
   │
   └──→ 阶段气象窗口 → 正常产量
```

---

# 1. 必须锁定的数据事实

## 1.1 R4 主气象数据

本轮正式主分析只允许使用三果园精确定位的 R4 数据：

```text
data/external/open_meteo_era5_orchards/weather_daily_era5_orchards.csv

data/external/open_meteo_era5_orchards/weather_hourly_era5_orchards.csv.gz

data/external/open_meteo_era5_orchards/download_metadata.json

data/external/open_meteo_era5_orchards/variable_dictionary.csv
```

时间范围：

```text
2021-08-01 ～ 2026-06-30
```

理论完整度：

```text
3 果园 × 1795 日 = 5385 个 orchard-day
3 果园 × 43080 小时 = 129240 个 orchard-hour
```

三个果园坐标：

| orchard_id | 果园 | 纬度 | 经度 |
|---|---|---:|---:|
| `bannei` | 办内果园 | 19.899341667 | 110.499494444 |
| `hongming` | 红明农场 | 19.698605556 | 110.580541667 |
| `luhong` | 鲁宏果园 | 18.609658333 | 109.942294444 |

R4 数据属于 **orchard-specific gridded ERA5 reanalysis**，不是果园现场气象站实测。报告和论文中不得写成“果园实测气象”。

## 1.2 R4 可用变量

逐日核心变量包括但不限于：

```text
tmean_c
tmin_c
tmax_c
precip_mm
rain_mm
precipitation_hours
relative_humidity_mean_pct
relative_humidity_min_pct
relative_humidity_max_pct
dewpoint_mean_c
vpd_max_kpa
sunshine_h
shortwave_radiation_mj_m2
wind_speed_mean_ms
wind_speed_max_ms
et0_mm
soil_moisture_0_7cm_mean_m3_m3
soil_moisture_7_28cm_mean_m3_m3
soil_moisture_28_100cm_mean_m3_m3
soil_temperature_* 
```

逐小时数据包括：

```text
temperature_c
relative_humidity_pct
dewpoint_c
vpd_kpa
precip_mm
rain_mm
cloud_cover_pct
shortwave_radiation_w_m2
wind_speed_ms
et0_mm
soil_moisture_0_7cm_m3_m3
soil_moisture_7_28cm_m3_m3
soil_moisture_28_100cm_m3_m3
soil_temperature_0_7cm_c
soil_temperature_7_28cm_c
```

**禁止把所有变量一次性投入模型。** 小样本下必须按生物学阶段预注册少量候选变量。

## 1.3 物候年份规则

`物候期.xlsx` 的 A 列表示产季/收获年份 `Y`。

完整日期已按跨年产季解释：

- 秋梢老熟通常属于 `Y-1`；
- 12 月露白属于 `Y-1`；
- 1 月及之后的抽穗、开花、坐果、成熟属于 `Y`；
- 群体谢花、初始坐果、生理落果可以重叠，不得为制造顺序而改月日。

继续沿用当前标准化后的：

```text
data/processed/phenology_event_long.csv
```

不得重新凭 Excel 底层错误年份推翻已确认的跨年日期。

## 1.4 测产年份规则

最终确认：

```text
测产.xlsx!A39 = 2026
```

不得再把 A39 改回 2025。

## 1.5 2025 办内台风/放弃投产

必须保留：

```text
orchard_id = bannei
harvest_year = 2025
final_yield_kg_per_mu = 0
normal_production_year = 0
typhoon_damage = 1
```

2025 办内：

- 最终产量 `0` 是真实结果，不是 NA；
- 未测单株产量、单果重、果数仍为 NA；
- 不进入“正常气象—物候—产量关系”主模型训练；
- 可进入描述性结果和灾害案例；
- 早期物候是否纳入主物候模型必须沿用当前 `phenology_main_eligible` / `phenology_sensitivity_eligible` 规则；
- 不训练绝收分类器、零膨胀模型或“台风损失模型”。

## 1.6 红明 2025 / 2026

年度总结提示红明受台风影响并处于恢复阶段。

主分析默认：

```text
hongming_2025: yield_main_eligible = 0
hongming_2026: yield_main_eligible = 0
```

敏感性分析允许分别加入：

```text
SENS-HM25
SENS-HM26
SENS-HM25-26
```

不得在不说明恢复状态的情况下把它们当作普通正常产年。

---

# 2. 本轮预注册研究问题与假设

本轮只围绕 5 个研究问题展开。

## RQ1 / H1：气象信息能否优于历史物候规律预测抽穗？

主任务：

```text
autumn_flush_mature → inflorescence_emergence
```

零假设：加入气象后并不能稳定优于“同果园历史中位持续天数”。

成功标准不是训练拟合度，而是 **按完整产季留出的 LOYO 预测误差**。

## RQ2 / H2：小时尺度低温信息是否优于日尺度温度？

比较：

```text
日尺度低温日数 / 冷量累积
vs
小时尺度低温小时 / 冷量小时累积
vs
低参数非线性温度响应
```

如果小时尺度没有稳定增益，不得因“更精细”而强行采用。

## RQ3 / H3：抽穗后和盛花后的发育是否可由热量积累预测？

两个任务：

```text
P2: inflorescence_emergence → full_bloom
P3: full_bloom → maturity
```

优先检验低参数 GDD/thermal-time 模型，不先上复杂 ML。

## RQ4 / H4：动态物候窗口是否优于固定日历窗口？

必须区分：

```text
W1-CALENDAR：固定日历窗口
W1-MEDIAN：只用训练年份估计的典型物候窗口
W2-OBS：实测物候窗口（回顾性上限，不可称部署预测）
W3-PRED：交叉拟合预测物候窗口（可部署形式）
```

核心比较：

```text
W2-OBS > W1 ?
W3-PRED 是否接近 W2-OBS 且优于 W1 ?
```

## RQ5 / H5：动态窗口能否改善正常产量预测？

只在产量数据闸门通过后执行。

比较：

```text
历史产量基线
固定日历气象
实测动态窗口气象
预测动态窗口气象
```

如果预测动态窗口不能稳定超过历史产量基线，不把文章定位为“产量预测模型论文”。

---

# 3. 分析单位与防伪重复原则

## 3.1 真正独立单位

主要统计独立单位：

```text
orchard_id × harvest_year
```

日数据和小时数据只是同一个果园—产季的时间序列输入，不增加独立样本数。

严禁：

- 把 129240 个小时当成 129240 个独立训练标签；
- 把同一果园—同一年 A/B/C 树类随机拆到训练与测试；
- 按单日随机分割训练/测试；
- 按树随机 8:2 划分后报告产量泛化精度。

## 3.2 交叉验证主协议

主验证：

```text
LOYO = Leave-One-Harvest-Year-Out
```

每一折必须把该 `harvest_year` 的所有果园一起留出。

例如：

```text
holdout=2024
train={2022, 2023, 2025, 2026} 中所有 eligible season
validation={2024 中所有 eligible season}
```

所有阈值、基础温度、正则参数、响应函数参数只能在训练折内确定。

## 3.3 前向滚动验证

作为更接近真实生产预测的次级验证：

```text
train 2022-2023 → test 2024
train 2022-2024 → test 2025
train 2022-2025 → test 2026
```

若某测试年含灾害/恢复样本，按主分析 eligibility 排除，并另做敏感性报告。

不得用 2026 数据预测 2024 后再称为“真实未来预测”；LOYO 和 rolling-origin 的语义必须分开。

---

# 4. Phase 0：R4 数据接管与数据闸门

## 4.1 新建配置

创建：

```text
configs/r4_experiment_v3.yaml
configs/r4_phenology_models.yaml
configs/r4_weather_windows.yaml
configs/r4_yield_models.yaml
configs/r4_scenarios.yaml
```

`r4_experiment_v3.yaml` 必须明确：

```yaml
weather_main_daily: data/external/open_meteo_era5_orchards/weather_daily_era5_orchards.csv
weather_main_hourly: data/external/open_meteo_era5_orchards/weather_hourly_era5_orchards.csv.gz
weather_metadata: data/external/open_meteo_era5_orchards/download_metadata.json
weather_role: orchard_specific_era5_main
```

旧数据：

```text
data/external/open_meteo_era5/weather_daily_era5.csv
```

仅允许作为区域代理敏感性分析，不得继续作为 R4 主输入。

## 4.2 R4 数据完整性测试

必须自动验证：

```text
3 orchards
5385 daily rows
129240 hourly rows
1795 daily dates / orchard
43080 hourly timestamps / orchard
2021-08-01 ～ 2026-06-30
no duplicate orchard-date
no duplicate orchard-time
main modeled variables no NA
```

温度基本物理规则：

```text
tmin <= tmean <= tmax
```

小时数据：

```text
0 <= RH <= 100
VPD >= 0
precip >= 0
0 <= soil_moisture <= 1
```

## 4.3 三果园网格独立性

输出：

```text
results/r4/qc/grid_identity.csv
```

至少包含：

```text
orchard_id
requested_latitude
requested_longitude
grid_latitude
grid_longitude
elevation_m
```

并计算任意两果园逐日 `tmean_c`、`precip_mm` 是否完全相同。

禁止因为两个海口果园距离较近就人为复制同一序列。

## 4.4 构建 R4 master table

创建：

```text
data/processed/r4_orchard_season_master.csv
```

一行一个果园—产季，至少包含：

```text
season_id
orchard_id
cultivar
harvest_year
normal_production_year
typhoon_damage
yield_main_eligible
phenology_main_eligible
phenology_sensitivity_eligible
final_yield_kg_per_mu
mean_yield_per_tree_kg
fruit_number_proxy
秋梢老熟日期
露白日期
抽穗日期
盛花日期
成熟日期
```

## 4.5 Phase 0 验收

输出：

```text
results/r4/qc/analysis_gate_r4.json
reports/r4/00_R4_DATA_GATE_REPORT.md
```

若天气完整度不是 100%，先修数据，不进入模型。

---

# 5. Phase 1：描述性“气象—物候”事实图，不做模型选择

目的：先看真实生物学差异，避免直接盲目优化模型。

## 5.1 每个果园—产季计算阶段持续时间

计算：

```text
D1 = 抽穗 - 秋梢老熟
D1a = 露白 - 秋梢老熟（有记录时）
D1b = 抽穗 - 露白（有记录时）
D2 = 盛花 - 抽穗
D3 = 成熟 - 盛花
```

## 5.2 生成天气叠加图

每个果园分别画 2022-2026 产季：

- 日平均/最低温曲线；
- 日降雨柱；
- 关键物候垂线；
- 秋梢老熟至抽穗的累计低温指标；
- 抽穗至盛花 GDD；
- 盛花至成熟 GDD。

## 5.3 只做描述，不用全数据挑最优阈值

可展示候选阈值曲线：

```text
T < 22°C
T < 20°C
T < 18°C
T < 15°C
```

但禁止根据全数据肉眼选一个阈值后再拿同一数据做验证。

输出：

```text
results/r4/descriptive/stage_duration.csv
results/r4/descriptive/stage_weather_summary.csv
results/r4/figures/Fig_R4_01_phenology_weather_timeline.*
reports/r4/01_R4_DESCRIPTIVE_REPORT.md
```

---

# 6. Phase 2：P1 秋梢老熟 → 抽穗（核心主模型）

P1 是整篇研究的第一优先级。

## 6.1 主目标

```text
start = autumn_flush_mature
end   = inflorescence_emergence
```

输出完整预测日期，不只预测持续天数。

## 6.2 基线模型

### P1-B0：同果园历史持续天数中位数

沿用 R2 已实现的思想：

```text
predicted_date = observed_autumn_flush_date
               + median(training-year duration for same orchard)
```

若同园训练样本不足，回退 pooled training median。

### P1-B1：同果园历史抽穗日历日期中位数

只使用训练年份。

P1 所有气象模型必须与 P1-B0/B1 在完全相同测试样本上比较。

## 6.3 日尺度候选模型

### P1-D1：低温日数阈值模型

候选温度阈值只允许：

```text
22°C, 20°C, 18°C, 15°C
```

候选统计量：

```text
count(tmean < threshold)
count(tmin  < threshold)
```

事件条件：训练折内估计累计低温日数阈值 `C*`。

**阈值选择必须嵌套在训练折内部。**

### P1-D2：冷量度日（cold degree-day）

对候选基准温度：

```text
Tb ∈ {18, 20, 22} °C
```

计算：

```text
CDD_d = max(0, Tb - Tmean_d)
Cumulative_CDD = Σ CDD_d
```

训练折估计达到抽穗的 `CDD*`。

## 6.4 小时尺度候选模型

### P1-H1：低温小时数

候选温度：

```text
T < 22°C
T < 20°C
T < 18°C
T < 15°C
```

从每个果园实际秋梢老熟日期 00:00 开始累计。

### P1-H2：冷量小时（cold degree-hours）

```text
CDH_h = max(0, Tb - temperature_h)
Tb ∈ {18, 20, 22} °C
```

训练折估计 `CDH*`。

### P1-H3：低参数非线性温度响应

优先实现一个参数数目受到严格限制的温度响应函数，例如：

- triangular / trapezoid response；或
- beta response，但必须限制参数范围且避免自由参数过多。

原则：

```text
适宜低温贡献高
过高温度贡献趋近 0
极端低温不允许被模型无约束地赋予无限贡献
```

禁止在 12 左右独立样本上拟合 6-10 个自由参数。

建议：

- 形状参数使用文献合理范围 + 训练折网格；
- 每折保存候选参数、训练目标值和最终选择；
- 若参数跨折极不稳定，判定为不可识别，不作为主模型。

## 6.5 水分扩展只能在温度模型验证后执行

### P1-W1：最佳温度模型 + 水分背景

只允许从以下候选中增加 **1 个** 水分指标：

```text
P_minus_ET0 = Σ(precip_mm - et0_mm)
dry_days = count(precip_mm < 0.1)
mean_vpd = mean(hourly vpd_kpa)
root_zone_soil_moisture = mean(soil_moisture_7_28cm or 28_100cm)
```

不得一次加入 4 个。

训练折内部比较哪个单变量扩展最有增益。

只有当：

```text
best temperature-only weather model < P1-B0 MAE
```

后，P1-W1 才有资格进入“机制扩展”比较。

## 6.6 P1 验证指标

每个模型必须输出：

```text
n_predictions
MAE_days
RMSE_days
median_AE_days
mean_bias_days
Spearman_r
per-fold MAE
per-orchard MAE
```

另输出相对于 P1-B0：

```text
delta_MAE_days
relative_MAE_reduction_pct
```

## 6.7 P1 稳定性判定

天气模型只有同时满足以下条件，才能称为“优于历史基线”：

1. pooled LOYO MAE < P1-B0；
2. 在至少 3 个 harvest-year holdout 中，MAE 不高于 P1-B0；
3. 总改善不能主要由单一测试年贡献；若移除最佳改善年后结论反转，标记 `fragile`；
4. rolling-origin 结果方向不与 LOYO 明显冲突；
5. 模型参数在不同折间具有基本可解释性，不出现极端边界解。

不要设置“必须提高 15%”之类没有生物学依据的硬阈值；报告实际改善和不确定性。

## 6.8 P1 输出

```text
results/r4/phenology/P1_model_comparison.csv
results/r4/phenology/P1_cv_predictions.csv
results/r4/phenology/P1_fold_metrics.csv
results/r4/phenology/P1_parameters_by_fold.csv
results/r4/phenology/P1_stability_diagnostics.csv
results/r4/figures/Fig_R4_02_P1_observed_vs_predicted.*
results/r4/figures/Fig_R4_03_P1_cumulative_response_examples.*
reports/r4/02_P1_PHENOLOGY_MODEL_REPORT.md
```

---

# 7. Phase 3：露白辅助任务（不抢主线）

若 `white_tip` 定义和样本完整度足够，执行：

```text
P1A: autumn_flush_mature → white_tip
P1B: white_tip → inflorescence_emergence
```

目的：判断“秋梢→抽穗”是否可以分解为：

```text
花芽诱导阶段
+
花序显现阶段
```

模型优先使用 P1 已验证的温度响应形式，不重新大规模搜索新模型。

如果 white-tip 样本不足或定义不一致：

```text
status = exploratory_only
```

不得阻塞 P2/P3。

---

# 8. Phase 4：P2 抽穗 → 盛花

## 8.1 研究目标

检验抽穗后开花进程主要是否由热量积累控制。

## 8.2 基线

```text
P2-B0：同果园历史 D2 中位数
```

## 8.3 P2-M1：GDD 模型

候选基础温度只允许：

```text
Tb ∈ {5, 8, 10, 12, 15} °C
```

计算：

```text
GDD_d = max(0, Tmean_d - Tb)
```

训练折内：

1. 选择 `Tb`；
2. 估计同园或部分汇聚的热量阈值 `GDD*`；
3. 对留出年份预测盛花日期。

不要用测试年真实盛花日期估计阈值。

## 8.4 P2-M2：受限辐射扩展

只有 P2-M1 优于 P2-B0 后才运行。

允许加入：

```text
mean_shortwave_radiation
```

或：

```text
sunshine_h
```

二选一，不同时加入。

若没有稳定增益，保留 P2-M1。

## 8.5 P2 输出

与 P1 同格式：

```text
P2_model_comparison.csv
P2_cv_predictions.csv
P2_parameters_by_fold.csv
P2_stability_diagnostics.csv
03_P2_PHENOLOGY_MODEL_REPORT.md
```

---

# 9. Phase 5：P3 盛花 → 成熟

## 9.1 基线

```text
P3-B0：同果园历史 D3 中位数
```

## 9.2 P3-M1：GDD 模型

候选：

```text
Tb ∈ {5, 8, 10, 12, 15} °C
```

注意红明为白糖罂，办内/鲁宏为妃子笑；当前“品种”和“果园”并非完全可分离。

因此禁止声称：

```text
白糖罂的温度阈值显著高/低于妃子笑
```

除非另有同地多品种数据支持。

主模型可以采用：

- shared base temperature + orchard-specific/shrunk heat threshold；或
- 每果园训练折历史 heat-sum 中位阈值。

## 9.3 P3-M2：高温/辐射受限扩展

只有 P3-M1 优于 P3-B0 后运行。

候选只允许增加 1 个：

```text
heat_days_gt_32C
heat_hours_gt_32C
mean_shortwave_radiation
P_minus_ET0
```

用训练折内部选择。

## 9.4 P3 输出

同 P1/P2。

---

# 10. Phase 6：动态气象窗口实验

这一阶段是论文方法学亮点，但必须严防未来信息泄漏。

## 10.1 预定义四套窗口

### W1-CALENDAR：固定日历窗口

固定，不根据测试年物候调整：

```text
Induction:  Sep 01 (Y-1) → Jan 31 (Y)
Flowering:  Jan 01 (Y)   → Mar 31 (Y)
FruitDev:   Mar 01 (Y)   → May 31 (Y)
```

如果需要改固定窗口，只允许在实验开始前统一修改配置，不允许看完结果后反复寻找最好月份。

### W1-MEDIAN：训练折典型物候窗口

每个 LOYO 折内，只根据训练年份的物候边界中位数确定该果园典型窗口。

这是比死板固定月份更强的基线。

### W2-OBS：实测动态物候窗口

```text
秋梢老熟 → 抽穗
抽穗 → 盛花
盛花 → 成熟
```

这是回顾性“oracle/upper-bound”窗口。

**W2-OBS 可用于机制解释和上限比较，但不能称为可实时部署预测，因为它使用了未来真实物候日期。**

### W3-PRED：交叉拟合预测物候窗口

对每个测试 season：

- 用该 fold 训练得到的 P1/P2/P3 模型预测阶段日期；
- 用预测日期形成窗口；
- 不得调用测试 season 真实未来物候日期。

这是实际可部署形式。

## 10.2 每阶段只提取预注册指标

### Induction window

优先：

```text
best_P1_temperature_metric
P_minus_ET0
dry_days
```

最多保留 2 个。

### Flowering window

候选：

```text
precip_mm_total
precipitation_hours
rainy_days_ge_1mm
mean_radiation
mean_vpd
```

预注册主指标：

```text
precipitation_hours
mean_shortwave_radiation
```

### Fruit development window

候选：

```text
GDD
heat_days_gt_32C
shortwave_radiation_sum
P_minus_ET0
```

预注册主指标：

```text
GDD
heat_days_gt_32C
```

严禁把几十个 ERA5 变量全部汇总后做“自动特征筛选”。

## 10.3 输出

```text
results/r4/windows/W1_calendar_features.csv
results/r4/windows/W1_median_features.csv
results/r4/windows/W2_observed_features.csv
results/r4/windows/W3_predicted_features.csv
results/r4/windows/window_alignment_diagnostics.csv
reports/r4/05_DYNAMIC_WINDOW_REPORT.md
```

---

# 11. Phase 7：正常产年产量模型（有条件执行）

## 11.1 进入闸门

只有同时满足：

```text
normal eligible orchard-season >= 10
unique harvest years >= 4
R4 dynamic/fixed features complete
no duplicate season used as independent sample
Bannei 2025 excluded from normal fit
Hongming 2025/2026 main excluded unless protocol explicitly changed
```

才运行正式产量模型。

## 11.2 产量主目标

```text
final_yield_kg_per_mu
```

次级：

```text
mean_yield_per_tree_kg
```

探索性：

```text
fruit_number_proxy
mean_single_fruit_weight_g
```

如果次级/探索性缺失过多，不得插补后强行建模。

## 11.3 基线模型

### Y-B0：同果园历史产量中位数

每个 LOYO fold 只使用训练年份。

### Y-B1：pooled historical median + orchard intercept

仅作补充。

## 11.4 主产量模型只采用低维 Ridge

不把 RF/XGBoost/深度学习作为主模型。

统一使用 Ridge 回归，原因：

- 样本极少；
- 特征存在相关性；
- 需要稳定、可解释的窗口比较；
- 算法固定后可以把研究重点放在“窗口是否有效”而不是“谁的算法分数高”。

所有模型使用完全相同的正则化流程和特征标准化；`alpha` 必须嵌套在训练 fold 内选择。

## 11.5 产量实验矩阵

### Y-W1C

```text
固定日历 W1-CALENDAR features → yield
```

### Y-W1M

```text
训练折典型 W1-MEDIAN features → yield
```

### Y-W2O

```text
实测动态 W2-OBS features → yield
```

这是 retrospective upper bound。

### Y-W3P

```text
交叉拟合预测动态 W3-PRED features → yield
```

这是论文中真正的“可预测”版本。

### Y-W3P+PHENO（只做一次有限扩展）

允许加入最多 2 个预测物候变量：

```text
predicted_inflorescence_date_offset
predicted_full_bloom_date_offset
```

目的：检验“物候本身”是否有超越阶段气象的附加信息。

## 11.6 产量特征数量上限

主模型最终输入不得超过：

```text
6 个连续特征 + 必要的果园编码
```

推荐核心 5 个：

```text
1. P1 最佳低温/诱导指标
2. induction P-ET0
3. flowering precipitation_hours
4. fruit-development GDD
5. fruit-development heat_days_gt_32C
```

第 6 个可选：

```text
flowering mean radiation
```

## 11.7 产量评价

输出：

```text
MAE
RMSE
median_AE
Spearman_r
normalized_MAE = MAE / mean(observed_yield)
per-fold error
per-orchard error
```

不要主要依赖 R²；小 n 下 R² 极不稳定。

## 11.8 产量“成功”判定

若：

```text
Y-W3P pooled LOYO MAE < Y-B0
并且
Y-W3P 至少不劣于 Y-W1C/W1M 的主要折
```

才允许在论文中称为“yield prediction/forecasting”。

若：

```text
W2-OBS 明显优于 W1
但 W3-PRED 无法保持增益
```

论文应解释为：

> 实测物候对齐有解释价值，但当前物候预测误差会削弱部署型产量预测。

若所有产量模型均不优于 Y-B0：

> 不把产量预测作为论文主贡献；保留为探索性“stage-specific weather–yield association”。

---

# 12. Phase 8：2025 办内灾害案例

只有在正常产量模型通过基本验证后运行。

## 12.1 实际事实

```text
actual_yield = 0 kg/mu
```

## 12.2 模型输出

使用不含 2025 办内训练信息的正常产量模型，得到：

```text
model_based_normal_production_reference
```

并计算：

```text
reference_yield - actual_yield
```

但必须写成：

> model-based normal-production reference gap

不得写成：

> causal typhoon yield loss

因为：

- 只有一个结构性绝收案例；
- 管理策略在 2025-03-01 后已改变；
- 缺乏完整风害剂量—响应数据。

输出：

```text
results/r4/typhoon/bannei_2025_reference.csv
reports/r4/07_TYPHOON_CASE_REPORT.md
```

---

# 13. Phase 9：情景推演（必须受模型验证闸门约束）

情景推演不是重新拟合模型，只改变输入天气后用已固定模型预测。

## 13.1 S1 暖冬情景：P1

仅在 P1 气象模型优于基线后执行。

对每个历史 P1 窗口：

```text
+0.5°C
+1.0°C
+1.5°C
+2.0°C
```

保持温度内部关系一致。

输出：

```text
抽穗日期变化（days）
有效低温累积变化
是否无法在观察季内达到诱导阈值
```

## 13.2 S2 秋梢老熟推迟

```text
+7 days
+14 days
+21 days
```

气象序列不变，仅将累计起点后移。

回答：

> 秋梢老熟过晚会损失多少有效低温窗口，并导致抽穗推迟多少？

这是非常重要的生产管理情景。

## 13.3 S3 暖冬 × 秋梢推迟联合作用

有限组合：

```text
(+1°C, +7d)
(+1°C, +14d)
(+2°C, +7d)
(+2°C, +14d)
```

不要建立巨大情景网格。

## 13.4 S4 P2/P3 升温情景

只有对应 P2/P3 热量模型优于基线后：

```text
+1°C
+2°C
```

输出盛花、成熟日期的变化。

## 13.5 S5 产量气象扰动

只有 Y-W3P 验证成立后，作为探索性分析：

```text
flowering precipitation +20%
flowering precipitation -20%
fruit-stage temperature +1°C
fruit-stage heat event +5 days equivalent
```

不得把小样本情景结果当作精确产量损失预测。

---

# 14. 敏感性分析

## 14.1 台风/恢复样本

至少报告：

```text
MAIN：排除 bannei2025 + hongming2025/2026
SENS-1：加入 hongming2025
SENS-2：加入 hongming2026
SENS-3：加入 hongming2025+2026
```

2025 办内零产量不得加入正常产量拟合，仅可做外部压力测试。

## 14.2 日尺度 vs 小时尺度 P1

必须直接比较：

```text
P1-D1/D2
vs
P1-H1/H2/H3
```

如果小时模型参数更复杂但 MAE 没改善，优先采用更简单日模型。

## 14.3 精确果园 R4 vs 旧区域代理天气

只在模型完成后做一次辅助敏感性：

```text
R4 orchard-specific ERA5
vs
R3 regional proxy ERA5
```

主结论必须来自 R4。

## 14.4 2025 办内早期物候

保持现有：

```text
main excluded
sensitivity eligible where valid
```

对 P1 报告包含/排除敏感性。

---

# 15. 模型选择与小样本限制：Codex 必须遵守

## 15.1 禁止全数据调参

任何：

- 温度阈值；
- GDD base temperature；
- chilling threshold；
- non-linear response parameter；
- Ridge alpha；

都必须在训练 fold 内确定。

## 15.2 禁止大规模特征搜索

不得：

```text
自动生成数百种温度阈值 × 时间窗口 × 水分指标
然后挑 LOYO 最好的一个
```

这会在 12 左右样本上产生严重 researcher degrees of freedom。

## 15.3 禁止把样本内拟合指标作为主要证据

必须优先报告：

```text
cross-fitted / held-out prediction
```

训练集 R²、AIC 可以作为补充，不能代替 LOYO。

## 15.4 不做复杂深度学习

本轮禁止：

- LSTM；
- Transformer；
- 深度时序网络；
- 大型 XGBoost 网格搜索；
- Random Forest 作为主模型。

原因不是技术不能做，而是独立终点样本过少。

---

# 16. 代码实现建议

在已有代码基础上新增/扩展：

```text
src/r4_weather_loader.py
src/phenology_models.py
src/phenology_cv.py
src/r4_stage_features.py
src/yield_models.py
src/yield_cv.py
src/scenario_simulation.py
src/r4_reporting.py
```

命令行建议：

```bash
python -m src.cli r4-qc --config configs/r4_experiment_v3.yaml
python -m src.cli r4-describe --config configs/r4_experiment_v3.yaml
python -m src.cli r4-p1 --config configs/r4_experiment_v3.yaml
python -m src.cli r4-p2 --config configs/r4_experiment_v3.yaml
python -m src.cli r4-p3 --config configs/r4_experiment_v3.yaml
python -m src.cli r4-windows --config configs/r4_experiment_v3.yaml
python -m src.cli r4-yield --config configs/r4_experiment_v3.yaml
python -m src.cli r4-scenarios --config configs/r4_experiment_v3.yaml
python -m src.cli r4-all --config configs/r4_experiment_v3.yaml
```

旧 R2/R3 结果不覆盖，全部输出到：

```text
results/r4/
reports/r4/
```

---

# 17. 必须新增的自动测试

至少包括：

## Weather

```text
test_r4_daily_row_count
test_r4_hourly_row_count
test_r4_exact_orchard_coordinates
test_r4_daily_continuity
test_r4_hourly_continuity
test_r4_no_duplicate_dates
test_r4_temperature_order
```

## Phenology CV

```text
test_loyo_holds_entire_year
test_no_holdout_year_in_parameter_fit
test_threshold_selection_train_only
test_predicted_date_after_observed_start
test_w3_uses_cross_fitted_phenology_only
```

## Yield

```text
test_bannei_2025_excluded_from_normal_yield_fit
test_hongming_damage_main_exclusion
test_tree_classes_not_split_across_cv
test_ridge_scaler_fit_on_training_only
test_yield_feature_count_limit
```

## Scenario

```text
test_scenario_does_not_refit_model
test_warming_perturbation_applies_only_to_temperature
test_flush_delay_changes_start_date_not_weather_history
```

---

# 18. 实验编号总表

| ID | 实验 | 必须执行？ | 进入条件 |
|---|---|---|---|
| R4-QC | R4 三果园数据闸门 | 是 | 无 |
| R4-DESC | 气象—物候描述 | 是 | R4-QC pass |
| P1-B0 | 历史持续时间基线 | 是 | 日期完整 |
| P1-B1 | 历史日期基线 | 是 | 日期完整 |
| P1-D1 | 日尺度低温日数 | 是 | R4-QC pass |
| P1-D2 | 日尺度 cold degree-day | 是 | R4-QC pass |
| P1-H1 | 小时低温小时数 | 是 | hourly pass |
| P1-H2 | cold degree-hours | 是 | hourly pass |
| P1-H3 | 低参数非线性温度响应 | 是 | hourly pass |
| P1-W1 | 温度 + 1个水分变量 | 条件 | 温度模型优于基线 |
| P1A/B | 露白分解任务 | 探索 | 样本定义足够 |
| P2-B0 | P2历史基线 | 是 | 日期完整 |
| P2-M1 | GDD | 是 | daily pass |
| P2-M2 | GDD + radiation | 条件 | P2-M1优于B0 |
| P3-B0 | P3历史基线 | 是 | 日期完整 |
| P3-M1 | GDD | 是 | daily pass |
| P3-M2 | GDD + 1项胁迫 | 条件 | P3-M1优于B0 |
| W1-C | 固定日历窗口 | 是 | 阶段天气完整 |
| W1-M | 训练折中位物候窗口 | 是 | 日期完整 |
| W2-O | 实测动态窗口 | 是 | 日期完整 |
| W3-P | 预测动态窗口 | 是 | P1/P2/P3 cross-fit可用 |
| Y-B0 | 历史产量基线 | 条件 | yield gate pass |
| Y-W1C | 固定日历气象→产量 | 条件 | yield gate pass |
| Y-W1M | 典型物候气象→产量 | 条件 | yield gate pass |
| Y-W2O | 实测动态气象→产量 | 条件 | yield gate pass |
| Y-W3P | 预测动态气象→产量 | 条件 | yield gate pass |
| TY-2025 | 办内2025灾害案例 | 条件 | 正常产量模型有效 |
| S1-S4 | 物候情景推演 | 条件 | 对应模型优于基线 |
| S5 | 产量情景 | 探索 | Y-W3P有效 |

---

# 19. 分阶段提交策略

Codex 不要把所有工作塞进一个巨大提交。

建议：

## Commit A：R4 接管与数据闸门

```text
Use exact-orchard R4 weather as primary analysis source
```

必须先提交 QC、配置、master table。

## Commit B：P1 模型

```text
Add nested-LOYO daily and hourly P1 phenology models
```

先把 P1 跑完整并生成报告。

## Commit C：P2/P3

```text
Add thermal-time P2 and P3 phenology models
```

## Commit D：动态窗口

```text
Add observed and cross-fitted phenology-aligned weather windows
```

## Commit E：产量模型

只有闸门通过：

```text
Add low-dimensional normal-year yield comparison
```

## Commit F：情景与最终报告

```text
Add validated weather scenarios and final R4 experiment report
```

每个提交后执行：

```bash
python -m pytest -q
python scripts/verify.py
```

若旧 `verify.py` 未覆盖 R4，应扩展为 `scripts/verify_r4.py`。

---

# 20. 最终必须回答的 12 个问题

Codex 最终报告不能只堆文件，必须逐条回答：

1. R4 三果园逐日和逐小时气象是否 100% 连续？
2. 办内、红明、鲁宏是否实际对应不同的 ERA5 网格/序列？
3. P1-B0 当前历史持续时间基线 MAE 是多少？
4. 最佳日尺度气象 P1 模型 MAE 是多少？
5. 最佳小时尺度 P1 模型 MAE 是多少？
6. 小时尺度是否稳定优于日尺度和历史基线？
7. P1 加水分信息是否有独立增益？
8. P2/P3 GDD 是否优于历史持续时间基线？
9. W2-OBS 是否比 W1-CALENDAR / W1-MEDIAN 更有解释力？
10. W3-PRED 能否保留 W2-OBS 的大部分优势？
11. 正常产年 Y-W3P 是否稳定优于历史产量基线？
12. 根据上述证据，论文最终应定位为：
    - A：多阶段物候预测 + 气候情景；
    - B：物候预测 + 动态窗口 + 正常产量预测；
    - C：气象—物候机制分析，产量仅探索性？

---

# 21. 最终报告必须生成的核心图

## Figure 1

三果园位置与顺序物候—气象框架。

## Figure 2

各果园 2022-2026 物候时间轴 + 温度/降雨背景。

## Figure 3

P1：B0/B1、日尺度、小时尺度、非线性温度模型 LOYO MAE 比较。

## Figure 4

P1 最佳模型 observed vs predicted dates；标注 orchard/year。

## Figure 5

P2/P3 thermal-time 预测表现。

## Figure 6

W1-CALENDAR、W1-MEDIAN、W2-OBS、W3-PRED 窗口示意与特征差异。

## Figure 7

若 yield gate 通过：Y-B0、Y-W1C、Y-W1M、Y-W2O、Y-W3P 的 held-out MAE。

## Figure 8

若情景 gate 通过：暖冬与秋梢老熟推迟对抽穗日期的二维响应。

2025 办内案例建议放 Supplementary 或主文最后一个 panel，不应抢主线。

---

# 22. 最终报告文件

必须生成：

```text
reports/r4/00_R4_DATA_GATE_REPORT.md
reports/r4/01_R4_DESCRIPTIVE_REPORT.md
reports/r4/02_P1_PHENOLOGY_MODEL_REPORT.md
reports/r4/03_P2_P3_PHENOLOGY_REPORT.md
reports/r4/04_WHITE_TIP_EXPLORATORY_REPORT.md
reports/r4/05_DYNAMIC_WINDOW_REPORT.md
reports/r4/06_YIELD_MODEL_REPORT.md
reports/r4/07_TYPHOON_CASE_REPORT.md
reports/r4/08_SCENARIO_REPORT.md
reports/r4/FINAL_R4_EXPERIMENT_REPORT_ZH.md
```

最终中文报告必须清楚区分：

- observed fact；
- held-out prediction；
- retrospective upper bound；
- sensitivity analysis；
- scenario simulation；
- unsupported claim。

---

# 23. Stop rules：不要为了“完成计划”强行跑下游模型

## Stop-P1

如果所有天气 P1 模型均不能稳定优于 P1-B0：

- 仍然执行 P2/P3；
- 不用失败的 P1 做暖冬预测结论；
- W3-PRED 标记受限；
- 论文主线转为阶段性物候响应而非完整链式预测。

## Stop-P2/P3

如果 GDD 不优于持续时间基线：

- 不加更多复杂变量去追分；
- 保留负结果；
- W3 该阶段可使用最稳定基线预测作为现实对照，但必须标明不是气象驱动模型。

## Stop-Y

如果 yield gate 不满足或 Y-W3P 不能优于 Y-B0：

- 停止产量“预测”扩展；
- 不上 RF/XGBoost/deep learning 挽救分数；
- 产量部分改写为正常产年的探索性阶段关联。

## Stop-Scenario

任何对应基础模型未通过验证，则对应情景不运行或只做明确标记的机制敏感性，不输出“预测影响多少天/多少产量”的强结论。

---

# 24. Codex 最终回复模板

最终回复用户必须包含：

```text
1. 工作分支
2. 最新提交 SHA
3. 测试通过数 / skip 数
4. R4 数据闸门状态
5. P1 各模型 LOYO MAE 与最佳模型
6. P2/P3 结果
7. W1/W2/W3 比较
8. Yield gate 是否通过；若通过给结果，若未通过说明原因
9. 2025 办内如何处理
10. 场景是否获准运行及结果
11. 论文当前最合理定位（A/B/C）
12. FINAL_R4_EXPERIMENT_REPORT_ZH.md 链接
```

不要只回复“实验已完成并推送”。

---

# 25. 本轮最重要的论文判据

最终不要以“建立了几个模型”为创新点。

最理想的论文证据链是：

```text
R4精确果园气象
      ↓
小时/日尺度低温确实改善抽穗日期 held-out 预测
      ↓
热量模型能够解释后续盛花/成熟阶段
      ↓
实测物候动态窗口优于固定日历窗口
      ↓
交叉预测物候构成的 W3 仍能保留这种优势
      ↓
（若数据支持）W3 正常产量预测优于历史产量基线
      ↓
暖冬 + 秋梢推迟情景揭示成花时间风险
```

如果其中产量链条不成立，仍可以形成：

```text
精确果园气象 + 多阶段物候预测 + 动态物候窗口 + 暖冬风险推演
```

这仍是一条完整、可发表的研究主线。
