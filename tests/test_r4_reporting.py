import json
import pandas as pd


def test_final_summary_distinguishes_completed_workflow_from_model_success(context):
    base=context[0]/'results/r4'
    state=json.loads((base/'qc/execution_summary.json').read_text(encoding='utf-8'))
    gate=json.loads((base/'qc/analysis_gate_r4.json').read_text(encoding='utf-8'))
    assert state['workflow_status']=='completed_with_scientific_stop_rules'
    assert state['normal_yield_sample_gate_pass'] and not state['formal_yield_comparison_complete']
    assert state['P1_stable_weather_models']==[] and 'P2-M1' in state['P2_stable_weather_models']
    assert not state['Y_W3P_success'] and state['paper_position']=='C'
    assert gate['status']=='pass' and not gate['yield_gate'].startswith('pending')


def test_required_reports_and_figures_preserve_negative_results(context):
    root=context[0]
    names=['00_R4_DATA_GATE_REPORT','01_R4_DESCRIPTIVE_REPORT','02_P1_PHENOLOGY_MODEL_REPORT',
           '03_P2_P3_PHENOLOGY_REPORT','04_WHITE_TIP_EXPLORATORY_REPORT','05_DYNAMIC_WINDOW_REPORT',
           '06_YIELD_MODEL_REPORT','07_TYPHOON_CASE_REPORT','08_SCENARIO_REPORT','FINAL_R4_EXPERIMENT_REPORT_ZH']
    for name in names: assert (root/'reports/r4'/(name+'.md')).stat().st_size>100
    figures=pd.read_csv(root/'results/r4/figures/figure_manifest.csv')
    assert figures.page.tolist()==list(range(1,len(figures)+1))
    assert len(figures)==11
    assert figures.figure.str.contains('P2_temperature_sensitivity').any()
    assert not figures.figure.str.contains('P1_warming|typhoon_loss|Figure_8').any()
    for name in figures.figure: assert (root/'results/r4/figures'/(name+'.png')).stat().st_size>1000
