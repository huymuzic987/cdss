--
-- CDSS decision-tree insert script (seventh pass — internal bookkeeping
-- nodes reclassified from ACTION to INFERENCE so they stop appearing in the
-- clinician-facing action trail; sixth pass added the specific-clinical-
-- situation beta-blocker check to every regimen tier; fifth pass cross-
-- checked against Tree 4/Tree 5 and drug-list removed; fourth pass rebuilt
-- to match the author's own 5-image board description, verbatim)
--
-- SEVENTH PASS: T6_ACTION_COMPARE_WITH_CURRENT_PRESCRIPTION,
-- T6_ACTION_ADJUST_REGIMEN, T6_ACTION_MAINTAIN_REGIMEN_NO_ADJUSTMENT,
-- T6_ACTION_KEEP_ONE_OR_REMOVE_BOTH, T6_ACTION_KEEP_ONE_DRUG, and
-- T6_ACTION_MAINTAIN_REGIMEN_NO_DUPLICATE were ACTION nodes even though they
-- are non-terminal steps in this tree's own internal logic (every node has
-- an outgoing edge, so none of them end a walk) -- the engine appends one
-- ExecutedAction per ACTION/END node entered, so a single traversal through
-- several of these produced a stack of intermediate "actions" on top of the
-- real terminal recommendation. Reclassified all six to INFERENCE (their
-- context_patch is preserved; action_payload cleared) so only genuine
-- terminal nodes populate the action trail. T6_ACTION_CHECK_DUPLICATE_DRUG_CLASS
-- was removed outright (it did nothing but copy two input fields into
-- context, exactly like an INFERENCE node, but under an ACTION label with no
-- real content of its own) -- its context_patch and Bảng-9 citation were
-- folded into T6_INF_DETERMINE_CONTRAINDICATIONS, which now branches
-- directly to T6_C_HAS_DUPLICATE_DRUG_CLASS / T6_C_NO_DUPLICATE_DRUG_CLASS.
--
-- SIXTH PASS: the specific-clinical-situation check (angina, post-MI, heart
-- failure, AFib, tachycardia, pregnancy) previously only gated the 2-drug
-- initiation tier. Per the author: having a specific clinical situation
-- means beta-blocker must be used regardless of whether the patient ends up
-- on 1, 2, or 3 drugs. The engine's single-path-per-node semantics mean this
-- check can't be shared across tiers as one branch (the "next step" after a
-- shared condition must be identical for every entry path, but each tier
-- needs a different outcome), so it is now duplicated per tier: monotherapy
-- gets its own T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_MONOTHERAPY ->
-- T6_C_HAS/NO_SPECIFIC_CLINICAL_SITUATION_MONOTHERAPY -> mandates
-- combination_options:[["B"]] when present (matching T4/T5's own
-- "beta_blocker_requires_indication" note, now properly enforced rather than
-- just annotated); the 3-drug escalation tier gets the same pattern via
-- T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_ESCALATION -> adds B to
-- additional_drug_classes when present. The existing 2-drug tier's check was
-- already correct and is unchanged.
--
-- FIFTH PASS: T6_C_SPECIAL_POPULATION/NOT_SPECIAL_POPULATION previously used
-- a condition invented from this tree's own reading of Bảng 9's prose
-- ((age>=80 AND frailty) OR (HIGH_NORMAL_BP AND low/medium risk)), which
-- does not match the already-seeded T4_C_MONOTHERAPY_ELIGIBILITY /
-- T5_C_MONOTHERAPY_ELIGIBILITY condition (is_lifestyle_follow_up OR age>=80
-- OR frailty, independently OR'd). Since Trees 4/5 already decide and
-- communicate the monotherapy-vs-combination tier via their own action
-- before an unconditional LINK into this tree's START, Tree 6 must reuse
-- the exact same condition or it can silently contradict what the patient
-- was already told. Fixed to match verbatim. Also added class B
-- (beta-blocker, requires_indication) to the monotherapy combination_options
-- menu, matching T4_ACTION_CONSIDER_MONOTHERAPY/
-- T5_ACTION_CONSIDER_MONOTHERAPY_ONE_PILL's drug_options exactly (previously
-- only offered A/C/D). Also removed T6_GLOBAL_DRUG_CLASS_GLOSSARY (the
-- Bảng-10-sourced list of specific drug names per class) — a separate drug
-- table is planned, so specific drug names no longer live in tree seed data.
-- Tree: "Cây 6: Phối Hợp Thuốc - Minh"
-- Source: Bảng 9, Bảng 10, Bảng 11, Hình 5, Mục 3.6.1
-- (Khuyến cáo THA VNHA 2022.pdf):
--   Bảng 9  -> printed p.20 / PDF page 22
--   Bảng 10 -> printed p.21-22 / PDF pages 23-24
--   Bảng 11 -> printed p.23 / PDF page 25
--   Hình 5 & Mục 3.6.1 -> printed p.24 / PDF page 26
--
-- 'drug-combination' already exists in the target database from earlier
-- passes; Section 0 deletes it first (FK-safe order), so this script is
-- safe to re-run.
--
-- WHAT CHANGED THIS PASS, after the author supplied the authoritative
-- 4-step description of their own board (previously only inferred from a
-- raw SVG export):
--
-- 1. RESTORED Step 1's prescription-review sub-flow (first visit / follow-up
--    -> has prior prescription? -> compare with current prescription ->
--    dosage-adjustment requested?). The previous pass deleted this on the
--    wrong assumption that has_prior_prescription/has_dosage_adjustment_request
--    were fabricated with no grounding. They are real (from the author's own
--    diagram) — the correct fix was to make them runtime-safe, not delete
--    them. Both now go through the established safe-default pattern: an
--    INFERENCE/ACTION node merges a static default, then COPY_PATH
--    (required:false) overlays the caller-supplied value if present.
-- 2. RESTORED the two-level duplicate-drug-class check (general "duplicate
--    same class -> keep 1" plus the specific "dual RAS-inhibitor blockade ->
--    keep 1 or remove both" sub-case), which the previous pass had
--    collapsed into a single RAS-only check.
-- 3. Per the author: the duplicate-drug-class check (Step 3) runs
--    unconditionally for every patient, not just follow-up visits — for a
--    fresh patient the safely-defaulted facts simply resolve to
--    "no duplicate found" and the tree proceeds.
-- 4. Per the author: Step 1 and Step 3's "Duy trì phác đồ" / resolution
--    nodes are NOT terminal — they are ACTION nodes with outgoing edges
--    that continue on into Step 4's combination-therapy logic, matching the
--    board's literal "tất cả hội tụ về Phối hợp thuốc" convergence.
-- 5. REMOVED the mandatory-indication chain (coronary artery disease / HFrEF
--    / stroke / CKD / high-risk T2DM -> specific mandatory combos) that the
--    previous pass added. That content does not appear anywhere in the
--    author's 4-step board description; it was pulled in from general
--    ESC/VNHA guideline knowledge, not from this tree's actual source
--    material, so it does not belong in Cây 6.
-- 6. RESTORED the full 5-example "specific clinical situation" list for the
--    beta-blocker add-on (angina, post-MI, atrial fibrillation, tachycardia,
--    pregnancy), matching the author's board — the previous pass had
--    trimmed this to just the PDF citation's terser phrasing (angina,
--    post-MI, heart failure, rate control). Each newly-added flag still
--    uses the safe-default pattern so it never raises MissingRuntimePath.
-- 7. ADDED a `was_on_monotherapy` safely-defaulted fact to distinguish, on a
--    follow-up visit still at the "INITIAL_REGIMEN" stage, whether the prior
--    regimen was monotherapy (-> escalate to the 2-drug low-dose path) or
--    already 2-drug (-> escalate to full-dose/3-drug). The established
--    medication_follow_up_stage enum only has two values
--    (INITIAL_REGIMEN/ESCALATED_REGIMEN) and can't represent this 3-way
--    distinction on its own.
-- 8. FIXED two Bảng 11 contraindication-table gaps found on this pass:
--    MRA's absolute contraindications were missing pregnancy, and the
--    "Direct renin inhibitor / Vasodilator" drug-class row (absolute:
--    pregnancy) was missing entirely.
--
-- ARCHITECTURE NOTE, unchanged: the 8-drug-class contraindication table
-- (Bảng 11) is not modeled as branching condition/inference nodes because
-- the engine follows exactly one path per node (first matching candidate
-- among siblings) and cannot evaluate independent facts in parallel. It is
-- carried into context as one pre-computed COPY_PATH (matching
-- T3_INF_RESTORE_ACTIVE_BP_TARGET's precedent), with the full table
-- preserved as documented metadata on
-- T6_GLOBAL_CONTRAINDICATION_REFERENCE_TABLE.
--
-- RUNTIME-SAFETY NOTE, unchanged: every fact not in this system's closed,
-- frozen input contract (docs/cdss/context-contract.md,
-- docs/cdss/traversal-engine-contract.md, frontend's MockPatientSidebar.tsx)
-- is written through a node whose context_patch merges a static default,
-- then COPY_PATH(required:false) overlays the caller-supplied value if
-- present. Downstream CONDITIONs read the always-present context.* copy,
-- never the possibly-absent input.* original.
--
-- IMPORTANT — still worth a final visual check against the original board:
--   1. Exact wording/labels are approximated in English/Vietnamese from the
--      author's prose description, not read pixel-by-pixel from the image.
--   2. "Cây 5" was explicitly declined as an escalation LINK target (author
--      chose to keep 3-drug escalation inline in Tree 6 instead).
--   3. "Cây 14: THA Kháng Trị" is modeled as a LINK to tree_key
--      'resistant-hypertension' (unseeded, per docs/cdss/tree-json-dialect.md
--      §10's list of expected-but-unseeded targets).
--
-- Use: cmd /c "docker compose exec -T postgres psql -U cdss -d cdss < backups\tree6.sql"
--

BEGIN;
-- ============================================================
-- 0. Remove the existing drug-combination tree, if present
-- ============================================================
DELETE FROM public.node_source_references
WHERE node_id IN (
        SELECT n.id
        FROM public.decision_nodes n
            JOIN public.decision_trees t ON t.id = n.tree_id
        WHERE t.tree_key = 'drug-combination'
    );
DELETE FROM public.decision_edges
WHERE from_node_id IN (
        SELECT n.id
        FROM public.decision_nodes n
            JOIN public.decision_trees t ON t.id = n.tree_id
        WHERE t.tree_key = 'drug-combination'
    );
DELETE FROM public.decision_nodes
WHERE tree_id IN (
        SELECT id FROM public.decision_trees WHERE tree_key = 'drug-combination'
    );
DELETE FROM public.decision_trees WHERE tree_key = 'drug-combination';
-- ============================================================
-- 1. Tree
-- ============================================================
INSERT INTO public.decision_trees (
        "id", "tree_key", "name_en", "name_vi", "created_at", "updated_at"
    )
VALUES (
        gen_random_uuid(), 'drug-combination', 'Drug Combination', 'Phối hợp thuốc', now(), now()
    );
-- ============================================================
-- 2. Nodes
-- ============================================================
WITH tree_ctx AS (
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'drug-combination'
),
node_seed (
    node_key, node_type, text_en, text_vi,
    condition_definition, context_patch, action_payload, global_config,
    link_target_tree_key, link_target_node_key, display_order
) AS (
    VALUES
    -- --- Step 1: visit type + existing-prescription review (Ảnh 1) ---
    (
        'T6_START_PATIENT_INFO_AND_PRESCRIPTIONS', 'START',
        'Patient information + prescribed medications',
        'Thông tin bệnh nhân + Các đơn thuốc chỉ định',
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 0
    ),
    (
        'T6_C_FIRST_VISIT', 'CONDITION', 'First visit', 'Khám lần đầu',
        '{"path":"input.is_medication_follow_up","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 1
    ),
    (
        'T6_C_FOLLOW_UP_VISIT', 'CONDITION', 'Follow-up visit', 'Tái khám',
        '{"path":"input.is_medication_follow_up","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 2
    ),
    (
        'T6_INF_DETERMINE_PRIOR_PRESCRIPTION_STATUS', 'INFERENCE',
        'Determine whether a prior prescription exists',
        'Xác định có đơn thuốc trước đó hay không',
        NULL::jsonb,
        '{"treatment":{"has_prior_prescription":true},"operations":[{"op":"COPY_PATH","from_path":"input.has_prior_prescription","to_path":"context.treatment.has_prior_prescription","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 3
    ),
    (
        'T6_C_HAS_PRIOR_PRESCRIPTION', 'CONDITION', 'Has prior prescription', 'Có đơn thuốc trước đó',
        '{"path":"context.treatment.has_prior_prescription","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 4
    ),
    (
        'T6_C_NO_PRIOR_PRESCRIPTION', 'CONDITION', 'No prior prescription', 'Không có đơn thuốc trước đó',
        '{"path":"context.treatment.has_prior_prescription","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 5
    ),
    (
        'T6_ACTION_COMPARE_WITH_CURRENT_PRESCRIPTION', 'INFERENCE',
        'Compare with current prescription', 'So sánh với đơn thuốc hiện tại',
        NULL::jsonb,
        '{"treatment":{"has_dosage_adjustment_request":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_dosage_adjustment_request","to_path":"context.treatment.has_dosage_adjustment_request","required":false}]}'::jsonb,
        NULL::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 6
    ),
    (
        'T6_C_DOSAGE_ADJUSTMENT_REQUESTED', 'CONDITION',
        'Dosage adjustment requested in current prescription',
        'Có yêu cầu điều chỉnh liều lượng trong đơn thuốc hiện tại',
        '{"path":"context.treatment.has_dosage_adjustment_request","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 7
    ),
    (
        'T6_C_NO_DOSAGE_ADJUSTMENT_REQUESTED', 'CONDITION',
        'No dosage adjustment requested in current prescription',
        'Không có yêu cầu điều chỉnh liều lượng trong đơn thuốc hiện tại',
        '{"path":"context.treatment.has_dosage_adjustment_request","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 8
    ),
    (
        'T6_ACTION_ADJUST_REGIMEN', 'INFERENCE', 'Adjust regimen', 'Điều chỉnh phác đồ',
        NULL::jsonb, '{"treatment":{"status":"ADJUST_REGIMEN"}}'::jsonb,
        NULL::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 9
    ),
    (
        'T6_ACTION_MAINTAIN_REGIMEN_NO_ADJUSTMENT', 'INFERENCE', 'Maintain regimen', 'Duy trì phác đồ',
        NULL::jsonb, NULL::jsonb,
        NULL::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 10
    ),
    -- --- Step 2: contraindication determination (reference lookup, see architecture note) ---
    (
        'T6_INF_DETERMINE_CONTRAINDICATIONS', 'INFERENCE',
        'Determine contraindicated drug classes based on patient information and current regimen',
        'Xác định thuốc chống chỉ định dựa trên thông tin bệnh nhân và phác đồ hiện tại',
        NULL::jsonb,
        '{"treatment":{"has_duplicate_drug_class":false,"has_duplicate_ras_inhibitor":false},"operations":[{"op":"COPY_PATH","from_path":"input.contraindicated_drug_classes","to_path":"context.treatment.contraindicated_drug_classes","required":false},{"op":"COPY_PATH","from_path":"input.has_duplicate_drug_class","to_path":"context.treatment.has_duplicate_drug_class","required":false},{"op":"COPY_PATH","from_path":"input.has_duplicate_ras_inhibitor","to_path":"context.treatment.has_duplicate_ras_inhibitor","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 11
    ),
    (
        'T6_GLOBAL_CONTRAINDICATION_REFERENCE_TABLE', 'GLOBAL',
        'Drug-class contraindication reference table (Bảng 11)',
        'Bảng chống chỉ định theo nhóm thuốc (Bảng 11)',
        NULL::jsonb, NULL::jsonb, NULL::jsonb,
        '{"kind":"REFERENCE_LIST","purpose":"Chống chỉ định bắt buộc/tương đối theo nhóm thuốc, dùng để tính input.contraindicated_drug_classes trước khi vào Cây 6.","input_path":"input.contraindicated_drug_classes","table":{"THIAZIDE_LIKE_DIURETIC":{"absolute":["gout"],"relative":["metabolic_syndrome","glucose_intolerance","pregnancy","hypercalcemia","hypokalemia"]},"BETA_BLOCKER":{"absolute":["asthma","sinoatrial_or_high_grade_av_block","bradycardia_lt_60"],"relative":["metabolic_syndrome","glucose_intolerance","athlete"]},"DIHYDROPYRIDINE_CCB":{"relative":["tachyarrhythmia","heart_failure_reduced_ef_nyha_3_or_4","severe_leg_edema_history"]},"NON_DIHYDROPYRIDINE_CCB":{"absolute":["sinoatrial_or_high_grade_av_block","severe_lv_dysfunction_lvef_lt_40","bradycardia_lt_60"],"relative":["constipation"]},"ACE_INHIBITOR":{"absolute":["pregnancy","angioedema_history","hyperkalemia_gt_5_5","bilateral_renal_artery_stenosis"],"relative":["woman_of_childbearing_age_without_contraception"]},"ARB":{"absolute":["pregnancy","hyperkalemia_gt_5_5","bilateral_renal_artery_stenosis"],"relative":["woman_of_childbearing_age_without_contraception"]},"MRA":{"absolute":["pregnancy","hyperkalemia","severe_acute_renal_failure_egfr_lt_30"]},"DIRECT_RENIN_INHIBITOR_OR_VASODILATOR":{"absolute":["pregnancy"]}}}'::jsonb,
        NULL::text, NULL::text, 12
    ),
    -- --- Step 3: duplicate drug-class check (folded into T6_INF_DETERMINE_CONTRAINDICATIONS above) ---
    (
        'T6_C_HAS_DUPLICATE_DRUG_CLASS', 'CONDITION',
        'Has duplicate drug class (e.g. 2 drugs of the same class)',
        'Có nhiều thuốc trùng nhóm (VD 2 thuốc cùng nhóm ƯCMC)',
        '{"path":"context.treatment.has_duplicate_drug_class","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 14
    ),
    (
        'T6_C_NO_DUPLICATE_DRUG_CLASS', 'CONDITION', 'No duplicate drug class',
        'Không có thuốc trùng nhóm',
        '{"path":"context.treatment.has_duplicate_drug_class","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 15
    ),
    (
        'T6_C_DUPLICATE_IS_RAS_INHIBITOR', 'CONDITION',
        'Regimen uses more than 2 RAS-inhibitor classes in parallel',
        'Phác đồ dùng >2 loại ức chế RAS song song',
        '{"path":"context.treatment.has_duplicate_ras_inhibitor","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 16
    ),
    (
        'T6_C_DUPLICATE_NOT_RAS_INHIBITOR', 'CONDITION',
        'Duplicate is within a single non-RAS drug class',
        'Trùng nhóm không thuộc nhóm ức chế RAS',
        '{"path":"context.treatment.has_duplicate_ras_inhibitor","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 17
    ),
    (
        'T6_ACTION_KEEP_ONE_OR_REMOVE_BOTH', 'INFERENCE',
        'Keep only 1 drug or remove both; prefer keeping the one already in use, only remove both for a special requirement',
        'Chỉ giữ lại 1 thuốc hoặc loại bỏ cả hai. Ưu tiên giữ lại thuốc đã hoặc đang dùng trước đó, chỉ loại bỏ cả hai khi có yêu cầu đặc biệt',
        NULL::jsonb, NULL::jsonb,
        NULL::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 18
    ),
    (
        'T6_ACTION_KEEP_ONE_DRUG', 'INFERENCE', 'Keep only 1 drug', 'Chỉ giữ lại 1 thuốc',
        NULL::jsonb, NULL::jsonb,
        NULL::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 19
    ),
    (
        'T6_ACTION_MAINTAIN_REGIMEN_NO_DUPLICATE', 'INFERENCE', 'Maintain regimen', 'Duy trì phác đồ',
        NULL::jsonb, NULL::jsonb,
        NULL::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 20
    ),
    -- --- Encounter-type convergence (reused established field a 2nd time) ---
    (
        'T6_C_IS_FIRST_VISIT_FOR_REGIMEN', 'CONDITION',
        'Encounter is a fresh-therapy visit', 'Đây là lần khám điều trị lần đầu',
        '{"path":"input.is_medication_follow_up","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 21
    ),
    (
        'T6_C_IS_FOLLOW_UP_FOR_REGIMEN', 'CONDITION',
        'Encounter is a medication follow-up visit', 'Đây là lần tái khám điều trị thuốc',
        '{"path":"input.is_medication_follow_up","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 22
    ),
    -- --- Step 4: fresh-therapy initiation (Nhánh A / Nhánh B, Bảng 9) ---
    (
        'T6_C_SPECIAL_POPULATION', 'CONDITION',
        'Persistent high-normal BP after lifestyle management, age 80 or older, or frailty syndrome',
        'HABTC không đạt mục tiêu sau thay đổi lối sống hoặc tuổi >= 80 hoặc hội chứng lão hóa',
        '{"any":[{"path":"input.is_lifestyle_follow_up","op":"eq","value":true},{"path":"input.age","op":"gte","value":80},{"path":"input.has_frailty_syndrome","op":"eq","value":true}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 23
    ),
    (
        'T6_C_NOT_SPECIAL_POPULATION', 'CONDITION', 'Not a special population',
        'BỆNH NHÂN KHÔNG THUỘC NHÓM ĐẶC BIỆT',
        '{"not":{"any":[{"path":"input.is_lifestyle_follow_up","op":"eq","value":true},{"path":"input.age","op":"gte","value":80},{"path":"input.has_frailty_syndrome","op":"eq","value":true}]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 24
    ),
    (
        'T6_INF_INITIATE_MONOTHERAPY', 'INFERENCE',
        'Drug therapy: start with 1 drug (A, C, or D)',
        'Điều trị thuốc KHỞI ĐẦU BẰNG 1 THUỐC (A, C, hoặc D)',
        NULL::jsonb,
        '{"treatment_preferences":{"combination_options":[["A"],["C"],["D"]],"dose_strategy":"LOW_TO_USUAL_DOSE"}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 25
    ),
    (
        'T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_MONOTHERAPY', 'INFERENCE',
        'Determine specific clinical situations relevant to beta-blocker add-on (monotherapy tier)',
        'Xác định tình huống lâm sàng đặc hiệu liên quan đến việc thêm chẹn Beta (bậc đơn trị)',
        NULL::jsonb,
        '{"treatment":{"has_angina":false,"has_prior_mi":false,"has_atrial_fibrillation":false,"has_tachycardia":false,"is_pregnant":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_angina","to_path":"context.treatment.has_angina","required":false},{"op":"COPY_PATH","from_path":"input.has_prior_mi","to_path":"context.treatment.has_prior_mi","required":false},{"op":"COPY_PATH","from_path":"input.has_atrial_fibrillation","to_path":"context.treatment.has_atrial_fibrillation","required":false},{"op":"COPY_PATH","from_path":"input.has_tachycardia","to_path":"context.treatment.has_tachycardia","required":false},{"op":"COPY_PATH","from_path":"input.is_pregnant","to_path":"context.treatment.is_pregnant","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 250
    ),
    (
        'T6_C_HAS_SPECIFIC_CLINICAL_SITUATION_MONOTHERAPY', 'CONDITION',
        'Has specific clinical situation (monotherapy tier)',
        'CÓ TÌNH HUỐNG LÂM SÀNG ĐẶC HIỆU (bậc đơn trị)',
        '{"any":[{"path":"input.has_heart_failure","op":"eq","value":true},{"path":"context.treatment.has_angina","op":"eq","value":true},{"path":"context.treatment.has_prior_mi","op":"eq","value":true},{"path":"context.treatment.has_atrial_fibrillation","op":"eq","value":true},{"path":"context.treatment.has_tachycardia","op":"eq","value":true},{"path":"context.treatment.is_pregnant","op":"eq","value":true}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 251
    ),
    (
        'T6_C_NO_SPECIFIC_CLINICAL_SITUATION_MONOTHERAPY', 'CONDITION',
        'No specific clinical situation (monotherapy tier)',
        'KHÔNG CÓ TÌNH HUỐNG LÂM SÀNG ĐẶC HIỆU (bậc đơn trị)',
        '{"not":{"any":[{"path":"input.has_heart_failure","op":"eq","value":true},{"path":"context.treatment.has_angina","op":"eq","value":true},{"path":"context.treatment.has_prior_mi","op":"eq","value":true},{"path":"context.treatment.has_atrial_fibrillation","op":"eq","value":true},{"path":"context.treatment.has_tachycardia","op":"eq","value":true},{"path":"context.treatment.is_pregnant","op":"eq","value":true}]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 252
    ),
    (
        'T6_INF_MONOTHERAPY_ADD_BETA_BLOCKER', 'INFERENCE',
        'Mandate beta-blocker monotherapy', 'Bắt buộc đơn trị bằng chẹn Beta',
        NULL::jsonb,
        '{"treatment_preferences":{"combination_options":[["B"]]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 253
    ),
    (
        'T6_END_INITIAL_MONOTHERAPY_WITH_BETA_BLOCKER', 'END',
        'Start beta-blocker monotherapy; reassess at next encounter',
        'Bắt đầu đơn trị bằng chẹn Beta; đánh giá lại ở lần tái khám kế tiếp',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"CONSIDER_MONOTHERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"next_medication_follow_up_stage":"INITIAL_REGIMEN"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 254
    ),
    (
        'T6_END_INITIAL_MONOTHERAPY', 'END', 'Start monotherapy; reassess at next encounter',
        'Bắt đầu đơn trị; đánh giá lại ở lần tái khám kế tiếp',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"CONSIDER_MONOTHERAPY","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"next_medication_follow_up_stage":"INITIAL_REGIMEN"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 26
    ),
    (
        'T6_INF_INITIATE_TWO_DRUG_LOW_DOSE', 'INFERENCE',
        'Drug therapy: start with 2 low-dose drugs (A combined with C or D)',
        'Điều trị thuốc KHỞI ĐẦU BẰNG 2 THUỐC LIỀU THẤP (kết hợp A cùng C hoặc D)',
        NULL::jsonb,
        '{"treatment_preferences":{"combination_options":[["A","C"],["A","D"]],"dose_strategy":"LOW_DOSE"}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 27
    ),
    (
        'T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS', 'INFERENCE',
        'Determine specific clinical situations relevant to beta-blocker add-on',
        'Xác định tình huống lâm sàng đặc hiệu liên quan đến việc thêm chẹn Beta',
        NULL::jsonb,
        '{"treatment":{"has_angina":false,"has_prior_mi":false,"has_atrial_fibrillation":false,"has_tachycardia":false,"is_pregnant":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_angina","to_path":"context.treatment.has_angina","required":false},{"op":"COPY_PATH","from_path":"input.has_prior_mi","to_path":"context.treatment.has_prior_mi","required":false},{"op":"COPY_PATH","from_path":"input.has_atrial_fibrillation","to_path":"context.treatment.has_atrial_fibrillation","required":false},{"op":"COPY_PATH","from_path":"input.has_tachycardia","to_path":"context.treatment.has_tachycardia","required":false},{"op":"COPY_PATH","from_path":"input.is_pregnant","to_path":"context.treatment.is_pregnant","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 28
    ),
    (
        'T6_C_HAS_SPECIFIC_CLINICAL_SITUATION', 'CONDITION',
        'Has specific clinical situation (heart failure, angina, post-MI, atrial fibrillation, tachycardia, or pregnancy)',
        'CÓ CÁC TÌNH HUỐNG LÂM SÀNG ĐẶC HIỆU: SUY TIM, ĐAU THẮT NGỰC, SAU NMCT, RUNG NHĨ, NHỊP TIM NHANH, THAI KỲ',
        '{"any":[{"path":"input.has_heart_failure","op":"eq","value":true},{"path":"context.treatment.has_angina","op":"eq","value":true},{"path":"context.treatment.has_prior_mi","op":"eq","value":true},{"path":"context.treatment.has_atrial_fibrillation","op":"eq","value":true},{"path":"context.treatment.has_tachycardia","op":"eq","value":true},{"path":"context.treatment.is_pregnant","op":"eq","value":true}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 29
    ),
    (
        'T6_C_NO_SPECIFIC_CLINICAL_SITUATION', 'CONDITION', 'No specific clinical situation',
        'KHÔNG CÓ CÁC TÌNH HUỐNG LÂM SÀNG ĐẶC HIỆU',
        '{"not":{"any":[{"path":"input.has_heart_failure","op":"eq","value":true},{"path":"context.treatment.has_angina","op":"eq","value":true},{"path":"context.treatment.has_prior_mi","op":"eq","value":true},{"path":"context.treatment.has_atrial_fibrillation","op":"eq","value":true},{"path":"context.treatment.has_tachycardia","op":"eq","value":true},{"path":"context.treatment.is_pregnant","op":"eq","value":true}]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 30
    ),
    (
        'T6_INF_ADD_BETA_BLOCKER', 'INFERENCE', 'Add beta-blocker', 'Thêm thuốc chẹn Beta',
        NULL::jsonb, '{"treatment_preferences":{"additional_drug_classes":["B"]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 31
    ),
    (
        'T6_END_INITIAL_TWO_DRUG_WITH_BETA_BLOCKER', 'END',
        'Start 2-drug low-dose combination plus beta-blocker; reassess at next encounter',
        'Bắt đầu phối hợp 2 thuốc liều thấp kèm chẹn Beta; đánh giá lại ở lần tái khám kế tiếp',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"INITIAL_TWO_DRUG_COMBINATION","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"next_medication_follow_up_stage":"INITIAL_REGIMEN"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 32
    ),
    (
        'T6_END_INITIAL_TWO_DRUG', 'END',
        'Start 2-drug low-dose combination; reassess at next encounter',
        'Bắt đầu phối hợp 2 thuốc liều thấp; đánh giá lại ở lần tái khám kế tiếp',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"INITIAL_TWO_DRUG_COMBINATION","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"next_medication_follow_up_stage":"INITIAL_REGIMEN"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 33
    ),
    -- --- Step 4 continued: follow-up target check and escalation ---
    (
        'T6_C_TARGET_ACHIEVED', 'CONDITION',
        'BP target achieved on current regimen',
        'Đạt đích điều trị với phác đồ hiện tại',
        '{"all":[{"path":"input.current_clinic_sbp","op":"lt","value_from_path":"context.treatment.bp_target.sbp.upper_exclusive_mmhg"},{"path":"input.current_clinic_dbp","op":"lt","value_from_path":"context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 34
    ),
    (
        'T6_C_TARGET_NOT_ACHIEVED', 'CONDITION',
        'BP target not achieved on current regimen',
        'Không đạt đích điều trị với phác đồ hiện tại',
        '{"any":[{"path":"input.current_clinic_sbp","op":"gte","value_from_path":"context.treatment.bp_target.sbp.upper_exclusive_mmhg"},{"path":"input.current_clinic_dbp","op":"gte","value_from_path":"context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 35
    ),
    (
        'T6_END_MAINTAIN_AND_MONITOR', 'END', 'Maintain current regimen and monitor',
        'Duy trì phác đồ hiện tại và theo dõi',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"MAINTAIN_CURRENT_REGIMEN","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 36
    ),
    (
        'T6_C_FOLLOWUP_INITIAL_STAGE', 'CONDITION',
        'Follow-up on the initial regimen, target not achieved',
        'Tái khám ở giai đoạn phác đồ ban đầu, chưa đạt đích',
        '{"path":"input.medication_follow_up_stage","op":"eq","value":"INITIAL_REGIMEN"}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 37
    ),
    (
        'T6_C_FOLLOWUP_ESCALATED_STAGE', 'CONDITION',
        'Follow-up already on an escalated 3-drug regimen, still not achieved',
        'Tái khám đã ở phác đồ 3 thuốc, vẫn chưa đạt đích',
        '{"path":"input.medication_follow_up_stage","op":"eq","value":"ESCALATED_REGIMEN"}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 38
    ),
    (
        'T6_INF_DETERMINE_PRIOR_REGIMEN_INTENSITY', 'INFERENCE',
        'Determine whether the prior regimen was monotherapy or a 2-drug combination',
        'Xác định phác đồ trước đó là đơn trị hay phối hợp 2 thuốc',
        NULL::jsonb,
        '{"treatment":{"was_on_monotherapy":false},"operations":[{"op":"COPY_PATH","from_path":"input.was_on_monotherapy","to_path":"context.treatment.was_on_monotherapy","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 39
    ),
    (
        'T6_C_WAS_ON_MONOTHERAPY', 'CONDITION', 'Prior regimen was monotherapy',
        'Phác đồ trước đó là đơn trị',
        '{"path":"context.treatment.was_on_monotherapy","op":"eq","value":true}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 40
    ),
    (
        'T6_C_WAS_NOT_ON_MONOTHERAPY', 'CONDITION', 'Prior regimen was already a 2-drug combination',
        'Phác đồ trước đó đã là phối hợp 2 thuốc',
        '{"path":"context.treatment.was_on_monotherapy","op":"eq","value":false}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 41
    ),
    (
        'T6_INF_ESCALATE_TO_FULL_DOSE_OR_THREE_DRUG', 'INFERENCE',
        'Increase dose of 2-drug combination, or move to 3-drug combination (A+C+D)',
        'Tăng liều phối hợp 2 thuốc, hoặc chuyển phối hợp 3 thuốc (A+C+D)',
        NULL::jsonb,
        '{"treatment_preferences":{"escalation_options":[{"strategy":"INCREASE_DOSE_TWO_DRUG"},{"strategy":"THREE_DRUG_COMBINATION","classes":["A","C","D"]}]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 42
    ),
    (
        'T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_ESCALATION', 'INFERENCE',
        'Determine specific clinical situations relevant to beta-blocker add-on (escalation tier)',
        'Xác định tình huống lâm sàng đặc hiệu liên quan đến việc thêm chẹn Beta (bậc leo thang)',
        NULL::jsonb,
        '{"treatment":{"has_angina":false,"has_prior_mi":false,"has_atrial_fibrillation":false,"has_tachycardia":false,"is_pregnant":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_angina","to_path":"context.treatment.has_angina","required":false},{"op":"COPY_PATH","from_path":"input.has_prior_mi","to_path":"context.treatment.has_prior_mi","required":false},{"op":"COPY_PATH","from_path":"input.has_atrial_fibrillation","to_path":"context.treatment.has_atrial_fibrillation","required":false},{"op":"COPY_PATH","from_path":"input.has_tachycardia","to_path":"context.treatment.has_tachycardia","required":false},{"op":"COPY_PATH","from_path":"input.is_pregnant","to_path":"context.treatment.is_pregnant","required":false}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 260
    ),
    (
        'T6_C_HAS_SPECIFIC_CLINICAL_SITUATION_ESCALATION', 'CONDITION',
        'Has specific clinical situation (escalation tier)',
        'CÓ TÌNH HUỐNG LÂM SÀNG ĐẶC HIỆU (bậc leo thang)',
        '{"any":[{"path":"input.has_heart_failure","op":"eq","value":true},{"path":"context.treatment.has_angina","op":"eq","value":true},{"path":"context.treatment.has_prior_mi","op":"eq","value":true},{"path":"context.treatment.has_atrial_fibrillation","op":"eq","value":true},{"path":"context.treatment.has_tachycardia","op":"eq","value":true},{"path":"context.treatment.is_pregnant","op":"eq","value":true}]}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 261
    ),
    (
        'T6_C_NO_SPECIFIC_CLINICAL_SITUATION_ESCALATION', 'CONDITION',
        'No specific clinical situation (escalation tier)',
        'KHÔNG CÓ TÌNH HUỐNG LÂM SÀNG ĐẶC HIỆU (bậc leo thang)',
        '{"not":{"any":[{"path":"input.has_heart_failure","op":"eq","value":true},{"path":"context.treatment.has_angina","op":"eq","value":true},{"path":"context.treatment.has_prior_mi","op":"eq","value":true},{"path":"context.treatment.has_atrial_fibrillation","op":"eq","value":true},{"path":"context.treatment.has_tachycardia","op":"eq","value":true},{"path":"context.treatment.is_pregnant","op":"eq","value":true}]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 262
    ),
    (
        'T6_INF_ESCALATE_ADD_BETA_BLOCKER', 'INFERENCE',
        'Add beta-blocker to escalated regimen', 'Thêm chẹn Beta vào phác đồ leo thang',
        NULL::jsonb,
        '{"treatment_preferences":{"additional_drug_classes":["B"]}}'::jsonb,
        NULL::jsonb, NULL::jsonb, NULL::text, NULL::text, 263
    ),
    (
        'T6_END_ESCALATE_REGIMEN_WITH_BETA_BLOCKER', 'END',
        'Increase dose or move to 3-drug combination plus beta-blocker; reassess at next encounter',
        'Tăng liều hoặc chuyển phối hợp 3 thuốc kèm chẹn Beta; đánh giá lại ở lần tái khám kế tiếp',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"INCREASE_DOSE_OR_THREE_DRUG_COMBINATION","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"next_medication_follow_up_stage":"ESCALATED_REGIMEN"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 264
    ),
    (
        'T6_END_ESCALATE_REGIMEN', 'END',
        'Increase dose or move to 3-drug combination; reassess at next encounter',
        'Tăng liều hoặc chuyển phối hợp 3 thuốc; đánh giá lại ở lần tái khám kế tiếp',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"INCREASE_DOSE_OR_THREE_DRUG_COMBINATION","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":true,"next_medication_follow_up_stage":"ESCALATED_REGIMEN"}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 43
    ),
    (
        'T6_LINK_RESISTANT_HYPERTENSION', 'LINK', 'Tree 14: Resistant Hypertension',
        'Cây 14: THA Kháng Trị',
        NULL::jsonb, NULL::jsonb, NULL::jsonb, NULL::jsonb,
        'resistant-hypertension', NULL::text, 44
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
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'drug-combination'
),
edge_seed (from_node_key, to_node_key, traversal_order) AS (
    VALUES
    -- Step 1
    ('T6_START_PATIENT_INFO_AND_PRESCRIPTIONS', 'T6_C_FIRST_VISIT', 1),
    ('T6_START_PATIENT_INFO_AND_PRESCRIPTIONS', 'T6_C_FOLLOW_UP_VISIT', 2),
    ('T6_C_FIRST_VISIT', 'T6_INF_DETERMINE_CONTRAINDICATIONS', 1),
    ('T6_C_FOLLOW_UP_VISIT', 'T6_INF_DETERMINE_PRIOR_PRESCRIPTION_STATUS', 1),
    ('T6_INF_DETERMINE_PRIOR_PRESCRIPTION_STATUS', 'T6_C_HAS_PRIOR_PRESCRIPTION', 1),
    ('T6_INF_DETERMINE_PRIOR_PRESCRIPTION_STATUS', 'T6_C_NO_PRIOR_PRESCRIPTION', 2),
    ('T6_C_NO_PRIOR_PRESCRIPTION', 'T6_INF_DETERMINE_CONTRAINDICATIONS', 1),
    ('T6_C_HAS_PRIOR_PRESCRIPTION', 'T6_ACTION_COMPARE_WITH_CURRENT_PRESCRIPTION', 1),
    ('T6_ACTION_COMPARE_WITH_CURRENT_PRESCRIPTION', 'T6_C_DOSAGE_ADJUSTMENT_REQUESTED', 1),
    ('T6_ACTION_COMPARE_WITH_CURRENT_PRESCRIPTION', 'T6_C_NO_DOSAGE_ADJUSTMENT_REQUESTED', 2),
    ('T6_C_DOSAGE_ADJUSTMENT_REQUESTED', 'T6_ACTION_ADJUST_REGIMEN', 1),
    ('T6_C_NO_DOSAGE_ADJUSTMENT_REQUESTED', 'T6_ACTION_MAINTAIN_REGIMEN_NO_ADJUSTMENT', 1),
    ('T6_ACTION_ADJUST_REGIMEN', 'T6_INF_DETERMINE_CONTRAINDICATIONS', 1),
    ('T6_ACTION_MAINTAIN_REGIMEN_NO_ADJUSTMENT', 'T6_INF_DETERMINE_CONTRAINDICATIONS', 1),
    -- Step 2 -> Step 3 (duplicate-drug-class check folded into T6_INF_DETERMINE_CONTRAINDICATIONS)
    ('T6_INF_DETERMINE_CONTRAINDICATIONS', 'T6_C_HAS_DUPLICATE_DRUG_CLASS', 1),
    ('T6_INF_DETERMINE_CONTRAINDICATIONS', 'T6_C_NO_DUPLICATE_DRUG_CLASS', 2),
    ('T6_C_HAS_DUPLICATE_DRUG_CLASS', 'T6_C_DUPLICATE_IS_RAS_INHIBITOR', 1),
    ('T6_C_HAS_DUPLICATE_DRUG_CLASS', 'T6_C_DUPLICATE_NOT_RAS_INHIBITOR', 2),
    ('T6_C_NO_DUPLICATE_DRUG_CLASS', 'T6_ACTION_MAINTAIN_REGIMEN_NO_DUPLICATE', 1),
    ('T6_C_DUPLICATE_IS_RAS_INHIBITOR', 'T6_ACTION_KEEP_ONE_OR_REMOVE_BOTH', 1),
    ('T6_C_DUPLICATE_NOT_RAS_INHIBITOR', 'T6_ACTION_KEEP_ONE_DRUG', 1),
    -- Step 3 -> Step 4 (3 entry points converge; each offers both encounter-type siblings)
    ('T6_ACTION_KEEP_ONE_OR_REMOVE_BOTH', 'T6_C_IS_FIRST_VISIT_FOR_REGIMEN', 1),
    ('T6_ACTION_KEEP_ONE_OR_REMOVE_BOTH', 'T6_C_IS_FOLLOW_UP_FOR_REGIMEN', 2),
    ('T6_ACTION_KEEP_ONE_DRUG', 'T6_C_IS_FIRST_VISIT_FOR_REGIMEN', 1),
    ('T6_ACTION_KEEP_ONE_DRUG', 'T6_C_IS_FOLLOW_UP_FOR_REGIMEN', 2),
    ('T6_ACTION_MAINTAIN_REGIMEN_NO_DUPLICATE', 'T6_C_IS_FIRST_VISIT_FOR_REGIMEN', 1),
    ('T6_ACTION_MAINTAIN_REGIMEN_NO_DUPLICATE', 'T6_C_IS_FOLLOW_UP_FOR_REGIMEN', 2),
    -- Step 4: fresh-therapy initiation (Nhánh A / Nhánh B)
    ('T6_C_IS_FIRST_VISIT_FOR_REGIMEN', 'T6_C_SPECIAL_POPULATION', 1),
    ('T6_C_IS_FIRST_VISIT_FOR_REGIMEN', 'T6_C_NOT_SPECIAL_POPULATION', 2),
    ('T6_C_SPECIAL_POPULATION', 'T6_INF_INITIATE_MONOTHERAPY', 1),
    ('T6_INF_INITIATE_MONOTHERAPY', 'T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_MONOTHERAPY', 1),
    ('T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_MONOTHERAPY', 'T6_C_HAS_SPECIFIC_CLINICAL_SITUATION_MONOTHERAPY', 1),
    ('T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_MONOTHERAPY', 'T6_C_NO_SPECIFIC_CLINICAL_SITUATION_MONOTHERAPY', 2),
    ('T6_C_HAS_SPECIFIC_CLINICAL_SITUATION_MONOTHERAPY', 'T6_INF_MONOTHERAPY_ADD_BETA_BLOCKER', 1),
    ('T6_INF_MONOTHERAPY_ADD_BETA_BLOCKER', 'T6_END_INITIAL_MONOTHERAPY_WITH_BETA_BLOCKER', 1),
    ('T6_C_NO_SPECIFIC_CLINICAL_SITUATION_MONOTHERAPY', 'T6_END_INITIAL_MONOTHERAPY', 1),
    ('T6_C_NOT_SPECIAL_POPULATION', 'T6_INF_INITIATE_TWO_DRUG_LOW_DOSE', 1),
    ('T6_INF_INITIATE_TWO_DRUG_LOW_DOSE', 'T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS', 1),
    ('T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS', 'T6_C_HAS_SPECIFIC_CLINICAL_SITUATION', 1),
    ('T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS', 'T6_C_NO_SPECIFIC_CLINICAL_SITUATION', 2),
    ('T6_C_HAS_SPECIFIC_CLINICAL_SITUATION', 'T6_INF_ADD_BETA_BLOCKER', 1),
    ('T6_INF_ADD_BETA_BLOCKER', 'T6_END_INITIAL_TWO_DRUG_WITH_BETA_BLOCKER', 1),
    ('T6_C_NO_SPECIFIC_CLINICAL_SITUATION', 'T6_END_INITIAL_TWO_DRUG', 1),
    -- Step 4: follow-up target check and escalation
    ('T6_C_IS_FOLLOW_UP_FOR_REGIMEN', 'T6_C_TARGET_ACHIEVED', 1),
    ('T6_C_IS_FOLLOW_UP_FOR_REGIMEN', 'T6_C_TARGET_NOT_ACHIEVED', 2),
    ('T6_C_TARGET_ACHIEVED', 'T6_END_MAINTAIN_AND_MONITOR', 1),
    ('T6_C_TARGET_NOT_ACHIEVED', 'T6_C_FOLLOWUP_INITIAL_STAGE', 1),
    ('T6_C_TARGET_NOT_ACHIEVED', 'T6_C_FOLLOWUP_ESCALATED_STAGE', 2),
    ('T6_C_FOLLOWUP_INITIAL_STAGE', 'T6_INF_DETERMINE_PRIOR_REGIMEN_INTENSITY', 1),
    ('T6_INF_DETERMINE_PRIOR_REGIMEN_INTENSITY', 'T6_C_WAS_ON_MONOTHERAPY', 1),
    ('T6_INF_DETERMINE_PRIOR_REGIMEN_INTENSITY', 'T6_C_WAS_NOT_ON_MONOTHERAPY', 2),
    ('T6_C_WAS_ON_MONOTHERAPY', 'T6_INF_INITIATE_TWO_DRUG_LOW_DOSE', 1),
    ('T6_C_WAS_NOT_ON_MONOTHERAPY', 'T6_INF_ESCALATE_TO_FULL_DOSE_OR_THREE_DRUG', 1),
    ('T6_INF_ESCALATE_TO_FULL_DOSE_OR_THREE_DRUG', 'T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_ESCALATION', 1),
    ('T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_ESCALATION', 'T6_C_HAS_SPECIFIC_CLINICAL_SITUATION_ESCALATION', 1),
    ('T6_INF_DETERMINE_SPECIFIC_CLINICAL_FLAGS_ESCALATION', 'T6_C_NO_SPECIFIC_CLINICAL_SITUATION_ESCALATION', 2),
    ('T6_C_HAS_SPECIFIC_CLINICAL_SITUATION_ESCALATION', 'T6_INF_ESCALATE_ADD_BETA_BLOCKER', 1),
    ('T6_INF_ESCALATE_ADD_BETA_BLOCKER', 'T6_END_ESCALATE_REGIMEN_WITH_BETA_BLOCKER', 1),
    ('T6_C_NO_SPECIFIC_CLINICAL_SITUATION_ESCALATION', 'T6_END_ESCALATE_REGIMEN', 1),
    ('T6_C_FOLLOWUP_ESCALATED_STAGE', 'T6_LINK_RESISTANT_HYPERTENSION', 1)
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
    SELECT id AS tree_id FROM public.decision_trees WHERE tree_key = 'drug-combination'
),
reference_seed (
    node_key, source_title, section_path, locator, locator_detail,
    printed_page_numbers, pdf_page_numbers, reference_note, reference_order
) AS (
    VALUES
    ('T6_START_PATIENT_INFO_AND_PRESCRIPTIONS',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.4", "title": "Điều trị Tăng huyết áp bằng thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Entry point of the drug-combination tree.',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Điểm vào của quy trình phối hợp thuốc.', 1),
    ('T6_INF_DETERMINE_CONTRAINDICATIONS',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 11. Chống chỉ định của các nhóm thuốc điều trị tăng huyết áp chính (1)',
     'Carries forward the pre-computed contraindicated-drug-class map; full table on the GLOBAL reference node.',
     ARRAY[23]::smallint[], ARRAY[25]::smallint[],
     'Chống chỉ định bắt buộc/tương đối theo nhóm thuốc.', 1),
    ('T6_GLOBAL_CONTRAINDICATION_REFERENCE_TABLE',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 11. Chống chỉ định của các nhóm thuốc điều trị tăng huyết áp chính (1)',
     'Full absolute/relative contraindication table by drug class, including direct renin inhibitor/vasodilator.',
     ARRAY[23]::smallint[], ARRAY[25]::smallint[],
     'Bảng chống chỉ định đầy đủ theo nhóm thuốc.', 1),
    ('T6_INF_DETERMINE_CONTRAINDICATIONS',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.4", "title": "Điều trị Tăng huyết áp bằng thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Dual RAS-inhibitor blockade is not recommended (Class III, Level A).',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Việc phối hợp hai nhóm thuốc ức chế hệ renin-angiotensin không được khuyến cáo.', 2),
    ('T6_ACTION_KEEP_ONE_OR_REMOVE_BOTH',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.4", "title": "Điều trị Tăng huyết áp bằng thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Dual RAS-inhibitor blockade is not recommended (Class III, Level A).',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Việc phối hợp hai nhóm thuốc ức chế hệ renin-angiotensin không được khuyến cáo.', 1),
    ('T6_C_SPECIAL_POPULATION',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Monotherapy eligibility, matching T4_C_MONOTHERAPY_ELIGIBILITY/T5_C_MONOTHERAPY_ELIGIBILITY''s established condition exactly so Tree 6 never contradicts the tier Trees 4/5 already decided.',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Đơn trị có thể xem xét khi HABTC không đạt mục tiêu sau thay đổi lối sống, hoặc tuổi >= 80, hoặc hội chứng lão hóa.', 1),
    ('T6_INF_INITIATE_MONOTHERAPY',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Monotherapy initiation for special populations; class menu (A/B/C/D, B requires indication) matches T4_ACTION_CONSIDER_MONOTHERAPY/T5_ACTION_CONSIDER_MONOTHERAPY_ONE_PILL exactly.',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Điều trị thuốc khởi đầu bằng 1 thuốc (A, B, C, hoặc D; B cần có chỉ định).', 1),
    ('T6_INF_INITIATE_TWO_DRUG_LOW_DOSE',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Optimal initial therapy: 2 drugs preferring A+C or A+D, fixed-dose combination at low dose (half the usual dose).',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Khuyến cáo điều trị ban đầu tối ưu với 2 thuốc ưu tiên A+C hoặc D, liều thấp (1/2 liều thông thường).', 1),
    ('T6_C_HAS_SPECIFIC_CLINICAL_SITUATION',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Beta-blocker recommended in combination with any other main drug class for specific clinical situations (Class I).',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Chẹn Beta được khuyến cáo phối hợp khi có tình huống lâm sàng đặc hiệu: đau thắt ngực, sau NMCT, suy tim hoặc kiểm soát nhịp tim.', 1),
    ('T6_C_HAS_SPECIFIC_CLINICAL_SITUATION_MONOTHERAPY',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'The specific-clinical-situation/beta-blocker check must gate every regimen tier (1, 2, or 3 drugs), not only the 2-drug tier, before the final regimen is given to the patient.',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Chẹn Beta được khuyến cáo phối hợp khi có tình huống lâm sàng đặc hiệu, áp dụng cho mọi bậc điều trị (1, 2, hoặc 3 thuốc).', 1),
    ('T6_C_HAS_SPECIFIC_CLINICAL_SITUATION_ESCALATION',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'The specific-clinical-situation/beta-blocker check must gate every regimen tier (1, 2, or 3 drugs), not only the 2-drug tier, before the final regimen is given to the patient.',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Chẹn Beta được khuyến cáo phối hợp khi có tình huống lâm sàng đặc hiệu, áp dụng cho mọi bậc điều trị (1, 2, hoặc 3 thuốc).', 1),
    ('T6_C_TARGET_ACHIEVED',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Dynamic BP-target comparison, mirrors T3/T4/T5''s established mechanism.',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Nếu không đạt HA mục tiêu trong vòng 1 tháng, tăng liều hoặc chuyển phối hợp 3 thuốc.', 1),
    ('T6_INF_ESCALATE_TO_FULL_DOSE_OR_THREE_DRUG',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.5", "title": "Chiến lược điều trị phối hợp thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'If BP is not controlled with 2 low-dose drugs, increase to full dose or add a third drug (early fixed-dose triple combination A+C+D).',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Nếu HA không kiểm soát có thể tăng liều hoặc phối hợp 3 thuốc cố định liều sớm A+C+D.', 1),
    ('T6_LINK_RESISTANT_HYPERTENSION',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.6.1", "title": "Tăng huyết áp kháng trị"}]'::jsonb,
     'Mục 3.6.1. Tăng huyết áp kháng trị',
     'Resistant hypertension: BP not controlled despite optimal 3-drug combination including a diuretic.',
     ARRAY[24]::smallint[], ARRAY[26]::smallint[],
     'THA kháng trị: không kiểm soát được HA dù đã tối ưu phối hợp 3 thuốc bao gồm lợi tiểu.', 1)
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
