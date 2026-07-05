--
-- CDSS decision-tree insert script
-- Tree: "Cây 14: THA Cấp Cứu - Minh"
-- Source: Mục 3.6.5, Bảng 14 (Khuyến cáo THA VNHA 2022.pdf):
--   Mục 3.6.5 intro -> printed p.27 / PDF page 29
--   Bảng 14 table   -> printed p.28 / PDF page 30
--
-- This is the tree_key = 'hypertensive-emergency' target that
-- T1_LINK_HYPERTENSIVE_EMERGENCY already links out to (null
-- link_target_node_key, resuming at this tree's START) — it did not exist
-- yet (0 rows) before this file.
--
-- Built following the same conventions and lessons as tree6.sql/tree8.sql/
-- tree11.sql/tree12.sql (see backups/shared_conventions.txt):
--   * gen_random_uuid()/now() for all ids/timestamps.
--   * Any fact not in the system's closed input contract is written through
--     a node whose context_patch merges a static default (false), then
--     COPY_PATH(required:false) overlays the caller-supplied value if
--     present. Applies to the 8 acute-presentation flags below.
--   * input.has_target_organ_damage and input.clinic_1_sbp/clinic_1_dbp are
--     already established fields (has_target_organ_damage is in the closed
--     input vocabulary; clinic_1_sbp/dbp is required by the intake form and
--     is the same field Tree 1's own crisis check
--     (T1_C_CLINIC_1_CRISIS: clinic_1_sbp>=180 OR clinic_1_dbp>=120) already
--     used before linking here) — no new unsafe fields needed for the entry
--     split or the BP-threshold sub-checks.
--   * No specific drug names in structured JSON fields (a separate drug
--     table is planned) — drug names appear only in text_en/text_vi, same
--     treatment as tree12.sql's IV drug nodes. action_payload carries
--     numeric/enum targets (MAP reduction %, BP thresholds, timing) instead.
--
-- SIMPLER PATTERN THAN TREE 6/8/11's has-X/no-X sibling pairs: the 9
-- clinical-scenario checks below have exactly ONE entry point
-- (T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS), so they are modeled as one
-- priority-ordered candidate list (first match wins, per
-- docs/cdss/traversal-engine-contract.md §11) ending in an unconditional
-- catch-all — not as paired has/no siblings, which was only necessary in
-- earlier trees because multiple different entry points needed to reach the
-- same check.
--
-- CROSS-CHECK FINDING (against the actual PDF, not just the supplied
-- description): the drug assignments for "Hội chứng vành cấp" (ACS) and
-- "Phù phổi cấp do tim" (acute cardiogenic pulmonary edema) were swapped in
-- the supplied table. The PDF's Bảng 14 actually reads:
--   ACS                        -> Nitroprusside hoặc Nitroglycerine (kèm lợi
--                                  tiểu quai) / Urapidil (kèm lợi tiểu quai)
--   Acute cardiogenic pulmonary
--   edema                      -> Labetalol hoặc Metoprolol (no alternative
--                                  listed)
-- This file uses the PDF's actual mapping, not the supplied table's.
--
-- DELIBERATE OMISSION / FLAGGED ANOMALY: the supplied description links
-- "Bệnh động mạch chủ cấp" (acute aortic syndrome) to tree_key
-- 'hypertension-heart-failure' (Cây 10), but also flags this itself as a
-- likely error in the self-assembled board (aortic dissection/aneurysm is
-- not a heart-failure presentation, and no aortic-specific tree exists in
-- this system's established tree-key list). Rather than encode a link that
-- both the author and clinical logic doubt, T14_END_ACUTE_AORTIC_SYNDROME is
-- a terminal END node (no LINK) documenting the acute target
-- (SBP<120 mmHg, HR<60 bpm) with requires_clinician_review:true. Revisit if
-- a dedicated aortic-syndrome tree or a confirmed correct target is added
-- later.
--
-- Node type mapping (matching the established legend from tree6/8/11/12):
--   green      Start Node          -> START
--   yellow     Condition Check     -> CONDITION
--   blue       Trigger/Input Node  -> INFERENCE (context_patch)
--   orange     Action/Output Node  -> ACTION
--   pink/red   Link Node           -> LINK
--   gray       Global Node         -> GLOBAL
--
-- Citation note: Bảng 14 is reproduced in the source document under
-- permission from Van den Born et al., European Heart Journal -
-- Cardiovascular Pharmacotherapy, Oxford University Press (per the source
-- document's own acknowledgements section) — preserved in the GLOBAL node's
-- config and per-scenario reference_note fields below.
--
-- IMPORTANT — per the author: this flowchart (severe-HTN entry -> target-
-- organ-damage split -> 9 clinical scenarios) is a self-assembled diagram
-- cross-checked against Bảng 14 and Mục 3.6.5 for clinical accuracy, not a
-- single original figure in the PDF.
--
-- Use: docker compose exec -T postgres psql -U cdss -d cdss -f /path/tree14.sql
--

BEGIN;
-- ============================================================
-- 0. Remove the existing hypertensive-emergency tree, if present
-- ============================================================
DELETE FROM public.node_source_references
WHERE node_id IN (
        SELECT n.id
        FROM public.decision_nodes n
            JOIN public.decision_trees t ON t.id = n.tree_id
        WHERE t.tree_key = 'hypertensive-emergency'
    );
DELETE FROM public.decision_edges
WHERE from_node_id IN (
        SELECT n.id
        FROM public.decision_nodes n
            JOIN public.decision_trees t ON t.id = n.tree_id
        WHERE t.tree_key = 'hypertensive-emergency'
    );
DELETE FROM public.decision_nodes
WHERE tree_id IN (
        SELECT id FROM public.decision_trees WHERE tree_key = 'hypertensive-emergency'
    );
DELETE FROM public.decision_trees WHERE tree_key = 'hypertensive-emergency';
-- ============================================================
-- 1. Tree
-- ============================================================
INSERT INTO public.decision_trees (
        "id", "tree_key", "name_en", "name_vi", "created_at", "updated_at"
    )
VALUES (
        gen_random_uuid(), 'hypertensive-emergency',
        'Hypertensive Emergency', 'Tăng Huyết Áp Cấp Cứu', now(), now()
    );
-- ============================================================
-- 2. Nodes
-- ============================================================
WITH tree_ctx AS (
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'hypertensive-emergency'
),
node_seed (
    node_key, node_type, text_en, text_vi,
    condition_definition, context_patch, action_payload, global_config,
    link_target_tree_key, link_target_node_key, display_order
) AS (
    VALUES
    -- --- Entry: severe hypertension, target-organ-damage split ---
    (
        'T14_START_SEVERE_HYPERTENSION', 'START',
        'Severe hypertension (SBP >=180 and/or DBP >=120 mmHg)',
        'Bệnh nhân tăng huyết áp nặng (HATT >= 180 và/hoặc HATTr >= 120 mmHg)',
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 0
    ),
    (
        'T14_C_NO_ACUTE_TARGET_ORGAN_DAMAGE', 'CONDITION',
        'No acute target organ damage', 'Không tổn thương cơ quan đích cấp tính',
        '{"path":"input.has_target_organ_damage","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 1
    ),
    (
        'T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE', 'CONDITION',
        'Has acute target organ damage', 'Có tổn thương cơ quan đích cấp tính',
        '{"path":"input.has_target_organ_damage","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 2
    ),
    -- --- Nhánh 1: urgent (no acute target organ damage) ---
    (
        'T14_END_URGENT_HYPERTENSION', 'END',
        'Urgent hypertension: oral antihypertensive therapy; outpatient/inpatient monitoring; gradual BP lowering',
        'Tăng huyết áp khẩn trương: Điều trị thuốc uống. Theo dõi ngoại trú/nội trú. Hạ huyết áp từ từ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ORAL_ANTIHYPERTENSIVE_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"bp_lowering_strategy":"GRADUAL"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 3
    ),
    -- --- Nhánh 2: emergency (has acute target organ damage) ---
    (
        'T14_ACTION_ADMIT_AND_DETERMINE_TARGET_ORGAN', 'ACTION',
        'Emergency hypertension: admit to hospital, apply IV antihypertensive therapy, determine target organ',
        'Tăng huyết áp cấp cứu: Nhập viện. Áp dụng thuốc hạ áp đường tĩnh mạch. Xác định cơ quan đích',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ADMIT_AND_DETERMINE_TARGET_ORGAN","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"route":"IV_INFUSION"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 4
    ),
    (
        'T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'INFERENCE',
        'Determine which of the 9 specific hypertensive-emergency clinical scenarios applies (Bảng 14)',
        'Xác định bệnh cảnh lâm sàng cấp cứu cụ thể (Bảng 14)',
        NULL::jsonb,
        '{"treatment":{"has_hypertensive_encephalopathy":false,"has_acute_ischemic_stroke":false,"is_thrombolysis_candidate":false,"has_acute_intracerebral_hemorrhage":false,"has_acute_coronary_syndrome":false,"has_acute_cardiogenic_pulmonary_edema":false,"has_acute_aortic_syndrome":false,"has_eclampsia_severe_preeclampsia_or_hellp":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_hypertensive_encephalopathy","to_path":"context.treatment.has_hypertensive_encephalopathy","required":false},{"op":"COPY_PATH","from_path":"input.has_acute_ischemic_stroke","to_path":"context.treatment.has_acute_ischemic_stroke","required":false},{"op":"COPY_PATH","from_path":"input.is_thrombolysis_candidate","to_path":"context.treatment.is_thrombolysis_candidate","required":false},{"op":"COPY_PATH","from_path":"input.has_acute_intracerebral_hemorrhage","to_path":"context.treatment.has_acute_intracerebral_hemorrhage","required":false},{"op":"COPY_PATH","from_path":"input.has_acute_coronary_syndrome","to_path":"context.treatment.has_acute_coronary_syndrome","required":false},{"op":"COPY_PATH","from_path":"input.has_acute_cardiogenic_pulmonary_edema","to_path":"context.treatment.has_acute_cardiogenic_pulmonary_edema","required":false},{"op":"COPY_PATH","from_path":"input.has_acute_aortic_syndrome","to_path":"context.treatment.has_acute_aortic_syndrome","required":false},{"op":"COPY_PATH","from_path":"input.has_eclampsia_severe_preeclampsia_or_hellp","to_path":"context.treatment.has_eclampsia_severe_preeclampsia_or_hellp","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 5
    ),
    -- --- Scenario 1: hypertensive encephalopathy (priority 1) ---
    (
        'T14_C_HYPERTENSIVE_ENCEPHALOPATHY', 'CONDITION',
        'Hypertensive encephalopathy (coma, seizures, cortical blindness)',
        'Bệnh não do THA (hôn mê, co giật, mù vỏ não)',
        '{"path":"context.treatment.has_hypertensive_encephalopathy","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 6
    ),
    (
        'T14_ACTION_HYPERTENSIVE_ENCEPHALOPATHY', 'ACTION',
        'Hypertensive encephalopathy: primary Labetalol/Nicardipine; alternative Nitroprusside; target MAP -20% to -25%, immediate',
        'Bệnh não do THA: ưu tiên Labetalol/Nicardipine; thay thế Nitroprusside; mục tiêu MAP giảm 20-25%, ngay lập tức',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"HYPERTENSIVE_ENCEPHALOPATHY_ACUTE_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"target_map_reduction_percent_min":20,"target_map_reduction_percent_max":25,"target_timing":"IMMEDIATE"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 7
    ),
    -- --- Scenario 4: AIS + thrombolysis candidate (priority 2, stricter threshold checked first) ---
    (
        'T14_C_AIS_THROMBOLYSIS_CANDIDATE', 'CONDITION',
        'Acute ischemic stroke, thrombolysis candidate, SBP >185 or DBP >110 mmHg',
        'Nhồi máu não cấp có chỉ định tiêu sợi huyết, HATT >185 hoặc HATTr >110 mmHg',
        '{"all":[{"path":"context.treatment.has_acute_ischemic_stroke","op":"eq","value":true},{"path":"context.treatment.is_thrombolysis_candidate","op":"eq","value":true},{"any":[{"path":"input.clinic_1_sbp","op":"gt","value":185},{"path":"input.clinic_1_dbp","op":"gt","value":110}]}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 8
    ),
    (
        'T14_ACTION_AIS_THROMBOLYSIS_CANDIDATE', 'ACTION',
        'AIS, thrombolysis candidate: primary Labetalol/Nicardipine; alternative Urapidil; target MAP -15%, within 1 hour',
        'Nhồi máu não cấp có chỉ định tiêu sợi huyết: ưu tiên Labetalol/Nicardipine; thay thế Urapidil; mục tiêu MAP giảm 15%, trong 1 giờ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ACUTE_ISCHEMIC_STROKE_THROMBOLYSIS_CANDIDATE_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"target_map_reduction_percent":15,"target_timing":"WITHIN_1_HOUR","bp_threshold_sbp_mmhg":185,"bp_threshold_dbp_mmhg":110}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 9
    ),
    -- --- Scenario 3: AIS, general (priority 3) ---
    (
        'T14_C_AIS_SEVERE', 'CONDITION',
        'Acute ischemic stroke, SBP >220 or DBP >120 mmHg',
        'Nhồi máu não cấp, HATT >220 hoặc HATTr >120 mmHg',
        '{"all":[{"path":"context.treatment.has_acute_ischemic_stroke","op":"eq","value":true},{"any":[{"path":"input.clinic_1_sbp","op":"gt","value":220},{"path":"input.clinic_1_dbp","op":"gt","value":120}]}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 10
    ),
    (
        'T14_ACTION_AIS_SEVERE', 'ACTION',
        'AIS: primary Labetalol/Nicardipine; alternative Nitroprusside; target MAP -15%, within 1 hour',
        'Nhồi máu não cấp: ưu tiên Labetalol/Nicardipine; thay thế Nitroprusside; mục tiêu MAP giảm 15%, trong 1 giờ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ACUTE_ISCHEMIC_STROKE_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"target_map_reduction_percent":15,"target_timing":"WITHIN_1_HOUR","bp_threshold_sbp_mmhg":220,"bp_threshold_dbp_mmhg":120}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 11
    ),
    -- --- Scenario 7: acute ICH (priority 4) ---
    (
        'T14_C_ACUTE_ICH', 'CONDITION',
        'Acute intracerebral hemorrhage, SBP >180 mmHg',
        'Xuất huyết não cấp, HATT >180 mmHg',
        '{"all":[{"path":"context.treatment.has_acute_intracerebral_hemorrhage","op":"eq","value":true},{"path":"input.clinic_1_sbp","op":"gt","value":180}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 12
    ),
    (
        'T14_ACTION_ACUTE_ICH', 'ACTION',
        'Acute ICH: primary Nitroglycerine/Labetalol; alternative Urapidil; target 130<SBP<180 mmHg',
        'Xuất huyết não cấp: ưu tiên Nitroglycerine/Labetalol; thay thế Urapidil; mục tiêu 130<HATT<180 mmHg',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ACUTE_INTRACEREBRAL_HEMORRHAGE_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"target_sbp_lower_mmhg":130,"target_sbp_upper_mmhg":180}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 13
    ),
    (
        'T14_END_REFER_STROKE_MANAGEMENT', 'END', 'Refer to stroke management',
        'Điều trị đột quỵ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"REFER_STROKE_MANAGEMENT","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"requires_clinician_review":true}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 14
    ),
    -- --- Scenario 5: acute coronary syndrome (priority 5) ---
    (
        'T14_C_ACS', 'CONDITION', 'Acute coronary syndrome', 'Hội chứng vành cấp',
        '{"path":"context.treatment.has_acute_coronary_syndrome","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 15
    ),
    (
        'T14_ACTION_ACS', 'ACTION',
        'ACS: primary Nitroprusside or Nitroglycerine (with a loop diuretic); alternative Urapidil (with a loop diuretic); target SBP <140 mmHg, immediate',
        'Hội chứng vành cấp: ưu tiên Nitroprusside hoặc Nitroglycerine (kèm lợi tiểu quai); thay thế Urapidil (kèm lợi tiểu quai); mục tiêu HATT <140 mmHg, ngay lập tức',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ACUTE_CORONARY_SYNDROME_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"target_sbp_upper_mmhg":140,"target_timing":"IMMEDIATE"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 16
    ),
    (
        'T14_LINK_CORONARY_ARTERY_DISEASE', 'LINK', 'Tree 9: Hypertension With Coronary Artery Disease',
        'Cây 9: THA + Bệnh Mạch Vành',
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::jsonb,
        'hypertension-coronary-artery-disease', NULL::text, 17
    ),
    -- --- Scenario 6: acute cardiogenic pulmonary edema (priority 6) ---
    (
        'T14_C_ACUTE_CARDIOGENIC_PULMONARY_EDEMA', 'CONDITION',
        'Acute cardiogenic pulmonary edema', 'Phù phổi cấp do tim',
        '{"path":"context.treatment.has_acute_cardiogenic_pulmonary_edema","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 18
    ),
    (
        'T14_ACTION_ACUTE_CARDIOGENIC_PULMONARY_EDEMA', 'ACTION',
        'Acute cardiogenic pulmonary edema: Labetalol or Metoprolol; target SBP <140 mmHg, immediate',
        'Phù phổi cấp do tim: Labetalol hoặc Metoprolol; mục tiêu HATT <140 mmHg, ngay lập tức',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ACUTE_CARDIOGENIC_PULMONARY_EDEMA_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"target_sbp_upper_mmhg":140,"target_timing":"IMMEDIATE"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 19
    ),
    (
        'T14_LINK_HEART_FAILURE', 'LINK', 'Tree 10: Hypertension With Heart Failure',
        'Cây 10: THA + Suy Tim',
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::jsonb,
        'hypertension-heart-failure', NULL::text, 20
    ),
    -- --- Scenario 8: acute aortic syndrome (priority 7; terminal, see header note) ---
    (
        'T14_C_ACUTE_AORTIC_SYNDROME', 'CONDITION',
        'Acute aortic syndrome', 'Bệnh động mạch chủ cấp',
        '{"path":"context.treatment.has_acute_aortic_syndrome","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 21
    ),
    (
        'T14_END_ACUTE_AORTIC_SYNDROME', 'END',
        'Acute aortic syndrome: Esmolol plus Nitroprusside, Nitroglycerine, or Nicardipine; target SBP <120 mmHg and heart rate <60 bpm, immediate',
        'Bệnh động mạch chủ cấp: Esmolol phối hợp Nitroprusside, Nitroglycerine, hoặc Nicardipine; mục tiêu HATT <120 mmHg và nhịp tim <60 lần/phút, ngay lập tức',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ACUTE_AORTIC_SYNDROME_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"target_sbp_upper_mmhg":120,"target_heart_rate_upper_bpm":60,"target_timing":"IMMEDIATE","requires_clinician_review":true}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 22
    ),
    -- --- Scenario 9: eclampsia / severe preeclampsia / HELLP (priority 8) ---
    (
        'T14_C_ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP', 'CONDITION',
        'Eclampsia, severe preeclampsia, or HELLP syndrome',
        'Sản giật, tiền sản giật nặng, hoặc hội chứng HELLP',
        '{"path":"context.treatment.has_eclampsia_severe_preeclampsia_or_hellp","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 23
    ),
    (
        'T14_ACTION_ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP', 'ACTION',
        'Eclampsia/severe preeclampsia/HELLP: Labetalol or Nicardipine plus magnesium sulfate; target SBP <160 mmHg and DBP <105 mmHg, immediate',
        'Sản giật/tiền sản giật nặng/HELLP: Labetalol hoặc Nicardipine phối hợp Magnesium sulfate; mục tiêu HATT <160 mmHg và HATTr <105 mmHg, ngay lập tức',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"target_sbp_upper_mmhg":160,"target_dbp_upper_mmhg":105,"target_timing":"IMMEDIATE"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 24
    ),
    (
        'T14_LINK_PREGNANCY', 'LINK', 'Tree 12: Hypertension in Pregnancy',
        'Cây 13: THA Thai Kỳ',
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::jsonb,
        'hypertension-in-pregnancy', NULL::text, 25
    ),
    -- --- Scenario 2: catch-all (priority 9, unconditional) ---
    (
        'T14_ACTION_MALIGNANT_HTN_TMA_AKI', 'ACTION',
        'Hypertensive emergency with or without TMA/acute kidney injury: primary Labetalol/Nicardipine; alternative Nitroprusside/Urapidil; target MAP -20% to -25%, within hours',
        'THA cấp cứu có hoặc không có TMA/Suy thận cấp: ưu tiên Labetalol/Nicardipine; thay thế Nitroprusside/Urapidil; mục tiêu MAP giảm 20-25%, trong vài giờ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"MALIGNANT_HYPERTENSION_TMA_AKI_THERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"target_map_reduction_percent_min":20,"target_map_reduction_percent_max":25,"target_timing":"WITHIN_HOURS"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 26
    ),
    (
        'T14_GLOBAL_ABBREVIATION_GLOSSARY', 'GLOBAL', 'Abbreviation glossary', 'Chú giải viết tắt',
        NULL::jsonb, NULL::jsonb, NULL::jsonb,
        '{"kind":"ABBREVIATION_GLOSSARY","purpose":"Chú giải các chữ viết tắt dùng trong Cây 14, theo chú thích Bảng 14.","source_permission_note":"Bảng 14 được trích dẫn theo Van den Born và cộng sự, với sự cho phép của Tạp chí European Heart Journal - Cardiovascular Pharmacotherapy, Oxford University Press.","entries":{"MAP":{"label":"MAP: Mean arterial pressure - Huyết áp trung bình"},"TMA":{"label":"TMA: Thrombotic microangiopathy - Bệnh vi mạch huyết khối"},"HELLP":{"label":"HELLP: Hemolysis, Elevated Liver Enzymes and Low Platelets - Hội chứng liên quan tiền sản giật nặng"}}}'::jsonb,
        NULL::text, NULL::text, 99
    )
)
INSERT INTO public.decision_nodes (
        "id", "tree_id", "node_key", "node_type", "text_en", "text_vi",
        "condition_definition", "context_patch", "action_payload", "global_config",
        "link_target_tree_key", "link_target_node_key", "display_order",
        "created_at", "updated_at"
    )
SELECT gen_random_uuid(),
    tree_ctx.tree_id,
    node_seed.node_key,
    node_seed.node_type::node_type,
    node_seed.text_en,
    node_seed.text_vi,
    node_seed.condition_definition,
    node_seed.context_patch,
    node_seed.action_payload,
    node_seed.global_config,
    node_seed.link_target_tree_key,
    node_seed.link_target_node_key,
    node_seed.display_order,
    now(),
    now()
FROM node_seed
    CROSS JOIN tree_ctx;
-- ============================================================
-- 3. Edges
-- ============================================================
WITH tree_ctx AS (
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'hypertensive-emergency'
),
edge_seed (from_node_key, to_node_key, traversal_order) AS (
    VALUES
    ('T14_START_SEVERE_HYPERTENSION', 'T14_C_NO_ACUTE_TARGET_ORGAN_DAMAGE', 1),
    ('T14_START_SEVERE_HYPERTENSION', 'T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE', 2),
    ('T14_C_NO_ACUTE_TARGET_ORGAN_DAMAGE', 'T14_END_URGENT_HYPERTENSION', 1),
    ('T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE', 'T14_ACTION_ADMIT_AND_DETERMINE_TARGET_ORGAN', 1),
    ('T14_ACTION_ADMIT_AND_DETERMINE_TARGET_ORGAN', 'T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 1),
    -- priority-ordered candidates; first match wins; ends in an unconditional catch-all
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_C_HYPERTENSIVE_ENCEPHALOPATHY', 1),
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_C_AIS_THROMBOLYSIS_CANDIDATE', 2),
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_C_AIS_SEVERE', 3),
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_C_ACUTE_ICH', 4),
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_C_ACS', 5),
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_C_ACUTE_CARDIOGENIC_PULMONARY_EDEMA', 6),
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_C_ACUTE_AORTIC_SYNDROME', 7),
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_C_ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP', 8),
    ('T14_INF_DETERMINE_CLINICAL_SCENARIO_FLAGS', 'T14_ACTION_MALIGNANT_HTN_TMA_AKI', 9),
    ('T14_C_HYPERTENSIVE_ENCEPHALOPATHY', 'T14_ACTION_HYPERTENSIVE_ENCEPHALOPATHY', 1),
    ('T14_ACTION_HYPERTENSIVE_ENCEPHALOPATHY', 'T14_END_REFER_STROKE_MANAGEMENT', 1),
    ('T14_C_AIS_THROMBOLYSIS_CANDIDATE', 'T14_ACTION_AIS_THROMBOLYSIS_CANDIDATE', 1),
    ('T14_ACTION_AIS_THROMBOLYSIS_CANDIDATE', 'T14_END_REFER_STROKE_MANAGEMENT', 1),
    ('T14_C_AIS_SEVERE', 'T14_ACTION_AIS_SEVERE', 1),
    ('T14_ACTION_AIS_SEVERE', 'T14_END_REFER_STROKE_MANAGEMENT', 1),
    ('T14_C_ACUTE_ICH', 'T14_ACTION_ACUTE_ICH', 1),
    ('T14_ACTION_ACUTE_ICH', 'T14_END_REFER_STROKE_MANAGEMENT', 1),
    ('T14_C_ACS', 'T14_ACTION_ACS', 1),
    ('T14_ACTION_ACS', 'T14_LINK_CORONARY_ARTERY_DISEASE', 1),
    ('T14_C_ACUTE_CARDIOGENIC_PULMONARY_EDEMA', 'T14_ACTION_ACUTE_CARDIOGENIC_PULMONARY_EDEMA', 1),
    ('T14_ACTION_ACUTE_CARDIOGENIC_PULMONARY_EDEMA', 'T14_LINK_HEART_FAILURE', 1),
    ('T14_C_ACUTE_AORTIC_SYNDROME', 'T14_END_ACUTE_AORTIC_SYNDROME', 1),
    ('T14_C_ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP', 'T14_ACTION_ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP', 1),
    ('T14_ACTION_ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP', 'T14_LINK_PREGNANCY', 1),
    ('T14_ACTION_MALIGNANT_HTN_TMA_AKI', 'T14_END_URGENT_HYPERTENSION', 1)
)
INSERT INTO public.decision_edges ("id", "from_node_id", "to_node_id", "traversal_order")
SELECT gen_random_uuid(), from_node.id, to_node.id, edge_seed.traversal_order
FROM edge_seed
    CROSS JOIN tree_ctx
    JOIN public.decision_nodes from_node ON from_node.tree_id = tree_ctx.tree_id
        AND from_node.node_key = edge_seed.from_node_key
    JOIN public.decision_nodes to_node ON to_node.tree_id = tree_ctx.tree_id
        AND to_node.node_key = edge_seed.to_node_key;
-- ============================================================
-- 4. Source references
-- ============================================================
WITH tree_ctx AS (
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'hypertensive-emergency'
),
reference_seed (
    node_key, source_title, section_path, locator, locator_detail,
    printed_page_numbers, pdf_page_numbers, reference_note, reference_order
) AS (
    VALUES
    ('T14_START_SEVERE_HYPERTENSION',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.5", "title": "Tăng huyết áp cấp cứu"}]'::jsonb,
     'Mục 3.6.5. Tăng huyết áp cấp cứu',
     'Entry point of the hypertensive-emergency tree; emergency vs. urgent hypertension distinction.',
     ARRAY[27]::smallint[], ARRAY[29]::smallint[],
     'Điểm vào của Cây 14; phân biệt THA cấp cứu và THA khẩn trương.', 1),
    ('T14_C_NO_ACUTE_TARGET_ORGAN_DAMAGE',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.5", "title": "Tăng huyết áp cấp cứu"}]'::jsonb,
     'Mục 3.6.5. Tăng huyết áp cấp cứu',
     'Without acute target-organ damage, this is urgent hypertension, usually treatable with oral therapy.',
     ARRAY[27]::smallint[], ARRAY[29]::smallint[],
     'Bệnh nhân tăng HA đáng kể nhưng không có tổn thương cơ quan đích cấp tính được gọi là tăng huyết áp khẩn trương.', 1),
    ('T14_C_HAS_ACUTE_TARGET_ORGAN_DAMAGE',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.5", "title": "Tăng huyết áp cấp cứu"}]'::jsonb,
     'Mục 3.6.5. Tăng huyết áp cấp cứu',
     'Severe hypertension with acute target-organ damage is a hypertensive emergency requiring immediate, usually IV, therapy.',
     ARRAY[27]::smallint[], ARRAY[29]::smallint[],
     'THA cấp cứu là THA nặng kết hợp tổn thương cơ quan đích cấp tính, cần can thiệp hạ HA ngay lập tức, thường bằng đường tĩnh mạch.', 1),
    ('T14_ACTION_MALIGNANT_HTN_TMA_AKI',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.5", "title": "Tăng huyết áp cấp cứu"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51)',
     'General/malignant hypertensive emergency with or without TMA/AKI: MAP reduction 20-25% over several hours.',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14, theo Van den Born và cộng sự (51).', 1),
    ('T14_ACTION_HYPERTENSIVE_ENCEPHALOPATHY',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.5", "title": "Tăng huyết áp cấp cứu"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51)',
     'Hypertensive encephalopathy: immediate MAP reduction 20-25%.',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14, theo Van den Born và cộng sự (51).', 1),
    ('T14_ACTION_AIS_THROMBOLYSIS_CANDIDATE',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.5", "title": "Tăng huyết áp và Đột quỵ"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51); xem thêm Bảng 24, Mục 3.7.5',
     'AIS with thrombolysis indication: MAP -15% within 1 hour if SBP>185 or DBP>110 mmHg; see Bảng 24 for more detailed AIS management including thrombolysis/thrombectomy.',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14; đối chiếu bổ sung Bảng 24, Mục 3.7.5 về xử trí HA trong đột quỵ thiếu máu não cấp.', 1),
    ('T14_ACTION_AIS_SEVERE',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.5", "title": "Tăng huyết áp và Đột quỵ"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51); xem thêm Bảng 24, Mục 3.7.5',
     'AIS: MAP -15% within 1 hour if SBP>220 or DBP>120 mmHg; see Bảng 24 for more detailed AIS management.',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14; đối chiếu bổ sung Bảng 24, Mục 3.7.5.', 1),
    ('T14_ACTION_ACUTE_ICH',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.5", "title": "Tăng huyết áp và Đột quỵ"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51); xem thêm Bảng 23, Mục 3.7.5',
     'Acute ICH: target 130<SBP<180 mmHg; see Bảng 23 for detailed ICH management (>220 consider IV infusion; 150-220 lowering to <140 within 6h shows no benefit and may be harmful; start within 2h, max reduction 90 mmHg from baseline).',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14; đối chiếu bổ sung Bảng 23, Mục 3.7.5 về xử trí HA trong xuất huyết não cấp.', 1),
    ('T14_ACTION_ACS',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.2", "title": "Tăng huyết áp và Bệnh mạch vành"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51); xem thêm Bảng 19, Mục 3.7.2',
     'ACS: target SBP<140 mmHg immediately; see Bảng 19 for hypertension-with-CAD strategy.',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14; đối chiếu bổ sung Bảng 19, Mục 3.7.2.', 1),
    ('T14_ACTION_ACUTE_CARDIOGENIC_PULMONARY_EDEMA',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.3", "title": "Tăng huyết áp và Suy tim"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51); xem thêm Bảng 20, Mục 3.7.3',
     'Acute cardiogenic pulmonary edema: target SBP<140 mmHg immediately; see Bảng 20 for heart-failure strategy.',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14; đối chiếu bổ sung Bảng 20, Mục 3.7.3.', 1),
    ('T14_END_ACUTE_AORTIC_SYNDROME',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.5", "title": "Tăng huyết áp cấp cứu"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51)',
     'Acute aortic syndrome: target SBP<120 mmHg and heart rate <60 bpm immediately. No onward tree link (see header note on the flagged Cây 10 discrepancy).',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14, theo Van den Born và cộng sự (51).', 1),
    ('T14_ACTION_ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51); xem thêm Bảng 15, 16, Mục 3.6.6',
     'Eclampsia/severe preeclampsia/HELLP: target SBP<160 and DBP<105 mmHg immediately; RAS-inhibitors contraindicated and sodium nitroprusside avoided in pregnancy (fetal cyanide toxicity risk).',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Trích Bảng 14; đối chiếu bổ sung Bảng 15, 16, Mục 3.6.6.', 1),
    ('T14_GLOBAL_ABBREVIATION_GLOSSARY',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.5", "title": "Tăng huyết áp cấp cứu"}]'::jsonb,
     'Bảng 14. Khuyến cáo điều trị bằng thuốc cho các trường hợp tăng huyết áp cấp cứu cụ thể (51), chú thích',
     'Footnote abbreviation glossary (MAP, TMA, HELLP) and source citation/permission note.',
     ARRAY[28]::smallint[], ARRAY[30]::smallint[],
     'Chú thích Bảng 14: MAP, TMA, HELLP; trích dẫn theo Van den Born và cộng sự, với sự cho phép của European Heart Journal - Cardiovascular Pharmacotherapy, Oxford University Press.', 1)
)
INSERT INTO public.node_source_references (
        "id", "node_id", "source_title", "section_path", "locator", "locator_detail",
        "printed_page_numbers", "pdf_page_numbers", "reference_note", "reference_order"
    )
SELECT gen_random_uuid(),
    node.id,
    reference_seed.source_title,
    reference_seed.section_path,
    reference_seed.locator,
    reference_seed.locator_detail,
    reference_seed.printed_page_numbers,
    reference_seed.pdf_page_numbers,
    reference_seed.reference_note,
    reference_seed.reference_order
FROM reference_seed
    CROSS JOIN tree_ctx
    JOIN public.decision_nodes node ON node.tree_id = tree_ctx.tree_id
        AND node.node_key = reference_seed.node_key;
COMMIT;
