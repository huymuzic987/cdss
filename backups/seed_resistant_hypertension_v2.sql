BEGIN;

INSERT INTO public.decision_trees (id, tree_key, name_en, name_vi, created_at, updated_at)
VALUES (gen_random_uuid(), 'resistant-hypertension', 'Resistant Hypertension', 'THA Kháng trị', NOW(), NOW())
ON CONFLICT (tree_key) DO NOTHING;


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_START', 'START'::node_type,
  'Essential Treatment Strategy Tree (Tree 4) or Optimal Treatment Strategy Tree (Tree 5)', 'Cây 4: cây chiến lược điều trị thiết yếu hoặc Cây 5: cây chiến lược điều trị tối ưu',
  NULL, NULL,
  NULL, NULL,
  NULL, NULL,
  1, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_START'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_C_LIMITED', 'CONDITION'::node_type,
  'Essential standard', 'Tiêu chuẩn thiết yếu',
  '{"op": "eq", "path": "input.facility_capability", "value": "LIMITED_RESOURCES"}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  2, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_C_LIMITED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_ESSENTIAL_TREATMENT', 'ACTION'::node_type,
  'Treat according to essential standard and enhance lifestyle changes', 'Điều trị theo tiêu chuẩn thiết yếu và Tăng cường biện pháp tđls, đặc biệt là hạn chế muối',
  NULL, NULL,
  '{"action_type": "LIFESTYLE_CHANGES", "salt_restriction": true}'::jsonb, NULL,
  NULL, NULL,
  3, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_ESSENTIAL_TREATMENT'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_CHECK_MRA', 'ACTION'::node_type,
  'Check MRA tolerance', 'Kiểm tra khả năng dung nạp MRA',
  NULL, NULL,
  '{"action_type": "CHECK_MRA"}'::jsonb, NULL,
  NULL, NULL,
  4, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_CHECK_MRA'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_C_MRA_TOLERATED', 'CONDITION'::node_type,
  'Tolerates MRA', 'Có khả năng dung nạp MRA',
  '{"op": "eq", "path": "input.tolerates_mra", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  5, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_C_MRA_TOLERATED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_ADD_MRA', 'ACTION'::node_type,
  'Combine A + C + D and MRA', 'Phối hợp 3 nhóm thuốc A + C + D và MRA',
  NULL, NULL,
  '{"action_type": "COMBINE_ACD_MRA"}'::jsonb, NULL,
  NULL, NULL,
  6, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_ADD_MRA'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_C_MRA_NOT_TOLERATED', 'CONDITION'::node_type,
  'Does not tolerate MRA', 'Không có khả năng dung nạp MRA',
  '{"op": "eq", "path": "input.tolerates_mra", "value": false}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  7, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_C_MRA_NOT_TOLERATED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_ADD_D', 'ACTION'::node_type,
  'Add D', 'Thêm D',
  NULL, NULL,
  '{"action_type": "ADD_D"}'::jsonb, NULL,
  NULL, NULL,
  8, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_ADD_D'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_CHECK_SPIRONOLACTONE', 'ACTION'::node_type,
  'Check Spironolactone tolerance', 'Kiểm tra khả năng dung nạp Spironolactone (lợi tiểu giữ kali)',
  NULL, NULL,
  '{"action_type": "CHECK_SPIRONOLACTONE"}'::jsonb, NULL,
  NULL, NULL,
  9, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_CHECK_SPIRONOLACTONE'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_C_SPIRONOLACTONE_TOLERATED', 'CONDITION'::node_type,
  'Tolerates Spironolactone', 'Có khả năng dung nạp Spironolactone',
  '{"op": "eq", "path": "input.tolerates_spironolactone", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  10, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_C_SPIRONOLACTONE_TOLERATED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_ADD_SPIRONOLACTONE', 'ACTION'::node_type,
  'Add low-dose Spironolactone to current regimen', 'Thêm Spironolactone liều thấp kết hợp với liều thuốc điều trị hiện có',
  NULL, NULL,
  '{"action_type": "ADD_SPIRONOLACTONE"}'::jsonb, NULL,
  NULL, NULL,
  11, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_ADD_SPIRONOLACTONE'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_C_SPIRONOLACTONE_NOT_TOLERATED', 'CONDITION'::node_type,
  'Does not tolerate Spironolactone', 'Không có khả năng dung nạp Spironolactone',
  '{"op": "eq", "path": "input.tolerates_spironolactone", "value": false}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  12, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_C_SPIRONOLACTONE_NOT_TOLERATED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_ALTERNATIVES', 'ACTION'::node_type,
  'Alternatives: Add K-sparing D, Increase D dose, or Add Bisoprolol/Doxazosin', 'Thêm nhóm D giữ kali, Tăng liều nhóm D, hoặc Thêm Bisoprolol/Doxazosin',
  NULL, NULL,
  '{"action_type": "THERAPEUTIC_ALTERNATIVES"}'::jsonb, NULL,
  NULL, NULL,
  13, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_ALTERNATIVES'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_C_BP_TARGET_REACHED', 'CONDITION'::node_type,
  'BP reaches target', 'HA đạt đích điều trị',
  '{"op": "eq", "path": "input.bp_target_reached", "value": true}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  14, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_C_BP_TARGET_REACHED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_END_MAINTAIN', 'END'::node_type,
  'Maintain regimen', 'Duy trì phác đồ',
  NULL, NULL,
  '{"action_type": "MAINTAIN_REGIMEN"}'::jsonb, NULL,
  NULL, NULL,
  15, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_END_MAINTAIN'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_C_BP_TARGET_NOT_REACHED', 'CONDITION'::node_type,
  'BP does not reach target', 'HA không đạt đích điều trị',
  '{"op": "eq", "path": "input.bp_target_reached", "value": false}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  16, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_C_BP_TARGET_NOT_REACHED'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_END_REFER', 'END'::node_type,
  'Refer to specialized center', 'Chuyển lên trung tâm chuyên khoa',
  NULL, NULL,
  '{"action_type": "REFER_TO_SPECIALIZED_CENTER"}'::jsonb, NULL,
  NULL, NULL,
  17, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_END_REFER'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_C_FULL', 'CONDITION'::node_type,
  'Optimal standard', 'Tiêu chuẩn tối ưu',
  '{"op": "eq", "path": "input.facility_capability", "value": "FULL_RESOURCES"}'::jsonb, NULL,
  NULL, NULL,
  NULL, NULL,
  18, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_C_FULL'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_OPTIMAL_TREATMENT', 'ACTION'::node_type,
  'Treat according to optimal standard and enhance lifestyle changes', 'Điều trị theo tiêu chuẩn tối ưu và Tăng cường biện pháp tđls, đặc biệt là hạn chế muối',
  NULL, NULL,
  '{"action_type": "LIFESTYLE_CHANGES", "salt_restriction": true}'::jsonb, NULL,
  NULL, NULL,
  19, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_OPTIMAL_TREATMENT'
);


