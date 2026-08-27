# 测产区块与年份核对

原始行、合并单元格锚点及 `source_block_id` 均保留。当前A39=2026与方案=2025冲突；不自动改年、不删除或合并最后三个区块。当前标签下每个果园—产季只有一个区块，方案中所述同年多区块尚无法与当前文件对齐。

| season_id | source_block_id | year_source_cell | year_protocol_conflict | final_yield_kg_per_mu |
| --- | --- | --- | --- | --- |
| bannei_2022 | yield_Sheet1_r03 | A3 | 0 | 990.0 |
| bannei_2023 | yield_Sheet1_r12 | A12 | 0 | 1590.0 |
| bannei_2024 | yield_Sheet1_r21 | A21 | 0 | 718.74 |
| bannei_2025 | yield_Sheet1_r30 | A30 | 0 | 0.0 |
| bannei_2026 | yield_Sheet1_r39 | A39 | 1 | 1306.23 |
| hongming_2022 | yield_Sheet1_r06 | A3 | 0 | 1804.4 |
| hongming_2023 | yield_Sheet1_r15 | A12 | 0 | 753.6 |
| hongming_2024 | yield_Sheet1_r24 | A21 | 0 | 107.14 |
| hongming_2025 | yield_Sheet1_r33 | A30 | 0 | 450.14 |
| hongming_2026 | yield_Sheet1_r42 | A39 | 1 | 750.25 |
| luhong_2022 | yield_Sheet1_r09 | A3 | 0 | 1691.64 |
| luhong_2023 | yield_Sheet1_r18 | A12 | 0 | 783.55 |
| luhong_2024 | yield_Sheet1_r27 | A21 | 0 | 1027.8 |
| luhong_2025 | yield_Sheet1_r36 | A30 | 0 | 1205.88 |
| luhong_2026 | yield_Sheet1_r45 | A39 | 1 | 1205.88 |

## 年度Word数值对照（证据线索，不自动判定年份）

按同一Word表格行与Excel首个测产类别的三棵树数值匹配；不把文档副本视为独立证据。

| source_block_id | excel_row | excel_harvest_year | word_source_file | word_table | word_row | word_report_year_from_filename | matched_tree_yields_kg | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| yield_Sheet1_r03 | 3 | 2022 | 示范园/2022年荔枝龙眼产业技术体系示范园-海口站（20220825）.doc | 5 | 3 | 2022 | 35.06;32.8;30.77 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r06 | 6 | 2022 | 示范园/2022年荔枝龙眼产业技术体系示范园-海口站（20220825）.doc | 5 | 6 | 2022 | 136.08;137.81;120.88 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r09 | 9 | 2022 | 示范园/2022年荔枝龙眼产业技术体系示范园-海口站（20220825）.doc | 5 | 18 | 2022 | 115.21;120.6;113.25 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r12 | 12 | 2023 | 示范园/2023年荔枝龙眼产业技术体系示范园-海口站（20230825）(1).doc | 5 | 3 | 2023 | 55.06;47.8;46.77 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r15 | 15 | 2023 | 示范园/2023年荔枝龙眼产业技术体系示范园-海口站（20230825）(1).doc | 5 | 6 | 2023 | 56.08;57.81;50.88 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r18 | 18 | 2023 | 示范园/2023年荔枝龙眼产业技术体系示范园-海口站（20230825）(1).doc | 5 | 18 | 2023 | 49.21;51.6;48.25 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r21 | 21 | 2024 | 示范园/2024年荔枝龙眼产业技术体系示范园-海口站（20240825）.doc | 5 | 3 | 2024 | 20.99;22.01;22.49 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r24 | 24 | 2024 | 示范园/2024年荔枝龙眼产业技术体系示范园-海口站（20240825）.doc | 5 | 6 | 2024 | 9.57;6.97;7.94 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r27 | 27 | 2024 | 示范园/2024年荔枝龙眼产业技术体系示范园-海口站（20240825）.doc | 5 | 18 | 2024 | 58.3;61.55;64.89 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r33 | 33 | 2025 | 示范园/2025年荔枝龙眼产业技术体系示范园-海口站（20250827）.doc | 5 | 6 | 2025 | 34.26;33.54;32.85 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r36 | 36 | 2025 | 示范园/2025年荔枝龙眼产业技术体系示范园-海口站（20250827）.doc | 5 | 18 | 2025 | 70.63;69.35;75.3 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r39 | 39 | 2026 | 示范园/2026年荔枝龙眼产业技术体系示范园-海口站（20260825）.doc | 5 | 3 | 2026 | 38.45;44.21;37.37 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r42 | 42 | 2026 | 示范园/2026年荔枝龙眼产业技术体系示范园-海口站（20260825）.doc | 5 | 6 | 2026 | 60.11;55.68;60.04 | numeric_evidence_only_no_year_override |
| yield_Sheet1_r45 | 45 | 2026 | 示范园/2026年荔枝龙眼产业技术体系示范园-海口站（20260825）.doc | 5 | 18 | 2026 | 71.67;76.23;77.88 | numeric_evidence_only_no_year_override |

请确认 A39 是方案旧版本中的笔误，还是本地工作簿与计划所指版本不同；如果确为2025，请进一步提供区块用途。所有验证将按整个产季分组，绝不把类别/调查树随机分入训练和测试。
