--
-- CDSS decision-tree insert script
-- Tree: "Cây 8: THA + Đái tháo đường týp 2 - Minh"
-- Source: Bảng 18, Bảng 2, Bảng 6, Bảng 7, Hình 5
--
-- This script inserts one decision tree and all its nodes/edges/references
-- into the existing cdss schema (decision_trees, decision_nodes,
-- decision_edges, node_source_references). It assumes those tables and the
-- node_type enum already exist (see cdss_prod_20260703.sql).
--
-- Node type mapping used (per legend colors in the source flowchart):
--   green  (Start Node)          -> START
--   yellow (Condition Check)     -> CONDITION
--   blue   (Trigger/Input Node)  -> INFERENCE (applies a context_patch)
--   pink   (Link Node)           -> LINK
--   gray   (glossary/legend box) -> GLOBAL (global_config)
--
-- Safe to run against an empty/staging database. Wrap in a transaction.
--

BEGIN;

-- ============================================================
-- 1. Tree
-- ============================================================

INSERT INTO public.decision_trees
    ("id", "tree_key", "name_en", "name_vi", "created_at", "updated_at")
VALUES
    ('11111111-1111-4111-8111-111111111108',
     'cay_8_tha_dtd_typ_2',
     'Tree 8: Hypertension + Type 2 Diabetes - Minh',
     'Cây 8: THA + Đái tháo đường týp 2 - Minh',
     '2026-07-03T00:00:00+00:00',
     '2026-07-03T00:00:00+00:00');

-- ============================================================
-- 2. Nodes
-- ============================================================

-- START: entry point, continues on from Tree 3 (BP threshold / target)
INSERT INTO public.decision_nodes
    ("id", "tree_id", "node_key", "node_type", "text_en", "text_vi",
     "condition_definition", "context_patch", "action_payload", "global_config",
     "link_target_tree_key", "link_target_node_key", "display_order",
     "created_at", "updated_at")
