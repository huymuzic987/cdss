BEGIN;

INSERT INTO public.decision_trees (id, tree_key, name_en, name_vi, created_at, updated_at)
VALUES (gen_random_uuid(), 'hypertension-heart-failure', 'Hypertension + Heart Failure', 'Cây 10: THA + suy tim', NOW(), NOW())
ON CONFLICT (tree_key) DO NOTHING;


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_START', 'START'::node_type,
  'Tree 3: Blood Pressure Thresholds and Targets', 'Cây 3 Ngưỡng huyết áp và đích điều trị',
  NULL, NULL,
  NULL, NULL,
  NULL, NULL,
  1, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_START'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_C_BP1', 'CONDITION'::node_type,
  'SBP < 130 and DBP < 85', 'HATT < 130 mmHg và HATTr < 85 mmHg',
  '{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 130}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 85}]}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  2, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_C_BP1'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_C_BP2', 'CONDITION'::node_type,
  'SBP >= 130 or DBP >= 85', 'HATT >= 130 mmHg Hoặc HATTr >= 85 mmHg',
  '{"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  3, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_C_BP2'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_A_EVAL_EF', 'INFERENCE'::node_type,
  'Evaluate ejection fraction (EF) and heart structure', 'Đánh giá phân suất tống máu(EF) và cấu trúc tim',
  NULL, NULL,
  '{"action_type": "EVALUATE_EF_AND_STRUCTURE"}'::jsonb, NULL,
  NULL, NULL,
  4, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_A_EVAL_EF'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_C_HFREF', 'CONDITION'::node_type,
  'Heart Failure with reduced EF (HFrEF)', 'Suy tim EF giảm (HFrEF)',
  '{"op": "eq", "path": "input.has_hfref", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  5, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_C_HFREF'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_C_HFMREF', 'CONDITION'::node_type,
  'Heart Failure with mildly reduced EF (HFmrEF)', 'Suy tim EF giảm nhẹ (HFmrEF)',
  '{"op": "eq", "path": "input.has_hfmref", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  6, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_C_HFMREF'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_C_HFPEF', 'CONDITION'::node_type,
  'Heart Failure with preserved EF (HFpEF)', 'Suy tim EF bảo tồn (HFpEF)',
  '{"op": "eq", "path": "input.has_hfpef", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  7, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_C_HFPEF'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_C_LVH', 'CONDITION'::node_type,
  'Left ventricular hypertrophy (LVH)', 'Phì đại thất trái (LVH)',
  '{"op": "eq", "path": "input.has_lvh", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  8, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_C_LVH'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_HFREF', 'INFERENCE'::node_type,
  'Combine A + B + D and/or Aldosterone antagonist + SGLT2i. B: (bisoprolol, carvedilol, metoprolol, nebivolol)', 'Phối hợp A + B + D và/hoặc kháng aldosterone + SGLT2i. B: (bisoprolol, carvedilol, metoprolol, nebivolol)',
  NULL, NULL,
  '{"action_type": "COMBINE_ABD_ALDO_SGLT2I"}'::jsonb, NULL,
  NULL, NULL,
  9, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_HFREF'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_HFMREF_1', 'INFERENCE'::node_type,
  'Combine D and SGLT2i and Aldosterone antagonist', 'Phối hợp D và SGLT2i và kháng Aldosterone',
  NULL, NULL,
  '{"action_type": "COMBINE_D_SGLT2I_ALDO"}'::jsonb, NULL,
  NULL, NULL,
  10, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_HFMREF_1'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_HFMREF_2', 'INFERENCE'::node_type,
  'Add A (ARNI or CTTA or UCMC)', 'Phối hợp thêm A (ARNI hoặc CTTA hoặc UCMC)',
  NULL, NULL,
  '{"action_type": "ADD_A_ARNI_CTTA_UCMC"}'::jsonb, NULL,
  NULL, NULL,
  11, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_HFMREF_2'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_HFPEF_1', 'INFERENCE'::node_type,
  'Combine D and SGLT2i and Aldosterone antagonist', 'Phối hợp D và SGLT2i và kháng Aldosterone',
  NULL, NULL,
  '{"action_type": "COMBINE_D_SGLT2I_ALDO"}'::jsonb, NULL,
  NULL, NULL,
  12, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_HFPEF_1'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_HFPEF_2', 'INFERENCE'::node_type,
  'Add A (ARNI and CTTA)', 'Phối hợp thêm A (ARNI và CTTA)',
  NULL, NULL,
  '{"action_type": "ADD_A_ARNI_CTTA"}'::jsonb, NULL,
  NULL, NULL,
  13, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_HFPEF_2'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_LVH', 'INFERENCE'::node_type,
  'Combine A + C or A + D', 'Phối hợp A + C hoặc A + D',
  NULL, NULL,
  '{"action_type": "COMBINE_AC_OR_AD"}'::jsonb, NULL,
  NULL, NULL,
  14, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_LVH'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_C_TARGET_NOT_REACHED', 'CONDITION'::node_type,
  'BP target not reached', 'HA không đạt đích điều trị',
  '{"op": "eq", "path": "input.bp_target_reached", "value": false}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  15, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_C_TARGET_NOT_REACHED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_C_TARGET_REACHED', 'CONDITION'::node_type,
  'BP target reached', 'HA đã đạt đích điều trị',
  '{"op": "eq", "path": "input.bp_target_reached", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  16, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_C_TARGET_REACHED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_ADD_CCB', 'INFERENCE'::node_type,
  'Add Dihydropyridine CCB', 'Thêm CKCa nhóm Dihydropyridine',
  NULL, NULL,
  '{"action_type": "ADD_DIHYDROPYRIDINE_CCB"}'::jsonb, NULL,
  NULL, NULL,
  17, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_ADD_CCB'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_ADJUST', 'INFERENCE'::node_type,
  'Adjust drug dosage and monitor', 'Điều chỉnh liều lượng thuốc và theo dõi',
  NULL, NULL,
  '{"action_type": "ADJUST_DOSAGE_AND_MONITOR"}'::jsonb, NULL,
  NULL, NULL,
  18, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_ADJUST'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_I_MAINTAIN', 'INFERENCE'::node_type,
  'Maintain regimen', 'Duy trì phác đồ',
  NULL, NULL,
  '{"action_type": "MAINTAIN_REGIMEN"}'::jsonb, NULL,
  NULL, NULL,
  19, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_I_MAINTAIN'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_LINK_ESSENTIAL', 'LINK'::node_type,
  'Tree 4: Essential Treatment Strategy', 'Cây 4: Chiến lược điều trị thiết yếu',
  NULL, NULL,
  NULL, NULL,
  'essential-treatment-strategy', NULL,
  20, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_LINK_ESSENTIAL'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure'),
  'T10_LINK_OPTIMAL', 'LINK'::node_type,
  'Tree 5: Optimal Treatment Strategy', 'Cây 5: Chiến lược điều trị tối ưu',
  NULL, NULL,
  NULL, NULL,
  'optimal-treatment-strategy', NULL,
  21, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
    AND node_key = 'T10_LINK_OPTIMAL'
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_A_EVAL_EF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFREF'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_A_EVAL_EF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFREF')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_A_EVAL_EF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFMREF'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_A_EVAL_EF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFMREF')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_A_EVAL_EF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFPEF'),
  3
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_A_EVAL_EF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFPEF')
    AND traversal_order = 3
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_A_EVAL_EF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_LVH'),
  4
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_A_EVAL_EF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_LVH')
    AND traversal_order = 4
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_BP1'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_BP1')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_BP1'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_BP1')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_BP2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_A_EVAL_EF'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_BP2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_A_EVAL_EF')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFMREF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFMREF_1'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFMREF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFMREF_1')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFPEF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFPEF_1'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFPEF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFPEF_1')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFREF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFREF'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFREF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFREF')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_LVH'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_LVH'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_LVH')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_LVH')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_NOT_REACHED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_ADD_CCB'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_NOT_REACHED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_ADD_CCB')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_NOT_REACHED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_ADJUST'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_NOT_REACHED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_ADJUST')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_REACHED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_MAINTAIN'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_REACHED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_MAINTAIN')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_ADD_CCB'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_ADD_CCB')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_ADD_CCB'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_ADD_CCB')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_ADJUST'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_ADJUST')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_ADJUST'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_ADJUST')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFMREF_1'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFMREF_2'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFMREF_1')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFMREF_2')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFMREF_2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_NOT_REACHED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFMREF_2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_NOT_REACHED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFMREF_2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_REACHED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFMREF_2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_REACHED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFPEF_1'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFPEF_2'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFPEF_1')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFPEF_2')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFPEF_2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_NOT_REACHED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFPEF_2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_NOT_REACHED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFPEF_2'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_REACHED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFPEF_2')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_REACHED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFREF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_NOT_REACHED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFREF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_NOT_REACHED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFREF'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_REACHED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFREF')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_REACHED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_LVH'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_NOT_REACHED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_LVH')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_NOT_REACHED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_LVH'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_REACHED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_LVH')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_REACHED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_MAINTAIN'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_LINK_ESSENTIAL'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_MAINTAIN')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_LINK_ESSENTIAL')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_MAINTAIN'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_LINK_OPTIMAL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_MAINTAIN')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_LINK_OPTIMAL')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_START'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_BP1'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_START')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_BP1')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_START'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_BP2'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_START')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_BP2')
    AND traversal_order = 2
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_A_EVAL_EF'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_A_EVAL_EF')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_BP1'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_BP1')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_BP2'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_BP2')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFMREF'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFMREF')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFPEF'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFPEF')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_HFREF'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_HFREF')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_LVH'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_LVH')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_NOT_REACHED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_NOT_REACHED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_C_TARGET_REACHED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_C_TARGET_REACHED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_ADD_CCB'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_ADD_CCB')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_ADJUST'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_ADJUST')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFMREF_1'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFMREF_1')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFMREF_2'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFMREF_2')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFPEF_1'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFPEF_1')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFPEF_2'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFPEF_2')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_HFREF'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_HFREF')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_LVH'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_LVH')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_I_MAINTAIN'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_I_MAINTAIN')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
     AND node_key = 'T10_START'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.7. Tu0103ng huyu1ebft u00e1p vu00e0 mu1ed9t su1ed1 bu1ec7nh u0111u1ed3ng mu1eafc", "3.7.3. Tu0103ng huyu1ebft u00e1p vu00e0 Suy tim"]'::jsonb,
  'Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim',
  NULL,
  '{33,34}'::integer[],
  '{35,36}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'hypertension-heart-failure')
      AND node_key = 'T10_START')
    AND reference_order = 1
);


COMMIT;
