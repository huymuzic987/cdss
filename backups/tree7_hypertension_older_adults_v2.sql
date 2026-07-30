-- CDSS decision-tree seed script
-- Tree 7: THA Người cao tuổi (Hypertension in Older Adults)
-- Source: Bảng 17, Hình 6 (Khuyến cáo THA VNHA 2022)
-- Format: v2 - gen_random_uuid(), WHERE NOT EXISTS guards, safe to re-run
--
-- Node map:
--   T7_START           START      - Entry from Tree 3
--   T7_A_CLASSIFY      INFERENCE  - Classify elderly vs very elderly
--   T7_C_AGE_70_79     CONDITION  - Age 70-79
--   T7_C_AGE_80_PLUS   CONDITION  - Age >= 80 (very elderly)
--   T7_I_DC_70_79      INFERENCE  - Prescribe D+C (thiazide-like priority) for 70-79
--   T7_LINK_ESSENTIAL  LINK       - Tree 4: Essential Treatment Strategy
--   T7_LINK_OPTIMAL    LINK       - Tree 5: Optimal Treatment Strategy
--   T7_G_DRUGS         GLOBAL     - Drug classification legend
--
-- Edge flow:
--   START → CLASSIFY
--   CLASSIFY → C_AGE_70_79 (1), C_AGE_80_PLUS (2)
--   C_AGE_70_79 → I_DC_70_79
--   I_DC_70_79  → LINK_ESSENTIAL (1), LINK_OPTIMAL (2)
--   C_AGE_80_PLUS → LINK_ESSENTIAL (1), LINK_OPTIMAL (2)

BEGIN;

-- ── decision_trees ────────────────────────────────────────────────────────────
INSERT INTO public.decision_trees (id, tree_key, name_en, name_vi, created_at, updated_at)
VALUES (gen_random_uuid(), 'hypertension-older-adults', 'Hypertension in Older Adults', 'Cây 7: THA Người cao tuổi', NOW(), NOW())
ON CONFLICT (tree_key) DO NOTHING;

-- ── decision_nodes ────────────────────────────────────────────────────────────

-- START
INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type, text_en, text_vi,
   condition_definition, context_patch, action_payload, global_config,
   link_target_tree_key, link_target_node_key, display_order, created_at, updated_at)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults'),
  'T7_START', 'START'::node_type,
  'Tree 3: Blood Pressure Thresholds and Targets',
  'Cây 3 Ngưỡng huyết áp và đích điều trị',
  NULL, NULL, NULL, NULL, NULL, NULL, 1, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
    AND node_key = 'T7_START');

-- INFERENCE: Classify
INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type, text_en, text_vi,
   condition_definition, context_patch, action_payload, global_config,
   link_target_tree_key, link_target_node_key, display_order, created_at, updated_at)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults'),
  'T7_A_CLASSIFY', 'INFERENCE'::node_type,
  'Classify hypertension in elderly and very elderly patients',
  'Phân loại THA bệnh nhân cao tuổi và bệnh nhân rất già',
  NULL, NULL, '{"action_type": "CLASSIFY_ELDERLY_PATIENT"}'::jsonb, NULL, NULL, NULL,
  2, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
    AND node_key = 'T7_A_CLASSIFY');

-- CONDITION: Age 70-79
INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type, text_en, text_vi,
   condition_definition, context_patch, action_payload, global_config,
   link_target_tree_key, link_target_node_key, display_order, created_at, updated_at)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults'),
  'T7_C_AGE_70_79', 'CONDITION'::node_type,
  'Patient age is in range 70-79',
  'Tuổi bệnh nhân thuộc khoảng 70-79',
  '{"all": [{"op": "gte", "path": "input.age", "value": 70}, {"op": "lte", "path": "input.age", "value": 79}]}'::jsonb,
  NULL, NULL, NULL, NULL, NULL, 3, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
    AND node_key = 'T7_C_AGE_70_79');

-- CONDITION: Age >= 80
INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type, text_en, text_vi,
   condition_definition, context_patch, action_payload, global_config,
   link_target_tree_key, link_target_node_key, display_order, created_at, updated_at)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults'),
  'T7_C_AGE_80_PLUS', 'CONDITION'::node_type,
  'Patient age >= 80 (very elderly)',
  'Tuổi bệnh nhân >=80',
  '{"op": "gte", "path": "input.age", "value": 80}'::jsonb,
  NULL, NULL, NULL, NULL, NULL, 4, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
    AND node_key = 'T7_C_AGE_80_PLUS');

-- INFERENCE: Prescribe D+C for age 70-79
INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type, text_en, text_vi,
   condition_definition, context_patch, action_payload, global_config,
   link_target_tree_key, link_target_node_key, display_order, created_at, updated_at)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults'),
  'T7_I_DC_70_79', 'INFERENCE'::node_type,
  'Prescribe D + C combination, prioritize thiazide-like D',
  'Chỉ định điều trị thuốc D + C, Ưu tiên D thiazide-like',
  NULL, NULL,
  '{"action_type": "PRESCRIBE_D_C_THIAZIDE_PRIORITY", "drugs": ["D_THIAZIDE_LIKE", "C"]}'::jsonb,
  NULL, NULL, NULL, 5, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
    AND node_key = 'T7_I_DC_70_79');