VALUES
('22222222-2222-4222-8222-000000000001',
 '11111111-1111-4111-8111-111111111108',
 'start',
 'START',
 'Tree 3: Blood pressure threshold and treatment target',
 'Cây 3: Ngưỡng huyết áp và đích điều trị',
 NULL, NULL, NULL, NULL, NULL, NULL, 0,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- CONDITION: at/below target
('22222222-2222-4222-8222-000000000002',
 '11111111-1111-4111-8111-111111111108',
 'cond_below_target',
 'CONDITION',
 'SBP < 130 mmHg and DBP < 85 mmHg',
 'HATT < 130 mmHg và HATTr < 85 mmHg',
 '{"all":[{"field":"HATT","op":"lt","value":130},{"field":"HATTr","op":"lt","value":85}]}'::jsonb,
 NULL, NULL, NULL, NULL, NULL, 1,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- CONDITION: above target
('22222222-2222-4222-8222-000000000003',
 '11111111-1111-4111-8111-111111111108',
 'cond_above_target',
 'CONDITION',
 'SBP >= 130 mmHg and DBP >= 85 mmHg',
 'HATT >= 130 mmHg và HATTr >= 85 mmHg',
 '{"all":[{"field":"HATT","op":"gte","value":130},{"field":"HATTr","op":"gte","value":85}]}'::jsonb,
 NULL, NULL, NULL, NULL, NULL, 2,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- INFERENCE: regimen options (A+C / A+D combinations)
('22222222-2222-4222-8222-000000000004',
 '11111111-1111-4111-8111-111111111108',
 'regimen_a_c_ucmc_ckca',
 'INFERENCE',
 'A + C (ACEI + CCB)',
 'A + C (ƯCMC + CKCa)',
 NULL,
 '{"regimen":"A+C","component_A":"ƯCMC (ức chế men chuyển)","component_C":"CKCa (chẹn kênh Canxi)"}'::jsonb,
 NULL, NULL, NULL, NULL, 1,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

('22222222-2222-4222-8222-000000000005',
 '11111111-1111-4111-8111-111111111108',
 'regimen_a_c_ctta_ckca',
 'INFERENCE',
 'A + C (ARB + CCB)',
 'A + C (CTTA + CKCa)',
 NULL,
 '{"regimen":"A+C","component_A":"CTTA (chẹn thụ thể angiotensin II)","component_C":"CKCa (chẹn kênh Canxi)"}'::jsonb,
 NULL, NULL, NULL, NULL, 2,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

('22222222-2222-4222-8222-000000000006',
 '11111111-1111-4111-8111-111111111108',
 'regimen_a_d_ucmc_lt',
 'INFERENCE',
 'A + D (ACEI + thiazide-like diuretic)',
 'A + D (ƯCMC + LT Thiazide-like)',
 NULL,
 '{"regimen":"A+D","component_A":"ƯCMC (ức chế men chuyển)","component_D":"LT Thiazide-like (lợi tiểu)"}'::jsonb,
 NULL, NULL, NULL, NULL, 3,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

('22222222-2222-4222-8222-000000000007',
 '11111111-1111-4111-8111-111111111108',
 'regimen_a_d_ctta_lt',
 'INFERENCE',
 'A + D (ARB + thiazide-like diuretic)',
 'A + D (CTTA + LT Thiazide-like)',
 NULL,
 '{"regimen":"A+D","component_A":"CTTA (chẹn thụ thể angiotensin II)","component_D":"LT Thiazide-like (lợi tiểu)"}'::jsonb,
 NULL, NULL, NULL, NULL, 4,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- CONDITION: cardiovascular risk factor present
('22222222-2222-4222-8222-000000000008',
 '11111111-1111-4111-8111-111111111108',
 'cond_has_cv_risk',
 'CONDITION',
 'Has at least one cardiovascular risk factor',
 'Có 1 trong các yếu tố nguy cơ tim mạch: Bệnh thận mạn xơ vữa, Bệnh mạch vành, Đột quỵ, Bệnh tim mạch, Nguy cơ tim mạch cao, Tổn thương cơ quan đích',
 '{"any":[{"field":"benh_than_man_xo_vua","op":"eq","value":true},{"field":"benh_mach_vanh","op":"eq","value":true},{"field":"dot_quy","op":"eq","value":true},{"field":"benh_tim_mach","op":"eq","value":true},{"field":"nguy_co_tim_mach_cao","op":"eq","value":true},{"field":"ton_thuong_co_quan_dich","op":"eq","value":true}]}'::jsonb,
 NULL, NULL, NULL, NULL, NULL, 5,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- CONDITION: no cardiovascular risk factor
('22222222-2222-4222-8222-000000000009',
 '11111111-1111-4111-8111-111111111108',
 'cond_no_cv_risk',
 'CONDITION',
 'No cardiovascular risk factors',
 'Không có các yếu tố nguy cơ tim mạch: Bệnh thận mạn xơ vữa, Bệnh mạch vành, Đột quỵ, Bệnh tim mạch, Nguy cơ tim mạch cao, Tổn thương cơ quan đích',
 '{"all":[{"field":"benh_than_man_xo_vua","op":"eq","value":false},{"field":"benh_mach_vanh","op":"eq","value":false},{"field":"dot_quy","op":"eq","value":false},{"field":"benh_tim_mach","op":"eq","value":false},{"field":"nguy_co_tim_mach_cao","op":"eq","value":false},{"field":"ton_thuong_co_quan_dich","op":"eq","value":false}]}'::jsonb,
 NULL, NULL, NULL, NULL, NULL, 6,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- INFERENCE: add SGLT2i or GLP-1RA
('22222222-2222-4222-8222-000000000010',
 '11111111-1111-4111-8111-111111111108',
 'action_add_sglt2i_glp1ra',
 'INFERENCE',
 'Add SGLT2i or GLP-1RA',
 'Bổ sung SGLT2i hoặc GLP-1RA',
 NULL,
 '{"action":"bo_sung_thuoc","options":["SGLT2i (dapagliflozin/empagliflozin)","GLP-1RA"]}'::jsonb,
 NULL, NULL, NULL, NULL, 7,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- INFERENCE: maintain regimen
('22222222-2222-4222-8222-000000000011',
 '11111111-1111-4111-8111-111111111108',
 'action_maintain_regimen',
 'INFERENCE',
 'Maintain current regimen',
 'Duy trì phác đồ',
 NULL,
 '{"action":"duy_tri_phac_do"}'::jsonb,
 NULL, NULL, NULL, NULL, 8,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- LINK: from "below target" branch
('22222222-2222-4222-8222-000000000012',
 '11111111-1111-4111-8111-111111111108',
 'link_to_cay4_cay5_a',
 'LINK',
 'Tree 4: Essential treatment strategy, or Tree 5: Optimal treatment strategy',
 'Cây 4: Chiến lược điều trị thiết yếu hoặc Cây 5: Chiến lược điều trị tối ưu',
 NULL, NULL, NULL, NULL,
 'cay_4_chien_luoc_dieu_tri_thiet_yeu',
 NULL, 9,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- LINK: from "above target" branch (both sub-paths converge here)
('22222222-2222-4222-8222-000000000013',
 '11111111-1111-4111-8111-111111111108',
 'link_to_cay4_cay5_b',
 'LINK',
 'Tree 4: Essential treatment strategy, or Tree 5: Optimal treatment strategy',
 'Cây 4: Chiến lược điều trị thiết yếu hoặc Cây 5: Chiến lược điều trị tối ưu',
 NULL, NULL, NULL, NULL,
 'cay_4_chien_luoc_dieu_tri_thiet_yeu',
 NULL, 10,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00'),

-- GLOBAL: glossary/abbreviation legend panel (excluded from traversal edges)
('22222222-2222-4222-8222-000000000014',
 '11111111-1111-4111-8111-111111111108',
 'global_chu_giai_viet_tat',
 'GLOBAL',
 'Abbreviation glossary',
 'Chú giải viết tắt',
 NULL, NULL, NULL,
 '{"1_A_uc_che_he_RAS":{"label":"A: ức chế hệ RAS","UCMC":"ức chế men chuyển","CTTA":"chẹn thụ thể angiotensin II","ARNI":"chẹn thụ thể Angiotensine-neprisyline"},"4_B_chen_Beta":{"label":"B: chẹn Beta","CB":"chẹn Beta"},"3_C_chen_kenh_Canxi":{"label":"C: chẹn kênh Canxi","CKCa":"chẹn kênh Canxi"},"2_D_loi_tieu":{"label":"D: lợi tiểu","LT":"lợi tiểu"},"6_MRA":{"label":"MRA: thuốc đối kháng thụ thể mineralocorticoid"},"5_SGLT2i":{"label":"SGLT2i: dapagliflozin / empagliflozin"}}'::jsonb,
 NULL, NULL, 99,
 '2026-07-03T00:00:00+00:00', '2026-07-03T00:00:00+00:00');

-- ============================================================
-- 3. Edges
-- ============================================================

INSERT INTO public.decision_edges
    ("id", "from_node_id", "to_node_id", "traversal_order")
VALUES
-- start -> two BP-target branches
('33333333-3333-4333-8333-000000000001',
 '22222222-2222-4222-8222-000000000001', '22222222-2222-4222-8222-000000000002', 1),
('33333333-3333-4333-8333-000000000002',
 '22222222-2222-4222-8222-000000000001', '22222222-2222-4222-8222-000000000003', 2),

-- below target -> link A
('33333333-3333-4333-8333-000000000003',
 '22222222-2222-4222-8222-000000000002', '22222222-2222-4222-8222-000000000012', 1),

-- above target -> four regimen options
('33333333-3333-4333-8333-000000000004',
 '22222222-2222-4222-8222-000000000003', '22222222-2222-4222-8222-000000000004', 1),
('33333333-3333-4333-8333-000000000005',
 '22222222-2222-4222-8222-000000000003', '22222222-2222-4222-8222-000000000005', 2),
('33333333-3333-4333-8333-000000000006',
 '22222222-2222-4222-8222-000000000003', '22222222-2222-4222-8222-000000000006', 3),
('33333333-3333-4333-8333-000000000007',
 '22222222-2222-4222-8222-000000000003', '22222222-2222-4222-8222-000000000007', 4),

-- A+C options -> "has CV risk" condition
('33333333-3333-4333-8333-000000000008',
 '22222222-2222-4222-8222-000000000004', '22222222-2222-4222-8222-000000000008', 1),
('33333333-3333-4333-8333-000000000009',
 '22222222-2222-4222-8222-000000000005', '22222222-2222-4222-8222-000000000008', 1),

-- A+D options -> "no CV risk" condition
('33333333-3333-4333-8333-00000000000a',
 '22222222-2222-4222-8222-000000000006', '22222222-2222-4222-8222-000000000009', 1),
('33333333-3333-4333-8333-00000000000b',
 '22222222-2222-4222-8222-000000000007', '22222222-2222-4222-8222-000000000009', 1),

-- has CV risk -> add SGLT2i/GLP-1RA
('33333333-3333-4333-8333-00000000000c',
 '22222222-2222-4222-8222-000000000008', '22222222-2222-4222-8222-000000000010', 1),

-- no CV risk -> maintain regimen
('33333333-3333-4333-8333-00000000000d',
 '22222222-2222-4222-8222-000000000009', '22222222-2222-4222-8222-000000000011', 1),

-- both outcomes converge -> link B
('33333333-3333-4333-8333-00000000000e',
 '22222222-2222-4222-8222-000000000010', '22222222-2222-4222-8222-000000000013', 1),
('33333333-3333-4333-8333-00000000000f',
 '22222222-2222-4222-8222-000000000011', '22222222-2222-4222-8222-000000000013', 1);

-- ============================================================
-- 4. Source references
-- ============================================================

INSERT INTO public.node_source_references
    ("id", "node_id", "source_title", "section_path", "locator", "locator_detail",
     "printed_page_numbers", "pdf_page_numbers", "reference_note", "reference_order")
VALUES
('44444444-4444-4444-8444-000000000001',
 '22222222-2222-4222-8222-000000000001',
 'Hướng dẫn điều trị THA + Đái tháo đường týp 2',
 '["Bảng 18", "Bảng 2", "Bảng 6", "Bảng 7", "Hình 5"]'::jsonb,
 'Cây 8', 'Cây 8: THA + Đái tháo đường týp 2 - Minh',
 NULL, NULL,
 'Nguồn tổng hợp cho toàn bộ Cây 8, theo sơ đồ gốc (Bảng 18, Bảng 2, Bảng 6, Bảng 7, Hình 5).',
 0);

COMMIT;
