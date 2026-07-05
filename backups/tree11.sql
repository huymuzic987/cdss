--
-- CDSS decision-tree insert script
-- Tree: "Cây 11: THA + Bệnh thận mạn - Minh"
-- Source: Bảng 21, Bảng 22, Mục 3.7.4 (Khuyến cáo THA VNHA 2022.pdf):
--   Mục 3.7.4 intro -> printed p.34 / PDF page 36
--   Bảng 21 & Bảng 22 tables -> printed p.35 / PDF page 37
--
-- This is the tree_key = 'hypertension-chronic-kidney-disease' target that
-- Tree 3's T3_LINK_18_69_CHRONIC_KIDNEY_DISEASE_MODIFIER and
-- T3_LINK_AGE_70_OR_HIGHER_CHRONIC_KIDNEY_DISEASE_MODIFIER already link out
-- to (both with a null link_target_node_key, resuming at this tree's START)
-- — it did not exist yet (0 rows) before this file.
--
-- Built following the same conventions and lessons as tree6.sql/tree8.sql/
-- tree12.sql (see backups/shared_conventions.txt):
--   * gen_random_uuid()/now() for all ids/timestamps.
--   * Any fact not in the system's closed input contract
--     (docs/cdss/context-contract.md, docs/cdss/traversal-engine-contract.md,
--     frontend's MockPatientSidebar.tsx) is written through a node whose
--     context_patch merges a static default, then COPY_PATH(required:false)
--     overlays the caller-supplied value if present — never a hard `eq` on a
--     possibly-absent input.* path. Applies here to has_kidney_transplant,
--     has_prior_creatinine_test, still_using_ras_inhibitor, and
--     creatinine_increased_over_30_percent, none of which are established.
--   * combination_options uses the A/B/C/D class-letter shape, matching
--     Tree 4/5/6/8 exactly (A = ACEI/ARB/ARNI, B = beta-blocker,
--     C = calcium-channel blocker, D = thiazide-like diuretic).
--   * No specific drug names anywhere (a separate drug table is planned per
--     the author) — the GLOBAL glossary below is class-letter abbreviations
--     only, same as Tree 8's, not a drug-name list.
--   * Every entry point into a boolean-check CONDITION pair offers BOTH
--     sibling candidates (the has-X/no-X lesson from tree6.sql), and the
--     shared T11_LINK_ESSENTIAL_TREATMENT_STRATEGY /
--     T11_LINK_OPTIMAL_TREATMENT_STRATEGY pair is reused from every
--     "maintain/adjust regimen" exit point, matching Tree 8's own
--     multi-entry-point-into-one-LINK-pair pattern.
--
-- DELIBERATE OMISSION: Bảng 22 (Loại III) also states "Không khuyến cáo kết
-- hợp hai nhóm thuốc ức chế RAS" (dual RAS-inhibitor blockade not
-- recommended) — the exact same rule Tree 6 already enforces
-- (T6_C_HAS_DUPLICATE_DRUG_CLASS / T6_C_DUPLICATE_IS_RAS_INHIBITOR). Since
-- every path here ends at Tree 4/5 -> Tree 6 for final agent-level
-- resolution, this tree does not duplicate that check itself, matching how
-- Tree 8 also does not duplicate it.
--
-- Node type mapping (matching the established legend from tree6/8/12):
--   green      Start Node          -> START
--   yellow     Condition Check     -> CONDITION
--   blue       Trigger/Input Node  -> INFERENCE (context_patch)
--   orange     Action/Output Node  -> ACTION
--   pink/red   Link Node           -> LINK
--   gray       Global Node         -> GLOBAL
--
-- IMPORTANT — per the author: this flowchart (visit type -> initial
-- combination -> creatinine-monitoring branch -> maintain/adjust -> link to
-- Tree 4/5) is a self-assembled diagram cross-checked against Bảng 21/22 and
-- Mục 3.7.4 for clinical accuracy, not a single original figure in the PDF.
--
-- Use: cmd /c "docker compose exec -T postgres psql -U cdss -d cdss < backups\tree11.sql"
--

BEGIN;
-- ============================================================
-- 0. Remove the existing chronic-kidney-disease tree, if present
-- ============================================================
DELETE FROM public.node_source_references
WHERE node_id IN (
        SELECT n.id
        FROM public.decision_nodes n
            JOIN public.decision_trees t ON t.id = n.tree_id
        WHERE t.tree_key = 'hypertension-chronic-kidney-disease'
    );
DELETE FROM public.decision_edges
WHERE from_node_id IN (
        SELECT n.id
        FROM public.decision_nodes n
            JOIN public.decision_trees t ON t.id = n.tree_id
        WHERE t.tree_key = 'hypertension-chronic-kidney-disease'
    );
DELETE FROM public.decision_nodes
WHERE tree_id IN (
        SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-chronic-kidney-disease'
    );
DELETE FROM public.decision_trees WHERE tree_key = 'hypertension-chronic-kidney-disease';
-- ============================================================
-- 1. Tree
-- ============================================================
INSERT INTO public.decision_trees (
        "id", "tree_key", "name_en", "name_vi", "created_at", "updated_at"
    )
VALUES (
        gen_random_uuid(), 'hypertension-chronic-kidney-disease',
        'Hypertension With Chronic Kidney Disease', 'THA + Bệnh Thận Mạn', now(), now()
    );
-- ============================================================
-- 2. Nodes
-- ============================================================
WITH tree_ctx AS (
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'hypertension-chronic-kidney-disease'
),
node_seed (
    node_key, node_type, text_en, text_vi,
    condition_definition, context_patch, action_payload, global_config,
    link_target_tree_key, link_target_node_key, display_order
) AS (
    VALUES
    -- --- Entry: transplant-status branch ---
    (
        'T11_START_BP_TARGET_STATUS', 'START',
        'Tree 3: Blood pressure threshold and treatment target',
        'Cây 3: Ngưỡng huyết áp và đích điều trị',
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 0
    ),
    (
        'T11_INF_DETERMINE_TRANSPLANT_STATUS', 'INFERENCE',
        'Determine kidney transplant status', 'Xác định tình trạng ghép thận',
        NULL::jsonb,
        '{"treatment":{"has_kidney_transplant":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_kidney_transplant","to_path":"context.treatment.has_kidney_transplant","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 1
    ),
    (
        'T11_C_NOT_TRANSPLANTED', 'CONDITION', 'Not kidney-transplanted',
        'BỆNH NHÂN KHÔNG GHÉP THẬN',
        '{"path":"context.treatment.has_kidney_transplant","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 2
    ),
    (
        'T11_C_TRANSPLANTED', 'CONDITION', 'Kidney-transplanted',
        'BỆNH NHÂN ĐÃ GHÉP THẬN',
        '{"path":"context.treatment.has_kidney_transplant","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 3
    ),
    -- --- Nhánh A: not transplanted ---
    (
        'T11_INF_REGIMEN_OPTIONS', 'INFERENCE',
        'A + C, or A + D (ACE inhibitor/ARB + calcium-channel blocker, or ACE inhibitor/ARB + thiazide-like diuretic)',
        'A + C, hoặc A + D (ƯCMC/CTTA + CKCa, hoặc ƯCMC/CTTA + LT Thiazide-like)',
        NULL::jsonb,
        '{"treatment_preferences":{"combination_options":[["A","C"],["A","D"]]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 4
    ),
    (
        'T11_INF_DETERMINE_CREATININE_TEST_STATUS', 'INFERENCE',
        'Determine whether baseline creatinine was tested before',
        'Xác định đã xét nghiệm chỉ số creatinine nền trước đó hay chưa',
        NULL::jsonb,
        '{"treatment":{"has_prior_creatinine_test":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_prior_creatinine_test","to_path":"context.treatment.has_prior_creatinine_test","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 5
    ),
    (
        'T11_C_NO_PRIOR_CREATININE_TEST', 'CONDITION', 'No prior creatinine test',
        'Chưa xét nghiệm chỉ số creatinine trước đó',
        '{"path":"context.treatment.has_prior_creatinine_test","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 6
    ),
    (
        'T11_C_HAS_PRIOR_CREATININE_TEST', 'CONDITION',
        'Creatinine tested 2-4 weeks prior',
        'Từng xét nghiệm chỉ số creatinine trước đó 2-4 tuần',
        '{"path":"context.treatment.has_prior_creatinine_test","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 7
    ),
    (
        'T11_ACTION_TEST_CREATININE_AND_MONITOR', 'ACTION',
        'Test creatinine and monitor after 2-4 weeks',
        'Xét nghiệm chỉ số creatinine và theo dõi sau 2-4 tuần',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"TEST_CREATININE_AND_MONITOR","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 8
    ),
    (
        'T11_INF_DETERMINE_RAS_INHIBITOR_USE_STATUS', 'INFERENCE',
        'Determine whether the patient is still using the RAS-inhibitor (class A)',
        'Xác định còn dùng thuốc nhóm A (ức chế RAS) hay không',
        NULL::jsonb,
        '{"treatment":{"still_using_ras_inhibitor":true},"operations":[{"op":"COPY_PATH","from_path":"input.still_using_ras_inhibitor","to_path":"context.treatment.still_using_ras_inhibitor","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 9
    ),
    (
        'T11_C_STILL_USING_RAS_INHIBITOR', 'CONDITION',
        'Still using the RAS-inhibitor (class A)', 'Có còn dùng thuốc nhóm A (ức chế RAS)',
        '{"path":"context.treatment.still_using_ras_inhibitor","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 10
    ),
    (
        'T11_C_NOT_USING_RAS_INHIBITOR', 'CONDITION',
        'Has stopped or is not using the RAS-inhibitor (class A)',
        'Đã ngừng A hoặc không dùng A',
        '{"path":"context.treatment.still_using_ras_inhibitor","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 11
    ),
    (
        'T11_ACTION_TEST_CREATININE_COMPARE_PRIOR', 'ACTION',
        'Test creatinine and compare with the prior measurement',
        'Xét nghiệm chỉ số creatinine và đối chiếu với lần đo trước',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"TEST_CREATININE_COMPARE_PRIOR","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 12
    ),
    (
        'T11_INF_DETERMINE_CREATININE_INCREASE_STATUS', 'INFERENCE',
        'Determine whether creatinine increased by more than 30%',
        'Xác định creatinine có tăng >30% hay không',
        NULL::jsonb,
        '{"treatment":{"creatinine_increased_over_30_percent":false},"operations":[{"op":"COPY_PATH","from_path":"input.creatinine_increased_over_30_percent","to_path":"context.treatment.creatinine_increased_over_30_percent","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 13
    ),
    (
        'T11_C_CREATININE_NOT_INCREASED', 'CONDITION',
        'Creatinine has not increased by more than 30%', 'Creatinine không tăng >30%',
        '{"path":"context.treatment.creatinine_increased_over_30_percent","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 14
    ),
    (
        'T11_C_CREATININE_INCREASED_OVER_30_PERCENT', 'CONDITION',
        'Creatinine increased by more than 30%', 'Creatinine tăng >30%',
        '{"path":"context.treatment.creatinine_increased_over_30_percent","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 15
    ),
    (
        'T11_ACTION_MAINTAIN_REGIMEN_CREATININE_STABLE', 'ACTION', 'Maintain regimen',
        'Duy trì phác đồ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"MAINTAIN_CURRENT_REGIMEN","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 16
    ),
    (
        'T11_ACTION_REDUCE_DOSE_OR_STOP_RAS_INHIBITOR', 'ACTION',
        'Reduce dose or stop the RAS-inhibitor (class A) combination',
        'Giảm liều hoặc ngừng phối hợp A',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"REDUCE_DOSE_OR_STOP_RAS_INHIBITOR","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false,"requires_clinician_review":true}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 17
    ),
    (
        'T11_ACTION_MAINTAIN_REGIMEN_STOPPED_RAS_INHIBITOR', 'ACTION', 'Maintain regimen',
        'Duy trì phác đồ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"MAINTAIN_CURRENT_REGIMEN","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 18
    ),
    -- --- Nhánh B: kidney-transplanted ---
    (
        'T11_INF_POST_TRANSPLANT_REGIMEN_OPTIONS', 'INFERENCE',
        'First-line choice after kidney transplant: C (dihydropyridine CCB) or A (ARB); BP target <130/80 mmHg',
        'Lựa chọn đầu tay sau ghép thận: C (CKCa nhóm Dihydropyridine) hoặc A (CTTA); Mục tiêu HA <130/80 mmHg',
        NULL::jsonb,
        '{"treatment_preferences":{"combination_options":[["C"],["A"]]},"treatment":{"bp_target":{"sbp":{"upper_exclusive_mmhg":130},"dbp":{"upper_exclusive_mmhg":80},"source":"TREE_11_POST_TRANSPLANT"}}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 19
    ),
    (
        'T11_ACTION_MAINTAIN_REGIMEN_POST_TRANSPLANT', 'ACTION', 'Maintain regimen',
        'Duy trì phác đồ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"MAINTAIN_CURRENT_REGIMEN","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 20
    ),
    -- --- Shared exit: Tree 4/Tree 5 by facility capability ---
    (
        'T11_LINK_ESSENTIAL_TREATMENT_STRATEGY', 'LINK', 'Tree 4: Essential treatment strategy',
        'Cây 4: Chiến lược điều trị thiết yếu',
        '{"path":"input.facility_capability","op":"eq","value":"LIMITED_RESOURCES"}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb,
        'essential-treatment-strategy', NULL::text, 21
    ),
    (
        'T11_LINK_OPTIMAL_TREATMENT_STRATEGY', 'LINK', 'Tree 5: Optimal treatment strategy',
        'Cây 5: Chiến lược điều trị tối ưu',
        '{"path":"input.facility_capability","op":"eq","value":"FULL_RESOURCES"}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb,
        'optimal-treatment-strategy', NULL::text, 22
    ),
    (
        'T11_GLOBAL_ABBREVIATION_GLOSSARY', 'GLOBAL', 'Abbreviation glossary',
        'Chú giải viết tắt',
        NULL::jsonb, NULL::jsonb, NULL::jsonb,
        '{"kind":"ABBREVIATION_GLOSSARY","purpose":"Chú giải các chữ viết tắt nhóm thuốc dùng trong Cây 11 (hệ thống A/B/C/D), theo chú thích Bảng 22.","entries":{"1_A_uc_che_he_RAS":{"label":"A: ức chế hệ RAS","UCMC":"ức chế men chuyển","CTTA":"chẹn thụ thể angiotensin II","ARNI":"chẹn thụ thể Angiotensine-neprisyline"},"4_B_chen_Beta":{"label":"B: chẹn Beta","CB":"chẹn Beta"},"3_C_chen_kenh_Canxi":{"label":"C: chẹn kênh Canxi","CKCa":"chẹn kênh Canxi"},"2_D_loi_tieu":{"label":"D: lợi tiểu","LT":"lợi tiểu"},"6_MRA":{"label":"MRA: thuốc đối kháng thụ thể mineralocorticoid"},"5_SGLT2i":{"label":"SGLT2i: thuốc ức chế đồng vận chuyển Natri-glucose 2"}}}'::jsonb,
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
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'hypertension-chronic-kidney-disease'
),
edge_seed (from_node_key, to_node_key, traversal_order) AS (
    VALUES
    ('T11_START_BP_TARGET_STATUS', 'T11_INF_DETERMINE_TRANSPLANT_STATUS', 1),
    ('T11_INF_DETERMINE_TRANSPLANT_STATUS', 'T11_C_NOT_TRANSPLANTED', 1),
    ('T11_INF_DETERMINE_TRANSPLANT_STATUS', 'T11_C_TRANSPLANTED', 2),
    -- Nhánh A
    ('T11_C_NOT_TRANSPLANTED', 'T11_INF_REGIMEN_OPTIONS', 1),
    ('T11_INF_REGIMEN_OPTIONS', 'T11_INF_DETERMINE_CREATININE_TEST_STATUS', 1),
    ('T11_INF_DETERMINE_CREATININE_TEST_STATUS', 'T11_C_NO_PRIOR_CREATININE_TEST', 1),
    ('T11_INF_DETERMINE_CREATININE_TEST_STATUS', 'T11_C_HAS_PRIOR_CREATININE_TEST', 2),
    ('T11_C_NO_PRIOR_CREATININE_TEST', 'T11_ACTION_TEST_CREATININE_AND_MONITOR', 1),
    ('T11_ACTION_TEST_CREATININE_AND_MONITOR', 'T11_LINK_ESSENTIAL_TREATMENT_STRATEGY', 1),
    ('T11_ACTION_TEST_CREATININE_AND_MONITOR', 'T11_LINK_OPTIMAL_TREATMENT_STRATEGY', 2),
    ('T11_C_HAS_PRIOR_CREATININE_TEST', 'T11_INF_DETERMINE_RAS_INHIBITOR_USE_STATUS', 1),
    ('T11_INF_DETERMINE_RAS_INHIBITOR_USE_STATUS', 'T11_C_STILL_USING_RAS_INHIBITOR', 1),
    ('T11_INF_DETERMINE_RAS_INHIBITOR_USE_STATUS', 'T11_C_NOT_USING_RAS_INHIBITOR', 2),
    ('T11_C_STILL_USING_RAS_INHIBITOR', 'T11_ACTION_TEST_CREATININE_COMPARE_PRIOR', 1),
    ('T11_ACTION_TEST_CREATININE_COMPARE_PRIOR', 'T11_INF_DETERMINE_CREATININE_INCREASE_STATUS', 1),
    ('T11_INF_DETERMINE_CREATININE_INCREASE_STATUS', 'T11_C_CREATININE_NOT_INCREASED', 1),
    ('T11_INF_DETERMINE_CREATININE_INCREASE_STATUS', 'T11_C_CREATININE_INCREASED_OVER_30_PERCENT', 2),
    ('T11_C_CREATININE_NOT_INCREASED', 'T11_ACTION_MAINTAIN_REGIMEN_CREATININE_STABLE', 1),
    ('T11_ACTION_MAINTAIN_REGIMEN_CREATININE_STABLE', 'T11_LINK_ESSENTIAL_TREATMENT_STRATEGY', 1),
    ('T11_ACTION_MAINTAIN_REGIMEN_CREATININE_STABLE', 'T11_LINK_OPTIMAL_TREATMENT_STRATEGY', 2),
    ('T11_C_CREATININE_INCREASED_OVER_30_PERCENT', 'T11_ACTION_REDUCE_DOSE_OR_STOP_RAS_INHIBITOR', 1),
    ('T11_ACTION_REDUCE_DOSE_OR_STOP_RAS_INHIBITOR', 'T11_LINK_ESSENTIAL_TREATMENT_STRATEGY', 1),
    ('T11_ACTION_REDUCE_DOSE_OR_STOP_RAS_INHIBITOR', 'T11_LINK_OPTIMAL_TREATMENT_STRATEGY', 2),
    ('T11_C_NOT_USING_RAS_INHIBITOR', 'T11_ACTION_MAINTAIN_REGIMEN_STOPPED_RAS_INHIBITOR', 1),
    ('T11_ACTION_MAINTAIN_REGIMEN_STOPPED_RAS_INHIBITOR', 'T11_LINK_ESSENTIAL_TREATMENT_STRATEGY', 1),
    ('T11_ACTION_MAINTAIN_REGIMEN_STOPPED_RAS_INHIBITOR', 'T11_LINK_OPTIMAL_TREATMENT_STRATEGY', 2),
    -- Nhánh B
    ('T11_C_TRANSPLANTED', 'T11_INF_POST_TRANSPLANT_REGIMEN_OPTIONS', 1),
    ('T11_INF_POST_TRANSPLANT_REGIMEN_OPTIONS', 'T11_ACTION_MAINTAIN_REGIMEN_POST_TRANSPLANT', 1),
    ('T11_ACTION_MAINTAIN_REGIMEN_POST_TRANSPLANT', 'T11_LINK_ESSENTIAL_TREATMENT_STRATEGY', 1),
    ('T11_ACTION_MAINTAIN_REGIMEN_POST_TRANSPLANT', 'T11_LINK_OPTIMAL_TREATMENT_STRATEGY', 2)
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
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'hypertension-chronic-kidney-disease'
),
reference_seed (
    node_key, source_title, section_path, locator, locator_detail,
    printed_page_numbers, pdf_page_numbers, reference_note, reference_order
) AS (
    VALUES
    ('T11_START_BP_TARGET_STATUS',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.4", "title": "Tăng huyết áp và Bệnh thận mạn"}]'::jsonb,
     'Bảng 21. Ngưỡng điều trị và mục tiêu huyết áp ở bệnh nhân tăng huyết áp có bệnh thận mạn (4, 5)',
     'Entry point of the CKD tree; BP should be lowered to <130/80 mmHg in CKD per SPRINT evidence.',
     ARRAY[34]::smallint[], ARRAY[36]::smallint[],
     'Điểm vào của Cây 11; HA cần được hạ xuống <130/80mmHg ở bệnh nhân bệnh thận mạn.', 1),
    ('T11_INF_REGIMEN_OPTIONS',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.4", "title": "Tăng huyết áp và Bệnh thận mạn"}]'::jsonb,
     'Bảng 22. Chiến lược điều trị tăng huyết áp có kèm bệnh thận mạn (4, 5)',
     'Initial therapy should combine a RAS-inhibitor with a CCB or a diuretic (Class I, Level A).',
     ARRAY[35]::smallint[], ARRAY[37]::smallint[],
     'Liệu pháp ban đầu nên kết hợp thuốc ức chế RAS với CKCa hoặc thuốc lợi tiểu.', 1),
    ('T11_ACTION_TEST_CREATININE_AND_MONITOR',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.4", "title": "Tăng huyết áp và Bệnh thận mạn"}]'::jsonb,
     'Bảng 22. Chiến lược điều trị tăng huyết áp có kèm bệnh thận mạn (4, 5)',
     'Monitor BP, creatinine, and potassium every 2-4 weeks after starting or increasing a RAS-inhibitor (Class I, Level A).',
     ARRAY[35]::smallint[], ARRAY[37]::smallint[],
     'Theo dõi HA, nồng độ creatinin và kali máu mỗi 2-4 tuần sau khi bắt đầu hoặc tăng liều thuốc ức chế RAS.', 1),
    ('T11_ACTION_TEST_CREATININE_COMPARE_PRIOR',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.4", "title": "Tăng huyết áp và Bệnh thận mạn"}]'::jsonb,
     'Bảng 22. Chiến lược điều trị tăng huyết áp có kèm bệnh thận mạn (4, 5)',
     'Monitor BP, creatinine, and potassium every 2-4 weeks after starting or increasing a RAS-inhibitor (Class I, Level A).',
     ARRAY[35]::smallint[], ARRAY[37]::smallint[],
     'Theo dõi HA, nồng độ creatinin và kali máu mỗi 2-4 tuần sau khi bắt đầu hoặc tăng liều thuốc ức chế RAS.', 1),
    ('T11_C_CREATININE_INCREASED_OVER_30_PERCENT',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.4", "title": "Tăng huyết áp và Bệnh thận mạn"}]'::jsonb,
     'Bảng 22. Chiến lược điều trị tăng huyết áp có kèm bệnh thận mạn (4, 5)',
     'If serum creatinine rises more than 30% within 4 weeks of starting/increasing a RAS-inhibitor, consider reducing the dose or stopping it (Class I).',
     ARRAY[35]::smallint[], ARRAY[37]::smallint[],
     'Nếu creatinin huyết thanh tăng hơn 30% trong vòng 4 tuần, xem xét giảm liều hoặc ngừng thuốc ức chế RAS.', 1),
    ('T11_ACTION_REDUCE_DOSE_OR_STOP_RAS_INHIBITOR',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.4", "title": "Tăng huyết áp và Bệnh thận mạn"}]'::jsonb,
     'Bảng 22. Chiến lược điều trị tăng huyết áp có kèm bệnh thận mạn (4, 5)',
     'If serum creatinine rises more than 30% within 4 weeks of starting/increasing a RAS-inhibitor, consider reducing the dose or stopping it (Class I).',
     ARRAY[35]::smallint[], ARRAY[37]::smallint[],
     'Nếu creatinin huyết thanh tăng hơn 30% trong vòng 4 tuần, xem xét giảm liều hoặc ngừng thuốc ức chế RAS.', 1),
    ('T11_INF_POST_TRANSPLANT_REGIMEN_OPTIONS',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.4", "title": "Tăng huyết áp và Bệnh thận mạn"}]'::jsonb,
     'Bảng 21. Ngưỡng điều trị và mục tiêu huyết áp ở bệnh nhân tăng huyết áp có bệnh thận mạn (4, 5)',
     'After kidney transplant, BP target should be <130/80 mmHg; dihydropyridine CCB or ARB is first-line (Bảng 21 Class I; Bảng 22 Class I, Level B).',
     ARRAY[35]::smallint[], ARRAY[37]::smallint[],
     'Sau ghép thận, mục tiêu HA nên <130/80mmHg; CKCa Dihydropyridine hoặc CTTA là thuốc được chọn đầu tay.', 1),
    ('T11_GLOBAL_ABBREVIATION_GLOSSARY',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.7.4", "title": "Tăng huyết áp và Bệnh thận mạn"}]'::jsonb,
     'Bảng 22. Chiến lược điều trị tăng huyết áp có kèm bệnh thận mạn (4, 5), chú thích',
     'Footnote abbreviation glossary for the drug classes named in Bảng 22.',
     ARRAY[35]::smallint[], ARRAY[37]::smallint[],
     'Chú thích Bảng 22: RAS, CKCa, CTTA, MLCT.', 1)
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