-- LINK: Essential Treatment Strategy (Tree 4)
INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type, text_en, text_vi,
   condition_definition, context_patch, action_payload, global_config,
   link_target_tree_key, link_target_node_key, display_order, created_at, updated_at)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults'),
  'T7_LINK_ESSENTIAL', 'LINK'::node_type,
  'Tree 4: Essential Treatment Strategy',
  'Cây 4: Chiến lược điều trị thiết yếu',
  NULL, NULL, NULL, NULL, 'essential-treatment-strategy', NULL,
  6, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
    AND node_key = 'T7_LINK_ESSENTIAL');

-- LINK: Optimal Treatment Strategy (Tree 5)
INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type, text_en, text_vi,
   condition_definition, context_patch, action_payload, global_config,
   link_target_tree_key, link_target_node_key, display_order, created_at, updated_at)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults'),
  'T7_LINK_OPTIMAL', 'LINK'::node_type,
  'Tree 5: Optimal Treatment Strategy',
  'Cây 5: Chiến lược điều trị tối ưu',
  NULL, NULL, NULL, NULL, 'optimal-treatment-strategy', NULL,
  7, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
    AND node_key = 'T7_LINK_OPTIMAL');

-- GLOBAL: Drug classification legend
INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type, text_en, text_vi,
   condition_definition, context_patch, action_payload, global_config,
   link_target_tree_key, link_target_node_key, display_order, created_at, updated_at)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults'),
  'T7_G_DRUGS', 'GLOBAL'::node_type,
  'First-line drugs: D (thiazide-like) + C. Add A or MRA when necessary',
  'Thuốc chỉ định hàng đầu: D (thiazide-like) + C. Thêm A hoặc MRA khi cần',
  NULL, NULL, NULL,
  '{"drug_classes": {"A": {"label": "Ức chế hệ RAS", "subtypes": ["UCMC: Ức chế men chuyển", "CTTA: chẹn thụ thể angiotensin II", "ARNI: chẹn thụ thể Angiotensine-neprisyline"]}, "B": {"label": "Chẹn Beta", "subtypes": ["CB"]}, "C": {"label": "Chẹn kênh Canxi", "subtypes": ["CKCa"]}, "D": {"label": "Lợi tiểu", "subtypes": ["LT"]}, "MRA": {"label": "Thuốc đối kháng thụ thể mineral coticoid"}, "SGLT2i": {"label": "dapagliflozin / empagliflozin"}}}'::jsonb,
  NULL, NULL, 8, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
    AND node_key = 'T7_G_DRUGS');

-- ── decision_edges ────────────────────────────────────────────────────────────

-- START → CLASSIFY
INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_START'),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_A_CLASSIFY'),
  1
WHERE NOT EXISTS (SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_START')
    AND to_node_id   = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_A_CLASSIFY')
    AND traversal_order = 1);

-- CLASSIFY → C_AGE_70_79 (1)
INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_A_CLASSIFY'),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_70_79'),
  1
WHERE NOT EXISTS (SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_A_CLASSIFY')
    AND to_node_id   = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_70_79')
    AND traversal_order = 1);

-- CLASSIFY → C_AGE_80_PLUS (2)
INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_A_CLASSIFY'),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_80_PLUS'),
  2
WHERE NOT EXISTS (SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_A_CLASSIFY')
    AND to_node_id   = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_80_PLUS')
    AND traversal_order = 2);

-- C_AGE_70_79 → I_DC_70_79
INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_70_79'),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_I_DC_70_79'),
  1
WHERE NOT EXISTS (SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_70_79')
    AND to_node_id   = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_I_DC_70_79')
    AND traversal_order = 1);

-- I_DC_70_79 → LINK_ESSENTIAL (1)
INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_I_DC_70_79'),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_I_DC_70_79')
    AND to_node_id   = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_LINK_ESSENTIAL')
    AND traversal_order = 1);

-- I_DC_70_79 → LINK_OPTIMAL (2)
INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_I_DC_70_79'),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_I_DC_70_79')
    AND to_node_id   = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_LINK_OPTIMAL')
    AND traversal_order = 2);

-- C_AGE_80_PLUS → LINK_ESSENTIAL (1)
INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_80_PLUS'),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_80_PLUS')
    AND to_node_id   = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_LINK_ESSENTIAL')
    AND traversal_order = 1);

-- C_AGE_80_PLUS → LINK_OPTIMAL (2)
INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_80_PLUS'),
  (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_C_AGE_80_PLUS')
    AND to_node_id   = (SELECT id FROM public.decision_nodes WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults') AND node_key = 'T7_LINK_OPTIMAL')
    AND traversal_order = 2);

-- ── node_source_references ────────────────────────────────────────────────────
INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
     AND node_key = nk),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Các trường hợp tăng huyết áp đặc biệt", "3.6.3. Tăng huyết áp ở người cao tuổi"]'::jsonb,
  '3.6.3. Tăng huyết áp ở người cao tuổi',
  NULL, '{31}'::integer[], '{33}'::integer[], NULL, 1
FROM (VALUES
  ('T7_START'), ('T7_A_CLASSIFY'), ('T7_C_AGE_70_79'), ('T7_C_AGE_80_PLUS'),
  ('T7_I_DC_70_79'), ('T7_LINK_ESSENTIAL'), ('T7_LINK_OPTIMAL'), ('T7_G_DRUGS')
) AS nodes(nk)
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-older-adults')
      AND node_key = nk)
    AND reference_order = 1
);

COMMIT;