INSERT INTO public.decision_nodes
  (id, tree_id, node_key, node_type,
   text_en, text_vi, condition_definition, context_patch,
   action_payload, global_config,
   link_target_tree_key, link_target_node_key,
   display_order, created_at, updated_at)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension'),
  'T13_A_CONSIDER_DEVICE', 'ACTION'::node_type,
  'Consider device intervention', 'Xem xét điều trị can thiệp dụng cụ',
  NULL, NULL,
  '{"action_type": "CONSIDER_DEVICE_INTERVENTION"}'::jsonb, NULL,
  NULL, NULL,
  20, NOW(), NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_nodes
  WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
    AND node_key = 'T13_A_CONSIDER_DEVICE'
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_D'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CHECK_SPIRONOLACTONE'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_D')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CHECK_SPIRONOLACTONE')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_MRA'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_REACHED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_MRA')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_REACHED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_MRA'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_NOT_REACHED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_MRA')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_NOT_REACHED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_SPIRONOLACTONE'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_REACHED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_SPIRONOLACTONE')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_REACHED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_SPIRONOLACTONE'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_NOT_REACHED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_SPIRONOLACTONE')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_NOT_REACHED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ALTERNATIVES'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_REACHED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ALTERNATIVES')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_REACHED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ALTERNATIVES'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_NOT_REACHED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ALTERNATIVES')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_NOT_REACHED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CHECK_MRA'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_MRA_TOLERATED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CHECK_MRA')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_MRA_TOLERATED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CHECK_MRA'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_MRA_NOT_TOLERATED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CHECK_MRA')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_MRA_NOT_TOLERATED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CHECK_SPIRONOLACTONE'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_SPIRONOLACTONE_TOLERATED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CHECK_SPIRONOLACTONE')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_SPIRONOLACTONE_TOLERATED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CHECK_SPIRONOLACTONE'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_SPIRONOLACTONE_NOT_TOLERATED'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CHECK_SPIRONOLACTONE')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_SPIRONOLACTONE_NOT_TOLERATED')
    AND traversal_order = 2
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CONSIDER_DEVICE'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_END_REFER'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CONSIDER_DEVICE')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_END_REFER')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ESSENTIAL_TREATMENT'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CHECK_MRA'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ESSENTIAL_TREATMENT')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CHECK_MRA')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_OPTIMAL_TREATMENT'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CONSIDER_DEVICE'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_OPTIMAL_TREATMENT')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CONSIDER_DEVICE')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_NOT_REACHED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_END_REFER'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_NOT_REACHED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_END_REFER')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_REACHED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_END_MAINTAIN'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_REACHED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_END_MAINTAIN')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_FULL'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_OPTIMAL_TREATMENT'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_FULL')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_OPTIMAL_TREATMENT')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_LIMITED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ESSENTIAL_TREATMENT'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_LIMITED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ESSENTIAL_TREATMENT')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_MRA_NOT_TOLERATED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_D'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_MRA_NOT_TOLERATED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_D')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_MRA_TOLERATED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_MRA'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_MRA_TOLERATED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_MRA')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_SPIRONOLACTONE_NOT_TOLERATED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ALTERNATIVES'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_SPIRONOLACTONE_NOT_TOLERATED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ALTERNATIVES')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_SPIRONOLACTONE_TOLERATED'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_SPIRONOLACTONE'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_SPIRONOLACTONE_TOLERATED')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_SPIRONOLACTONE')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_START'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_LIMITED'),
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_START')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_LIMITED')
    AND traversal_order = 1
);


