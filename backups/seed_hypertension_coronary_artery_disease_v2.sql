BEGIN;

INSERT INTO public.decision_trees (id, tree_key, name_en, name_vi, created_at, updated_at)
VALUES (gen_random_uuid(), 'hypertension-coronary-artery-disease', 'Hypertension + Coronary Artery Disease', 'Cây 9: THA + bệnh mạch vành', NOW(), NOW())
ON CONFLICT (tree_key) DO NOTHING;


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_START', 'START'::node_type,
  'Tree 3: Blood Pressure Thresholds and Targets', 'Cây 3 Ngưỡng huyết áp và đích điều trị',
  NULL, NULL,
  NULL, NULL,
  NULL, NULL,
  1, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_START'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_C_BP1', 'CONDITION'::node_type,
  '18-69 years and SBP >= 130 or DBP >= 85', '18-69 tuổi và HATT >= 130 mmHg HATTr >= 85 mmHg',
  '{"all": [{"all": [{"op": "gte", "path": "input.age", "value": 18}, {"op": "lte", "path": "input.age", "value": 69}]}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}]}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  2, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_C_BP1'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_C_BP2', 'CONDITION'::node_type,
  '>70 years and SBP >= 140 or DBP >= 90', '>70 tuổi và HATT >= 140 mmHg HATTr >= 90 mmHg',
  '{"all": [{"op": "gt", "path": "input.age", "value": 70}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 140}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 90}]}]}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  3, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_C_BP2'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_C_BP3', 'CONDITION'::node_type,
  '18-69 years and SBP < 130 and DBP < 85', '18-69 tuổi và HATT < 130 mmHg HATTr < 85 mmHg',
  '{"all": [{"op": "gte", "path": "input.age", "value": 18}, {"op": "lte", "path": "input.age", "value": 69}, {"op": "lt", "path": "input.current_clinic_sbp", "value": 130}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 85}]}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  4, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_C_BP3'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_C_BP4', 'CONDITION'::node_type,
  '>70 years and SBP < 140 and DBP < 90', '>70 tuổi và HATT < 140 mmHg HATTr < 90 mmHg',
  '{"all": [{"op": "gt", "path": "input.age", "value": 70}, {"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}]}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  5, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_C_BP4'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_C_AMI', 'CONDITION'::node_type,
  'Myocardial Infarction or Acute Coronary Syndrome', 'Nhồi máu cơ tim hoặc hội chứng vành cấp',
  '{"op": "eq", "path": "input.has_mi_acs", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  6, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_C_AMI'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_C_CCS_ANGINA', 'CONDITION'::node_type,
  'Chronic Coronary Syndrome with Angina', 'Hội chứng vành mạn có cơn đau thắt ngực',
  '{"op": "eq", "path": "input.has_ccs_angina", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  7, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_C_CCS_ANGINA'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_C_CCS_REVASC', 'CONDITION'::node_type,
  'Chronic Coronary Syndrome after Revascularization', 'Hội chứng vành mạn sau tái thông',
  '{"op": "eq", "path": "input.has_ccs_revasc", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  8, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_C_CCS_REVASC'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_C_CABG', 'CONDITION'::node_type,
  'Post CABG', 'Sau phẫu thuật bắc cầu vành CABG',
  '{"op": "eq", "path": "input.has_cabg", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  9, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_C_CABG'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_A_B_3Y', 'INFERENCE'::node_type,
  'Combine Beta-blocker for 3 years', 'Phối hợp thuốc B trong 3 năm',
  NULL, '{"regimen_modifier": "add_beta_blocker_3_years"}'::jsonb,
  '{"action_type": "BETA_BLOCKER_3_YEARS"}'::jsonb, NULL,
  NULL, NULL,
  10, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_A_B_3Y'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_A_B_OR_C', 'INFERENCE'::node_type,
  'Combine Beta-blocker or CCB', 'Phối hợp thuốc B hoặc C',
  NULL, '{"regimen_modifier": "add_beta_blocker_or_ccb"}'::jsonb,
  '{"action_type": "BETA_BLOCKER_OR_CCB"}'::jsonb, NULL,
  NULL, NULL,
  11, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_A_B_OR_C'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_A_NO_B', 'INFERENCE'::node_type,
  'No routine indication for Beta-blocker', 'Không có chỉ định thuốc B thường quy',
  NULL, '{"regimen_modifier": "no_routine_beta_blocker"}'::jsonb,
  '{"action_type": "NO_ROUTINE_BETA_BLOCKER"}'::jsonb, NULL,
  NULL, NULL,
  12, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_A_NO_B'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_A_B_EARLY', 'INFERENCE'::node_type,
  'Start Beta-blocker as early as possible', 'Bắt đầu thuốc B sớm nhất có thể',
  NULL, '{"regimen_modifier": "early_beta_blocker"}'::jsonb,
  '{"action_type": "EARLY_BETA_BLOCKER"}'::jsonb, NULL,
  NULL, NULL,
  13, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_A_B_EARLY'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_LINK_ESSENTIAL', 'LINK'::node_type,
  'Tree 4: Essential Treatment Strategy', 'Cây 4: Chiến lược điều trị thiết yếu',
  NULL, NULL,
  NULL, NULL,
  'essential-treatment-strategy', NULL,
  14, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_LINK_ESSENTIAL'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_LINK_OPTIMAL', 'LINK'::node_type,
  'Tree 5: Optimal Treatment Strategy', 'Cây 5: Chiến lược điều trị tối ưu',
  NULL, NULL,
  NULL, NULL,
  'optimal-treatment-strategy', NULL,
  15, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_LINK_OPTIMAL'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease'),
  'T9_G_DRUGS', 'GLOBAL'::node_type,
  'First-line drugs: A + B. Add C, D or MRA when necessary', 'Thuốc chỉ định hàng đầu: A + B thêm thuốc C, D hoặc MRA khi cần',
  NULL, NULL,
  NULL, '{"add_on_drugs": ["C", "D", "MRA"], "first_line_drugs": ["A", "B"]}'::jsonb,
  NULL, NULL,
  16, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
    AND node_key = 'T9_G_DRUGS'
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_3Y'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_3Y')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_3Y'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_3Y')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_EARLY'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_EARLY')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_EARLY'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_EARLY')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_OR_C'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_OR_C')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_OR_C'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_OR_C')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_NO_B'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_NO_B')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_NO_B'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_NO_B')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_AMI'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_3Y'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_AMI')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_3Y')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP1'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_AMI'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP1')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_AMI')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP1'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CCS_ANGINA'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP1')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CCS_ANGINA')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP1'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CCS_REVASC'),
  3
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP1')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CCS_REVASC')
    AND traversal_order = 3
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP1'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CABG'),
  4
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP1')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CABG')
    AND traversal_order = 4
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_AMI'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_AMI')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CCS_ANGINA'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CCS_ANGINA')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CCS_REVASC'),
  3
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CCS_REVASC')
    AND traversal_order = 3
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CABG'),
  4
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CABG')
    AND traversal_order = 4
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP3'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP3')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP3'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP3')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP4'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP4')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP4'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP4')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CABG'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_EARLY'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CABG')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_EARLY')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CCS_ANGINA'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_OR_C'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CCS_ANGINA')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_OR_C')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CCS_REVASC'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_NO_B'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CCS_REVASC')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_NO_B')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_START'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP1'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_START')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP1')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_START'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP2'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_START')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP2')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_START'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP3'),
  3
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_START')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP3')
    AND traversal_order = 3
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_START'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP4'),
  4
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_START')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP4')
    AND traversal_order = 4
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_3Y'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_3Y')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_EARLY'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_EARLY')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_B_OR_C'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_B_OR_C')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_A_NO_B'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_A_NO_B')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_AMI'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_AMI')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP1'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP1')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP2'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP2')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP3'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP3')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_BP4'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_BP4')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CABG'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CABG')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CCS_ANGINA'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CCS_ANGINA')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_C_CCS_REVASC'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_C_CCS_REVASC')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_G_DRUGS'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_G_DRUGS')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_ESSENTIAL'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_ESSENTIAL')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_LINK_OPTIMAL'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_LINK_OPTIMAL')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
     AND node_key = 'T9_START'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.2. Tu0103ng huyu1ebft u00e1p vu00e0 Bu1ec7nh mu1ea1ch vu00e0nh"]'::jsonb,
  'Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành',
  NULL,
  '{33}'::integer[],
  '{35}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-coronary-artery-disease')
      AND node_key = 'T9_START')
    AND reference_order = 1
);


COMMIT;
