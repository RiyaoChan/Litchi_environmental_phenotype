# 模型验证约束下的情景

| experiment_id | status | reason |
| --- | --- | --- |
| S1 | blocked | P1_no_stable_weather_superiority |
| S2 | blocked | P1_no_stable_weather_superiority |
| S3 | blocked | P1_no_stable_weather_superiority |
| S4-P2 | executed | stable_P2-M1_fixed_LOYO_fit |
| S4-P3 | blocked | P3_no_stable_weather_superiority |
| S5 | blocked | normal_Y-W3P_not_validated |

## 实际获准的固定模型结果

| experiment_id | task | temperature_shift_c | flush_start_delay_days | count | mean | median | min | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S4-P2 | P2 | 1 | 0 | 12 | -3.667 | -3.5 | -7 | -2 |
| S4-P2 | P2 | 2 | 0 | 12 | -7.25 | -6 | -15 | -4 |

变化=扰动后的预测日期−未扰动的预测日期，而不是减去实测日期；负值为提前。每个样本使用其LOYO训练折既有模型，不重新拟合参数。升温同步改变日均/最高/最低及小时气温，雨量、辐射、VPD、土壤湿度不改；这是受控输入敏感性，不是完整气候耦合模拟。

秋梢推迟只改累计起点，不删除或重写天气历史。对应模型未验证时不输出正式影响天数。P2情景以实际抽穗起点为条件，并不意味着整条秋梢→成熟链已验证。由于只有5年，不能把数值当确定生产预报。

若S5获准，只报告固定预测边界下的探索性Ridge特征扰动；增加5个高温日是特征级等价扰动，不是创造一段真实气象。主模型只有花期降雨小时数，花期雨量±20%的强度变化不直接对应该输入，故不把没有相应变量的模型解释成“降雨无效”。