INSERT INTO public.decision_edges (id, from_node_id, to_node_id, traversal_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_START'),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_FULL'),
  2
WHERE NOT EXISTS (
  SELECT 1 FROM public.decision_edges
  WHERE from_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_START')
    AND to_node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_FULL')
    AND traversal_order = 2
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_D'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_D')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_MRA'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_MRA')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ADD_SPIRONOLACTONE'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ADD_SPIRONOLACTONE')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ALTERNATIVES'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ALTERNATIVES')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CHECK_MRA'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CHECK_MRA')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CHECK_SPIRONOLACTONE'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CHECK_SPIRONOLACTONE')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_CONSIDER_DEVICE'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_CONSIDER_DEVICE')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_ESSENTIAL_TREATMENT'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_ESSENTIAL_TREATMENT')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_A_OPTIMAL_TREATMENT'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_A_OPTIMAL_TREATMENT')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_NOT_REACHED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_NOT_REACHED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_BP_TARGET_REACHED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_BP_TARGET_REACHED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_FULL'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_FULL')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_LIMITED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_LIMITED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_MRA_NOT_TOLERATED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_MRA_NOT_TOLERATED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_MRA_TOLERATED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_MRA_TOLERATED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_SPIRONOLACTONE_NOT_TOLERATED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_SPIRONOLACTONE_NOT_TOLERATED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_C_SPIRONOLACTONE_TOLERATED'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_C_SPIRONOLACTONE_TOLERATED')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_END_MAINTAIN'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_END_MAINTAIN')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_END_REFER'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_END_REFER')
    AND reference_order = 1
);


INSERT INTO public.node_source_references
  (id, node_id, source_title, section_path, locator, locator_detail,
   printed_page_numbers, pdf_page_numbers, reference_note, reference_order)
SELECT
  gen_random_uuid(),
  (SELECT id FROM public.decision_nodes
   WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
     AND node_key = 'T13_START'),
  'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)',
  '["3.6. Cu00e1c tru01b0u1eddng hu1ee3p tu0103ng huyu1ebft u00e1p u0111u1eb7c biu1ec7t", "3.6.1. Tu0103ng huyu1ebft u00e1p khu00e1ng tru1ecb"]'::jsonb,
  '3.6.1. Tăng huyết áp kháng trị',
  NULL,
  '{24}'::integer[],
  '{26}'::integer[],
  NULL,
  1
WHERE NOT EXISTS (
  SELECT 1 FROM public.node_source_references
  WHERE node_id = (SELECT id FROM public.decision_nodes
    WHERE tree_id = (SELECT id FROM public.decision_trees WHERE tree_key = 'resistant-hypertension')
      AND node_key = 'T13_START')
    AND reference_order = 1
);


COMMIT;
