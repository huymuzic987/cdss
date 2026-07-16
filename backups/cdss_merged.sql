--
-- CDSS database backup (merged)
-- Source database : neondb
-- Server version  : PostgreSQL 18.4 (eaf151e) on aarch64-unknown-linux-gnu, compiled by gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, 64-bit
--
-- Merged from, in order:
--   1. cdss_prod_20260701.sql  - schema (types/tables/constraints/indexes) and
--      base data for 5 trees: risk-classification, treatment-threshold-and-bp-target,
--      essential-treatment-strategy, optimal-treatment-strategy, hypertension-diagnosis
--   2. tree6.sql                                        -> drug-combination
--   3. tree8.sql                                        -> hypertension-type-2-diabetes
--   4. seed_hypertension_coronary_artery_disease.sql     -> hypertension-coronary-artery-disease
--   5. seed_hypertension_heart_failure.sql               -> hypertension-heart-failure
--   6. tree11.sql                                        -> hypertension-chronic-kidney-disease
--   7. tree12.sql                                        -> hypertension-in-pregnancy
--   8. seed_resistant_hypertension.sql                   -> resistant-hypertension
--   9. tree14.sql                                        -> hypertensive-emergency
--
-- cdss_prod_20260705.sql intentionally excluded (per request) - it is a later
-- snapshot that already contains the result of applying scripts 2-9 above
-- (plus hypertension-type-2-diabetes/hypertension-in-pregnancy data that here
-- instead comes from tree8.sql/tree12.sql), so it is not a merge input.
--
-- Individual per-tree scripts were originally separate, standalone
-- transactions; they have been spliced into this file's single BEGIN/COMMIT,
-- in dependency-safe order (each tree's own DELETE-then-insert or
-- insert-only body is preserved verbatim, including its original comments).
--
-- Restore into an EMPTY database:
--   createdb cdss_restore
--   psql -d cdss_restore -f <this file>
--

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

BEGIN;

-- Types
CREATE TYPE public.node_type AS ENUM ('START', 'CONDITION', 'INFERENCE', 'ACTION', 'END', 'LINK', 'GLOBAL');

-- Tables
CREATE TABLE public.alembic_version (
    "version_num" character varying(32) NOT NULL
);

CREATE TABLE public.decision_edges (
    "id" uuid NOT NULL,
    "from_node_id" uuid NOT NULL,
    "to_node_id" uuid NOT NULL,
    "traversal_order" integer NOT NULL
);

CREATE TABLE public.decision_nodes (
    "id" uuid NOT NULL,
    "tree_id" uuid NOT NULL,
    "node_key" text NOT NULL,
    "node_type" public.node_type NOT NULL,
    "text_en" text NOT NULL,
    "text_vi" text NOT NULL,
    "condition_definition" jsonb,
    "context_patch" jsonb,
    "action_payload" jsonb,
    "global_config" jsonb,
    "link_target_tree_key" text,
    "link_target_node_key" text,
    "display_order" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL
);

CREATE TABLE public.decision_trees (
    "id" uuid NOT NULL,
    "tree_key" text NOT NULL,
    "name_en" text NOT NULL,
    "name_vi" text NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL
);

CREATE TABLE public.development_runtime_logs (
    "id" uuid NOT NULL,
    "request_id" uuid NOT NULL,
    "environment" text NOT NULL,
    "input_payload" jsonb NOT NULL,
    "inference_context" jsonb NOT NULL,
    "journey" jsonb NOT NULL,
    "output_payload" jsonb,
    "error_payload" jsonb,
    "created_at" timestamp with time zone NOT NULL
);

CREATE TABLE public.node_source_references (
    "id" uuid NOT NULL,
    "node_id" uuid NOT NULL,
    "source_title" text NOT NULL,
    "section_path" jsonb NOT NULL,
    "locator" text,
    "locator_detail" text,
    "printed_page_numbers" smallint[],
    "pdf_page_numbers" smallint[],
    "reference_note" text,
    "reference_order" integer DEFAULT 0 NOT NULL
);

-- Primary keys, unique and check constraints
ALTER TABLE public.alembic_version ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);
ALTER TABLE public.decision_edges ADD CONSTRAINT decision_edges_pkey PRIMARY KEY (id);
ALTER TABLE public.decision_edges ADD CONSTRAINT uq_decision_edges_from_to UNIQUE (from_node_id, to_node_id);
ALTER TABLE public.decision_edges ADD CONSTRAINT uq_decision_edges_from_traversal_order UNIQUE (from_node_id, traversal_order);
ALTER TABLE public.decision_nodes ADD CONSTRAINT decision_nodes_pkey PRIMARY KEY (id);
ALTER TABLE public.decision_nodes ADD CONSTRAINT uq_decision_nodes_tree_id_node_key UNIQUE (tree_id, node_key);
ALTER TABLE public.decision_trees ADD CONSTRAINT decision_trees_name_en_key UNIQUE (name_en);
ALTER TABLE public.decision_trees ADD CONSTRAINT decision_trees_name_vi_key UNIQUE (name_vi);
ALTER TABLE public.decision_trees ADD CONSTRAINT decision_trees_pkey PRIMARY KEY (id);
ALTER TABLE public.decision_trees ADD CONSTRAINT decision_trees_tree_key_key UNIQUE (tree_key);
ALTER TABLE public.development_runtime_logs ADD CONSTRAINT ck_development_runtime_logs_environment CHECK ((environment = ANY (ARRAY['development'::text, 'test'::text])));
ALTER TABLE public.development_runtime_logs ADD CONSTRAINT development_runtime_logs_pkey PRIMARY KEY (id);
ALTER TABLE public.node_source_references ADD CONSTRAINT node_source_references_pkey PRIMARY KEY (id);
ALTER TABLE public.node_source_references ADD CONSTRAINT uq_node_source_references_node_id_reference_order UNIQUE (node_id, reference_order);

-- Foreign keys
ALTER TABLE public.decision_edges ADD CONSTRAINT decision_edges_from_node_id_fkey FOREIGN KEY (from_node_id) REFERENCES decision_nodes(id);
ALTER TABLE public.decision_edges ADD CONSTRAINT decision_edges_to_node_id_fkey FOREIGN KEY (to_node_id) REFERENCES decision_nodes(id);
ALTER TABLE public.decision_nodes ADD CONSTRAINT decision_nodes_tree_id_fkey FOREIGN KEY (tree_id) REFERENCES decision_trees(id);
ALTER TABLE public.node_source_references ADD CONSTRAINT node_source_references_node_id_fkey FOREIGN KEY (node_id) REFERENCES decision_nodes(id);

-- Indexes
CREATE INDEX ix_decision_edges_from_node_id ON public.decision_edges USING btree (from_node_id);
CREATE INDEX ix_decision_edges_to_node_id ON public.decision_edges USING btree (to_node_id);
CREATE INDEX ix_development_runtime_logs_created_at ON public.development_runtime_logs USING btree (created_at);
CREATE INDEX ix_development_runtime_logs_request_id ON public.development_runtime_logs USING btree (request_id);
CREATE INDEX ix_node_source_references_node_id ON public.node_source_references USING btree (node_id);

-- Data
COPY public.decision_trees ("id", "tree_key", "name_en", "name_vi", "created_at", "updated_at") FROM stdin;
8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	risk-classification	Risk Classification	Phân tầng nguy cơ	2026-06-27 08:31:00.446744+00	2026-06-27 14:43:43.947879+00
723b3d9d-5052-a626-1ab8-5f3a2145173e	treatment-threshold-and-bp-target	Treatment Threshold and BP Target	Ngưỡng Huyết Áp và Đích điều trị	2026-06-27 10:16:47.50998+00	2026-06-27 15:51:59.041846+00
e7ffabdc-c629-b367-585c-5c081b7e3ee5	essential-treatment-strategy	Essential treatment strategy	Cây chiến lược điều trị thiết yếu	2026-06-27 16:01:18.770793+00	2026-06-28 04:53:28.115396+00
5be98c95-06f2-e474-21d9-cb52308e0455	optimal-treatment-strategy	Optimal treatment strategy	Cây chiến lược điều trị tối ưu	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
3897f50b-1c59-f954-5bef-89650cc45e5a	hypertension-diagnosis	Hypertension Diagnosis	Chẩn đoán THA	2026-06-27 07:20:49.313128+00	2026-06-28 07:51:47.889206+00
\.

COPY public.decision_nodes ("id", "tree_id", "node_key", "node_type", "text_en", "text_vi", "condition_definition", "context_patch", "action_payload", "global_config", "link_target_tree_key", "link_target_node_key", "display_order", "created_at", "updated_at") FROM stdin;
854590f4-9e9c-3158-47af-43695e29611e	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_START_PATIENT_INFORMATION	START	Patient information	Thông tin bệnh nhân	\N	\N	\N	\N	\N	\N	1	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
af62ea0d-827f-488d-9218-ffb2d0e4e0b0	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_IS_PREGNANT	CONDITION	Patient is pregnant	Bệnh nhân đang mang thai	{"path": "input.is_pregnant", "op": "eq", "value": true}	\N	\N	\N	\N	\N	65	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
8a526e4b-cfd9-4b7b-8fc5-06c18cad2dd8	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_HYPERTENSION_IN_PREGNANCY	LINK	Hypertension in Pregnancy Tree	Cây: Tăng huyết áp thai kỳ	\N	\N	\N	\N	hypertension-in-pregnancy	\N	66	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
8a14e0bd-3f41-4672-9b28-f236d56cfe99	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_IS_NOT_PREGNANT	CONDITION	Patient is not pregnant	Bệnh nhân không mang thai	{"path": "input.is_pregnant", "op": "eq", "value": false}	\N	\N	\N	\N	\N	67	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
a04f0087-1e67-7368-d086-d6fcccdaedb1	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_CLINIC_1_CRISIS	CONDITION	First clinic blood-pressure measurement\nSBP ≥ 180 mmHg OR DBP ≥ 120 mmHg	HAPK lần 1\nHATT ≥ 180 hoặc HATTr ≥ 120 mmHg	{"any": [{"op": "gte", "path": "input.clinic_1_sbp", "value": 180}, {"op": "gte", "path": "input.clinic_1_dbp", "value": 120}]}	\N	\N	\N	\N	\N	2	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
bfbb746b-d5ff-6d27-a5e6-5376a31d2841	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_HYPERTENSIVE_EMERGENCY	INFERENCE	Hypertensive emergency	THA CẤP CỨU	\N	{"diagnosis": {"hypertension_class": "HYPERTENSIVE_EMERGENCY"}}	\N	\N	\N	\N	3	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
b8778eca-3e96-47d7-fc9d-c8ff3c68e3f7	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_HYPERTENSIVE_EMERGENCY	LINK	Hypertensive Emergency Tree	Cây 14: THA CẤP CỨU	\N	\N	\N	\N	hypertensive-emergency	\N	4	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
6538e358-5110-978e-fdeb-9f9163930524	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_CLINIC_1_NON_CRISIS	CONDITION	First clinic blood-pressure measurement\nSBP < 180 mmHg AND DBP < 120 mmHg	HAPK lần 1\nHATT < 180 và HATTr < 120 mmHg	{"all": [{"op": "lt", "path": "input.clinic_1_sbp", "value": 180}, {"op": "lt", "path": "input.clinic_1_dbp", "value": 120}]}	\N	\N	\N	\N	\N	5	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
7bc03fb5-45fa-4d03-6732-b8f4d0fb67d8	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_CLINIC_2_DIRECT_RANGE	CONDITION	Second clinic blood-pressure measurement\nSBP 140–179 mmHg AND DBP 90–119 mmHg	HAPK lần 2\nHATT 140–179 và HATTr 90–119 mmHg	{"all": [{"op": "gte", "path": "input.clinic_2_sbp", "value": 140}, {"op": "lte", "path": "input.clinic_2_sbp", "value": 179}, {"op": "gte", "path": "input.clinic_2_dbp", "value": 90}, {"op": "lte", "path": "input.clinic_2_dbp", "value": 119}]}	\N	\N	\N	\N	\N	6	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
8902d0f7-7e45-05f3-57b4-3cbab88a2766	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_CLINIC_2_LOWER	CONDITION	Second clinic blood-pressure measurement\nSBP < 140 mmHg OR DBP < 90 mmHg	HAPK lần 2\nHATT < 140 hoặc HATTr < 90 mmHg	{"any": [{"op": "lt", "path": "input.clinic_2_sbp", "value": 140}, {"op": "lt", "path": "input.clinic_2_dbp", "value": 90}]}	\N	\N	\N	\N	\N	7	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
82e84f39-0a8b-ed8e-14f1-78a9db7c991c	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_DIRECT_ISOLATED_SYSTOLIC	CONDITION	SBP ≥ 140 mmHg AND DBP < 90 mmHg	HATT ≥ 140 và HATTr < 90 mmHg	{"all": [{"op": "gte", "path": "input.clinic_2_sbp", "value": 140}, {"op": "lt", "path": "input.clinic_2_dbp", "value": 90}]}	\N	\N	\N	\N	\N	8	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
b252d144-2b2d-17d1-97d6-ebe8419d6347	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_DIRECT_ISOLATED_SYSTOLIC	INFERENCE	Isolated systolic hypertension	THA tâm thu đơn độc	\N	{"diagnosis": {"hypertension_phenotype": "ISOLATED_SYSTOLIC_HYPERTENSION"}}	\N	\N	\N	\N	9	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
024340ba-69f5-8b5f-ee24-1a8ac453af3f	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_DIRECT_PREFER_THIAZIDE_LIKE_CCB	INFERENCE	Prefer thiazide-like diuretics and calcium channel blockers	Ưu tiên dùng thuốc lợi tiểu thiazide-like và CKCa	\N	{"treatment_preferences": {"preferred_drug_classes": ["THIAZIDE_LIKE_DIURETIC", "CALCIUM_CHANNEL_BLOCKER"]}}	\N	\N	\N	\N	10	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
993144cf-893d-ef87-efb3-a1adb2aff1b7	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_DIRECT_ISH_GRADE_2	CONDITION	SBP ≥ 160 mmHg OR DBP ≥ 100 mmHg	HATT ≥ 160 HOẶC HATTr ≥ 100 mmHg	{"any": [{"op": "gte", "path": "input.clinic_2_sbp", "value": 160}, {"op": "gte", "path": "input.clinic_2_dbp", "value": 100}]}	\N	\N	\N	\N	\N	11	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
4156b708-5a62-f921-c8f8-c4fcc66ac355	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_DIRECT_ISH_GRADE_2	INFERENCE	Grade 2 hypertension	THA độ 2	\N	{"diagnosis": {"hypertension_class": "GRADE_2_HYPERTENSION"}}	\N	\N	\N	\N	12	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
b96559b4-f6fe-70e4-1704-7ea3325dbd6e	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_DIRECT_ISH_GRADE_2_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	13	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
6ef8e7ef-9791-2d7a-de78-92bcf0157fd3	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_DIRECT_ISH_GRADE_1	CONDITION	SBP 140–159 mmHg OR DBP 90–99 mmHg	HATT 140–159 mmHg HOẶC HATTr 90–99 mmHg	{"any": [{"all": [{"op": "gte", "path": "input.clinic_2_sbp", "value": 140}, {"op": "lte", "path": "input.clinic_2_sbp", "value": 159}]}, {"all": [{"op": "gte", "path": "input.clinic_2_dbp", "value": 90}, {"op": "lte", "path": "input.clinic_2_dbp", "value": 99}]}]}	\N	\N	\N	\N	\N	14	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
f71ef072-f987-4bdf-74ea-9831561c847d	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_DIRECT_ISH_GRADE_1	INFERENCE	Grade 1 hypertension	THA độ 1	\N	{"diagnosis": {"hypertension_class": "GRADE_1_HYPERTENSION"}}	\N	\N	\N	\N	15	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
392d4dcf-3a87-5994-7a28-319df16913e1	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_DIRECT_ISH_GRADE_1_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	16	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
c4c213f6-cc3f-b126-965c-7cc29a920737	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_DIRECT_GRADE_2	CONDITION	SBP ≥ 160 mmHg OR DBP ≥ 100 mmHg	HATT ≥ 160 HOẶC HATTr ≥ 100 mmHg	{"any": [{"op": "gte", "path": "input.clinic_2_sbp", "value": 160}, {"op": "gte", "path": "input.clinic_2_dbp", "value": 100}]}	\N	\N	\N	\N	\N	17	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
50183af5-180d-684d-ca85-0a39375047f6	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_DIRECT_GRADE_2	INFERENCE	Grade 2 hypertension	THA độ 2	\N	{"diagnosis": {"hypertension_class": "GRADE_2_HYPERTENSION"}}	\N	\N	\N	\N	18	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
3b3d3e10-8020-0e11-85ab-694d7e2606d7	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_DIRECT_GRADE_2_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	19	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
f61c1dae-7953-1d8c-7397-3d1014a9a56e	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_DIRECT_GRADE_1	CONDITION	SBP 140–159 mmHg OR DBP 90–99 mmHg	HATT 140–159 mmHg HOẶC HATTr 90–99 mmHg	{"any": [{"all": [{"op": "gte", "path": "input.clinic_2_sbp", "value": 140}, {"op": "lte", "path": "input.clinic_2_sbp", "value": 159}]}, {"all": [{"op": "gte", "path": "input.clinic_2_dbp", "value": 90}, {"op": "lte", "path": "input.clinic_2_dbp", "value": 99}]}]}	\N	\N	\N	\N	\N	20	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
82622d63-8358-42e4-5396-5b0de98cb992	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_DIRECT_GRADE_1	INFERENCE	Grade 1 hypertension	THA độ 1	\N	{"diagnosis": {"hypertension_class": "GRADE_1_HYPERTENSION"}}	\N	\N	\N	\N	21	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
71abd56d-80ba-11c6-f7f4-ea0fea899e94	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_DIRECT_GRADE_1_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	22	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
bc1e94e0-c24f-60dc-0183-55a69caf4364	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_OPTIMAL_MEASUREMENT_ROUTE	CONDITION	Home blood-pressure measurement and continuous blood-pressure measurement method (optimal)	Phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	{"any": [{"op": "exists", "path": "input.home_sbp"}, {"op": "exists", "path": "input.home_dbp"}, {"op": "exists", "path": "input.daytime_sbp"}, {"op": "exists", "path": "input.daytime_dbp"}, {"op": "exists", "path": "input.bp_24h_sbp"}, {"op": "exists", "path": "input.bp_24h_dbp"}]}	\N	\N	\N	\N	\N	23	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
f568eca7-99d1-6a0a-db05-08b1ef7f342a	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_LINK_GRADE_2_HIGH_RISK_TO_TREE_3	LINK	Treatment Threshold and BP Target Tree	Cây 3: Ngưỡng và đích điều trị	\N	\N	\N	\N	treatment-threshold-and-bp-target	\N	28	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
4ef64653-acf3-b7b9-e6fc-8e594a02967a	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_GRADE_2_RISK_FACTOR_COUNT_0	CONDITION	0 risk factors	0 YTNC	{"op": "eq", "path": "input.risk_factor_count", "value": 0}	\N	\N	\N	\N	\N	29	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
ae850596-a036-f3d1-021b-462917f62055	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_OUT_OF_OFFICE_ELEVATED	CONDITION	Home BP: SBP ≥ 135 mmHg OR DBP ≥ 85 mmHg\nOR daytime BP: SBP ≥ 135 mmHg OR DBP ≥ 85 mmHg\nOR 24-hour BP: SBP ≥ 130 mmHg OR DBP ≥ 80 mmHg\nOR morning BP: SBP ≥ 135 mmHg OR DBP ≥ 85 mmHg	HATN HATT ≥ 135 HOẶC HATTr ≥ 85\nHOẶC HA ban ngày HATT ≥ 135 HOẶC HATTr ≥ 85\nHOẶC HA 24h HATT ≥ 130 HOẶC HATTr ≥ 80\nHOẶC HA buổi sáng HATT ≥ 135 HOẶC HATTr ≥ 85	{"any": [{"all": [{"op": "exists", "path": "input.home_sbp"}, {"op": "gte", "path": "input.home_sbp", "value": 135}]}, {"all": [{"op": "exists", "path": "input.home_dbp"}, {"op": "gte", "path": "input.home_dbp", "value": 85}]}, {"all": [{"op": "exists", "path": "input.daytime_sbp"}, {"op": "gte", "path": "input.daytime_sbp", "value": 135}]}, {"all": [{"op": "exists", "path": "input.daytime_dbp"}, {"op": "gte", "path": "input.daytime_dbp", "value": 85}]}, {"all": [{"op": "exists", "path": "input.bp_24h_sbp"}, {"op": "gte", "path": "input.bp_24h_sbp", "value": 130}]}, {"all": [{"op": "exists", "path": "input.bp_24h_dbp"}, {"op": "gte", "path": "input.bp_24h_dbp", "value": 80}]}, {"all": [{"op": "exists", "path": "input.morning_sbp"}, {"op": "gte", "path": "input.morning_sbp", "value": 135}]}, {"all": [{"op": "exists", "path": "input.morning_dbp"}, {"op": "gte", "path": "input.morning_dbp", "value": 85}]}]}	\N	\N	\N	\N	\N	24	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
f75e07aa-b64c-f05a-3f40-beb41b32da8b	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ELEVATED_OOB_CLINIC_3_ELEVATED	CONDITION	Third clinic blood-pressure measurement\nSBP ≥ 140 mmHg OR DBP ≥ 90 mmHg	HAPK lần 3\nHATT ≥ 140 HOẶC HATTr ≥ 90	{"any": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 140}, {"op": "gte", "path": "input.clinic_3_dbp", "value": 90}]}	\N	\N	\N	\N	\N	25	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
a28ba521-9617-68bd-700b-bd1ea531ef83	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ELEVATED_OOB_CLINIC_3_LOWER	CONDITION	Third clinic blood-pressure measurement\nSBP < 140 mmHg OR DBP < 90 mmHg	HAPK lần 3\nHATT < 140 HOẶC HATTr < 90	{"any": [{"op": "lt", "path": "input.clinic_3_sbp", "value": 140}, {"op": "lt", "path": "input.clinic_3_dbp", "value": 90}]}	\N	\N	\N	\N	\N	26	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
e76d51eb-d7f0-3ac8-9f48-bd5e57eb2e0c	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_MASKED_HYPERTENSION	INFERENCE	Masked hypertension (equivalent to Grade 1 hypertension)	THA ẩn giấu (tương đương độ 1)	\N	{"diagnosis": {"hypertension_class": "MASKED_HYPERTENSION", "risk_classification_group": "GRADE_1_HYPERTENSION"}}	\N	\N	\N	\N	27	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
75763523-d572-842e-ea01-b32478244bd0	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_MASKED_HYPERTENSION_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	28	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
056a6e9f-05e4-2371-5783-3ba963d00c8b	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ELEVATED_OOB_ISOLATED_SYSTOLIC	CONDITION	SBP ≥ 140 mmHg AND DBP < 90 mmHg	HATT ≥ 140 VÀ HATTr < 90 mmHg	{"all": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 140}, {"op": "lt", "path": "input.clinic_3_dbp", "value": 90}]}	\N	\N	\N	\N	\N	29	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
ad79523f-69d2-df24-dfe2-d932d2cebd3b	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ELEVATED_OOB_ISOLATED_SYSTOLIC	INFERENCE	Isolated systolic hypertension	THA tâm thu đơn độc	\N	{"diagnosis": {"hypertension_phenotype": "ISOLATED_SYSTOLIC_HYPERTENSION"}}	\N	\N	\N	\N	30	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
9c646ad6-5544-914d-f5b4-272ff4613e77	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ELEVATED_OOB_PREFER_THIAZIDE_LIKE_CCB	INFERENCE	Prefer thiazide-like diuretics and calcium channel blockers	Ưu tiên dùng thuốc lợi tiểu thiazide-like và CKCa	\N	{"treatment_preferences": {"preferred_drug_classes": ["THIAZIDE_LIKE_DIURETIC", "CALCIUM_CHANNEL_BLOCKER"]}}	\N	\N	\N	\N	31	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
b01e9357-c88c-04f0-365b-f6f88b91cd45	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ELEVATED_OOB_ISH_GRADE_2	CONDITION	SBP ≥ 160 mmHg OR DBP ≥ 100 mmHg	HATT ≥ 160 HOẶC HATTr ≥ 100 mmHg	{"any": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 160}, {"op": "gte", "path": "input.clinic_3_dbp", "value": 100}]}	\N	\N	\N	\N	\N	32	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
6b917a54-139e-9612-88fb-d7a07f13d854	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ELEVATED_OOB_ISH_GRADE_2	INFERENCE	Grade 2 hypertension	THA độ 2	\N	{"diagnosis": {"hypertension_class": "GRADE_2_HYPERTENSION"}}	\N	\N	\N	\N	33	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
f97ae77a-ca30-c1be-b1fe-fddf13b59dc1	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_ELEVATED_OOB_ISH_GRADE_2_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	34	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
889df3c8-b8f3-d06b-8122-5e868cdee57c	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ELEVATED_OOB_ISH_GRADE_1	CONDITION	SBP 140–159 mmHg OR DBP 90–99 mmHg	HATT 140–159 mmHg HOẶC HATTr 90–99 mmHg	{"any": [{"all": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 140}, {"op": "lte", "path": "input.clinic_3_sbp", "value": 159}]}, {"all": [{"op": "gte", "path": "input.clinic_3_dbp", "value": 90}, {"op": "lte", "path": "input.clinic_3_dbp", "value": 99}]}]}	\N	\N	\N	\N	\N	35	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
41df521d-823e-bbeb-ed4b-850f86b212a7	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ELEVATED_OOB_ISH_GRADE_1	INFERENCE	Grade 1 hypertension	THA độ 1	\N	{"diagnosis": {"hypertension_class": "GRADE_1_HYPERTENSION"}}	\N	\N	\N	\N	36	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
447978a9-d6cd-ea05-cd0c-819bae969c8f	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_ELEVATED_OOB_ISH_GRADE_1_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	37	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
8c055fa2-1e69-33ea-7281-0d0e7fc668d4	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ELEVATED_OOB_GRADE_2	CONDITION	SBP ≥ 160 mmHg OR DBP ≥ 100 mmHg	HATT ≥ 160 HOẶC HATTr ≥ 100 mmHg	{"any": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 160}, {"op": "gte", "path": "input.clinic_3_dbp", "value": 100}]}	\N	\N	\N	\N	\N	38	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
e2999392-875c-8b00-231c-c0d860198d0d	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ELEVATED_OOB_GRADE_2	INFERENCE	Grade 2 hypertension	THA độ 2	\N	{"diagnosis": {"hypertension_class": "GRADE_2_HYPERTENSION"}}	\N	\N	\N	\N	39	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
3161f04a-b5d9-012f-fa56-a8ea416aedb1	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_ELEVATED_OOB_GRADE_2_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	40	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
dcdfb9e6-8424-7c53-10c2-c59c612d0016	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ELEVATED_OOB_GRADE_1	CONDITION	SBP 140–159 mmHg OR DBP 90–99 mmHg	HATT 140–159 mmHg HOẶC HATTr 90–99 mmHg	{"any": [{"all": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 140}, {"op": "lte", "path": "input.clinic_3_sbp", "value": 159}]}, {"all": [{"op": "gte", "path": "input.clinic_3_dbp", "value": 90}, {"op": "lte", "path": "input.clinic_3_dbp", "value": 99}]}]}	\N	\N	\N	\N	\N	41	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
e246a50d-938e-801a-9d10-fda5e54e3409	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ELEVATED_OOB_GRADE_1	INFERENCE	Grade 1 hypertension	THA độ 1	\N	{"diagnosis": {"hypertension_class": "GRADE_1_HYPERTENSION"}}	\N	\N	\N	\N	42	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
581f7d7a-70fe-1ede-6b51-6a6f2a8e3dd1	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_ELEVATED_OOB_GRADE_1_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	43	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
15b24644-6822-aeec-5228-6c66fe4e4c34	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_OUT_OF_OFFICE_NORMAL	CONDITION	Home BP: SBP < 135 mmHg AND DBP < 85 mmHg\nOR daytime BP: SBP < 135 mmHg AND DBP < 85 mmHg\nOR 24-hour BP: SBP < 130 mmHg AND DBP < 80 mmHg	HATN HATT < 135 VÀ HATTr < 85\nHOẶC HA ban ngày HATT < 135 VÀ HATTr < 85\nHOẶC HA 24h HATT < 130 VÀ HATTr < 80	{"any": [{"all": [{"op": "exists", "path": "input.home_sbp"}, {"op": "exists", "path": "input.home_dbp"}, {"op": "lt", "path": "input.home_sbp", "value": 135}, {"op": "lt", "path": "input.home_dbp", "value": 85}]}, {"all": [{"op": "exists", "path": "input.daytime_sbp"}, {"op": "exists", "path": "input.daytime_dbp"}, {"op": "lt", "path": "input.daytime_sbp", "value": 135}, {"op": "lt", "path": "input.daytime_dbp", "value": 85}]}, {"all": [{"op": "exists", "path": "input.bp_24h_sbp"}, {"op": "exists", "path": "input.bp_24h_dbp"}, {"op": "lt", "path": "input.bp_24h_sbp", "value": 130}, {"op": "lt", "path": "input.bp_24h_dbp", "value": 80}]}]}	\N	\N	\N	\N	\N	44	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
dee9eca4-41b6-8283-fb90-22d986a02545	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_NORMAL_OOB_CLINIC_3_ELEVATED	CONDITION	Third clinic blood-pressure measurement\nSBP ≥ 140 mmHg OR DBP ≥ 90 mmHg	HAPK lần 3\nHATT ≥ 140 HOẶC HATTr ≥ 90	{"any": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 140}, {"op": "gte", "path": "input.clinic_3_dbp", "value": 90}]}	\N	\N	\N	\N	\N	45	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
150b12aa-ea76-4ef4-4ae9-72e8b3427d57	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_END_WHITE_COAT_HYPERTENSION	END	White-coat hypertension	THA ÁO CHOÀNG TRẮNG	\N	\N	\N	\N	\N	\N	46	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
d65ada75-d44e-f28b-4538-d5b8f7ba7d88	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_NORMAL_OOB_CLINIC_3_LOWER	CONDITION	Third clinic blood-pressure measurement\nSBP < 140 mmHg OR DBP < 90 mmHg	HAPK lần 3\nHATT < 140 HOẶC HATTr < 90	{"any": [{"op": "lt", "path": "input.clinic_3_sbp", "value": 140}, {"op": "lt", "path": "input.clinic_3_dbp", "value": 90}]}	\N	\N	\N	\N	\N	47	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
0120ac75-acdf-48e0-db92-0d53f45198ad	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ESSENTIAL_MEASUREMENT_ROUTE	CONDITION	Clinic blood-pressure measurement method (essential)	Phương pháp đo huyết áp tại phòng khám (thiết yếu)	{"not": {"any": [{"op": "exists", "path": "input.home_sbp"}, {"op": "exists", "path": "input.home_dbp"}, {"op": "exists", "path": "input.daytime_sbp"}, {"op": "exists", "path": "input.daytime_dbp"}, {"op": "exists", "path": "input.bp_24h_sbp"}, {"op": "exists", "path": "input.bp_24h_dbp"}]}}	\N	\N	\N	\N	\N	50	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
2ccf9a48-c739-b8c8-3ff3-58e07085dada	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_CLINIC_3_AVAILABLE	CONDITION	Third clinic blood-pressure measurement	HAPK lần 3	{"all": [{"op": "exists", "path": "input.clinic_3_sbp"}, {"op": "exists", "path": "input.clinic_3_dbp"}]}	\N	\N	\N	\N	\N	51	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
0da5ee04-82fe-8681-957d-0ab16678ad1f	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ESSENTIAL_HYPERTENSION	CONDITION	SBP ≥ 140 mmHg OR DBP ≥ 90 mmHg	HATT ≥ 140 HOẶC HATTr ≥ 90	{"any": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 140}, {"op": "gte", "path": "input.clinic_3_dbp", "value": 90}]}	\N	\N	\N	\N	\N	52	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
e9270ac1-7ccd-40d7-92d4-a8e4d065f611	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ESSENTIAL_HYPERTENSION	INFERENCE	Hypertension	THA	\N	{"diagnosis": {"hypertension_present": true}}	\N	\N	\N	\N	53	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
67ab35c9-30ea-85e4-ffb8-1a15cfb906e1	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ESSENTIAL_GRADE_2	CONDITION	SBP ≥ 160 mmHg OR DBP ≥ 100 mmHg	HATT ≥ 160 HOẶC HATTr ≥ 100 mmHg	{"any": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 160}, {"op": "gte", "path": "input.clinic_3_dbp", "value": 100}]}	\N	\N	\N	\N	\N	54	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
42a86643-3a3d-4e13-e45f-c160a278e0b9	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ESSENTIAL_GRADE_2	INFERENCE	Grade 2 hypertension	THA độ 2	\N	{"diagnosis": {"hypertension_class": "GRADE_2_HYPERTENSION"}}	\N	\N	\N	\N	55	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
da558a72-f0f4-eb91-e3b1-e823f6b4054b	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_ESSENTIAL_GRADE_2_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	56	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
60c1e457-4b7d-614b-8ef7-61506403ef5f	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ESSENTIAL_GRADE_1	CONDITION	SBP 140–159 mmHg OR DBP 90–99 mmHg	HATT 140–159 mmHg HOẶC HATTr 90–99 mmHg	{"any": [{"all": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 140}, {"op": "lte", "path": "input.clinic_3_sbp", "value": 159}]}, {"all": [{"op": "gte", "path": "input.clinic_3_dbp", "value": 90}, {"op": "lte", "path": "input.clinic_3_dbp", "value": 99}]}]}	\N	\N	\N	\N	\N	57	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
1bfbc013-8b60-85f8-0e6f-16bb8b2e08f3	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ESSENTIAL_GRADE_1	INFERENCE	Grade 1 hypertension	THA độ 1	\N	{"diagnosis": {"hypertension_class": "GRADE_1_HYPERTENSION"}}	\N	\N	\N	\N	58	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
e13a27c1-391e-20de-a536-a24514514629	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_ESSENTIAL_GRADE_1_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	59	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
cd0e9072-3ea2-ae16-3d22-9c27c95e0bf5	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ESSENTIAL_HIGH_NORMAL_BP	CONDITION	SBP 130–139 mmHg OR DBP 85–89 mmHg	HATT 130–139 HOẶC HATTr 85–89	{"any": [{"all": [{"op": "gte", "path": "input.clinic_3_sbp", "value": 130}, {"op": "lte", "path": "input.clinic_3_sbp", "value": 139}]}, {"all": [{"op": "gte", "path": "input.clinic_3_dbp", "value": 85}, {"op": "lte", "path": "input.clinic_3_dbp", "value": 89}]}]}	\N	\N	\N	\N	\N	60	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
28c71bb1-a8df-b8d0-bc32-06c0e5006228	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_INF_ESSENTIAL_HIGH_NORMAL_BP	INFERENCE	High-normal BP	HA bình thường-cao	\N	{"diagnosis": {"hypertension_class": "HIGH_NORMAL_BP"}}	\N	\N	\N	\N	61	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
8130a5fc-4e3c-edb9-6a46-d1eb994e3efd	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_LINK_ESSENTIAL_HIGH_NORMAL_BP_TO_RISK	LINK	Risk Classification Tree	Cây 2: Phân Tầng Nguy Cơ	\N	\N	\N	\N	risk-classification	\N	62	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
578ce908-3403-1df1-378a-79136a9eedb3	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_C_ESSENTIAL_NORMAL_BP	CONDITION	SBP < 130 mmHg AND DBP < 85 mmHg	HATT < 130 VÀ HATTr < 85	{"all": [{"op": "lt", "path": "input.clinic_3_sbp", "value": 130}, {"op": "lt", "path": "input.clinic_3_dbp", "value": 85}]}	\N	\N	\N	\N	\N	63	2026-06-27 07:20:49.313128+00	2026-06-27 07:20:49.313128+00
901b8971-4490-05eb-0fb4-7b009bb8929e	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_END_NORMAL_BP	END	Normal BP	HA BÌNH THƯỜNG	\N	\N	\N	\N	\N	\N	48	2026-06-27 07:20:49.313128+00	2026-06-27 07:47:09.765975+00
ec404ee2-7221-4ad8-ca64-c9e9d5363d97	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_START_RISK_AND_COMORBIDITY_INFORMATION	START	Patient risk-factor and comorbidity information	Thông tin về yếu tố nguy cơ, bệnh nền của bệnh nhân	\N	\N	\N	\N	\N	\N	1	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
c0a64934-faa3-7403-22a9-8db45fb883d9	3897f50b-1c59-f954-5bef-89650cc45e5a	T1_END_ESSENTIAL_NORMAL_BP	END	Normal BP	HA BÌNH THƯỜNG	\N	{"diagnosis": {"hypertension_class": "NORMAL_BP"}}	\N	\N	\N	\N	64	2026-06-27 07:20:49.313128+00	2026-06-28 07:51:47.889206+00
677ced6a-83c9-f393-be9d-1f520be5bada	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_GLOBAL_RISK_FACTOR_LIST	GLOBAL	Risk Factors\nAge >65\nMale sex\nSmoking\nElevated LDL\nObesity\nHeart rate >80\nFamily history\nPremature menopause\nPrediabetes\nPhysical inactivity	Yếu Tố Nguy Cơ\nTuổi >65\nNam giới\nHút thuốc\nLDL tăng\nBéo phì\nNhịp tim >80\nTiền sử gia đình\nMãn kinh sớm\nTiền ĐTĐ\nÍt vận động	\N	\N	\N	{"kind": "REFERENCE_LIST", "purpose": "Reference list for the supplied risk-factor count.", "input_path": "input.risk_factor_count"}	\N	\N	2	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
15d21cbf-d095-e977-4b20-b71b993a7aad	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_GLOBAL_RISK_FACTOR_COUNT_AT_LEAST_3_NOTE	GLOBAL	For all BP categories (high-normal BP, Grade 1, Grade 2), ≥3 risk factors indicate high risk immediately.	Tất cả loại THA (Bình thường cao, độ 1, độ 2 nếu có >=3 thì nguy cơ cao ngay)	\N	\N	\N	{"kind": "OVERRIDE_NOTE", "purpose": "Risk-factor count >=3 has immediate high-risk precedence.", "implemented_by_condition": "T2_C_RISK_FACTOR_COUNT_AT_LEAST_3"}	\N	\N	3	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
9dc9020e-d70e-1ebe-f2ea-b390b5346c33	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_INF_HIGH_RISK_COMORBIDITY_PRESENT	INFERENCE	High risk	NGUY CƠ CAO	\N	{"risk": {"level": "HIGH"}}	\N	\N	\N	\N	5	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
230600f6-0c3f-ca8c-4f84-7a449004be41	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_LINK_HIGH_RISK_COMORBIDITY_TO_TREE_3	LINK	Treatment Threshold and BP Target Tree	Cây 3: Ngưỡng và đích điều trị	\N	\N	\N	\N	treatment-threshold-and-bp-target	\N	6	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
3f0e2f17-4775-0538-ce10-6f11dc621c84	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_RISK_FACTOR_COUNT_AT_LEAST_3	CONDITION	At least 3 risk factors	≥3 YTNC	{"op": "gte", "path": "input.risk_factor_count", "value": 3}	\N	\N	\N	\N	\N	7	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
23276de5-636d-3312-1636-1dc4f4b6b969	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_INF_HIGH_RISK_FACTOR_COUNT_AT_LEAST_3	INFERENCE	High risk	NGUY CƠ CAO	\N	{"risk": {"level": "HIGH"}}	\N	\N	\N	\N	8	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
48152ce5-628b-7448-66f0-833128715fc9	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_LINK_HIGH_RISK_FACTOR_COUNT_AT_LEAST_3_TO_TREE_3	LINK	Treatment Threshold and BP Target Tree	Cây 3: Ngưỡng và đích điều trị	\N	\N	\N	\N	treatment-threshold-and-bp-target	\N	9	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
98cee07d-28ca-dcc6-384c-02c30b0b50fe	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_CONTEXT_HIGH_NORMAL_BP	CONDITION	High-normal BP	HA bình thường cao	{"op": "eq", "path": "context.diagnosis.hypertension_class", "value": "HIGH_NORMAL_BP"}	\N	\N	\N	\N	\N	11	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
8058aebe-6375-cafe-b718-d5df20ac85c9	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_CONTEXT_GRADE_1_OR_MASKED_HYPERTENSION	CONDITION	Grade 1 hypertension OR masked hypertension (equivalent to Grade 1)	THA độ 1 HOẶC THA ẩn giấu (Tương đương Độ 1)	{"any": [{"op": "eq", "path": "context.diagnosis.hypertension_class", "value": "GRADE_1_HYPERTENSION"}, {"op": "eq", "path": "context.diagnosis.hypertension_class", "value": "MASKED_HYPERTENSION"}]}	\N	\N	\N	\N	\N	12	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
165c4ea4-8261-4117-9efb-83084a9b3e2a	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_CONTEXT_GRADE_2_HYPERTENSION	CONDITION	Grade 2 hypertension	THA độ 2	{"op": "eq", "path": "context.diagnosis.hypertension_class", "value": "GRADE_2_HYPERTENSION"}	\N	\N	\N	\N	\N	13	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
ba1a1c44-b0fd-499d-144c-ac54731ba62d	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_HIGH_NORMAL_RISK_FACTOR_COUNT_AT_MOST_1	CONDITION	≤1 risk factor	<=1 YTNC	{"op": "lte", "path": "input.risk_factor_count", "value": 1}	\N	\N	\N	\N	\N	14	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
b492a11d-3566-318f-3269-e04bc11d09fa	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_INF_HIGH_NORMAL_LOW_RISK	INFERENCE	Low risk	NGUY CƠ THẤP	\N	{"risk": {"level": "LOW"}}	\N	\N	\N	\N	15	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
ca8f6031-35f3-7851-80f9-dc274edf0f1d	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_LINK_HIGH_NORMAL_LOW_RISK_TO_TREE_3	LINK	Treatment Threshold and BP Target Tree	Cây 3: Ngưỡng và đích điều trị	\N	\N	\N	\N	treatment-threshold-and-bp-target	\N	16	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
3ed68451-bfad-5d50-de50-7c968df606af	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_HIGH_NORMAL_RISK_FACTOR_COUNT_2	CONDITION	2 risk factors	2 YTNC	{"op": "eq", "path": "input.risk_factor_count", "value": 2}	\N	\N	\N	\N	\N	17	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
03f895d0-ee99-19d6-58c3-35b49042dda3	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_INF_HIGH_NORMAL_MEDIUM_RISK	INFERENCE	Medium risk	NGUY CƠ TRUNG BÌNH	\N	{"risk": {"level": "MEDIUM"}}	\N	\N	\N	\N	18	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
943686dd-9e22-48ef-9787-989530941b54	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_LINK_HIGH_NORMAL_MEDIUM_RISK_TO_TREE_3	LINK	Treatment Threshold and BP Target Tree	Cây 3: Ngưỡng và đích điều trị	\N	\N	\N	\N	treatment-threshold-and-bp-target	\N	19	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
fb7c62d1-4d86-0013-e05e-4f862b4a4d8a	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_GRADE_1_OR_MASKED_RISK_FACTOR_COUNT_0	CONDITION	0 risk factors	0 YTNC	{"op": "eq", "path": "input.risk_factor_count", "value": 0}	\N	\N	\N	\N	\N	20	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
27c4d74f-163b-4131-11d4-9597e6404738	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_INF_GRADE_1_OR_MASKED_LOW_RISK	INFERENCE	Low risk	NGUY CƠ THẤP	\N	{"risk": {"level": "LOW"}}	\N	\N	\N	\N	21	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
0365dd82-cd8a-5d80-5236-3ef0f7fe85ac	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_LINK_GRADE_1_OR_MASKED_LOW_RISK_TO_TREE_3	LINK	Treatment Threshold and BP Target Tree	Cây 3: Ngưỡng và đích điều trị	\N	\N	\N	\N	treatment-threshold-and-bp-target	\N	22	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
20a7535d-1695-4d68-0048-c86dc1101221	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_GRADE_1_OR_MASKED_RISK_FACTOR_COUNT_1_OR_2	CONDITION	1 or 2 risk factors	1 hoặc 2 YTNC	{"op": "in", "path": "input.risk_factor_count", "value": [1, 2]}	\N	\N	\N	\N	\N	23	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
d186b9cc-2b53-3662-e66d-655fff3ba7c6	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_INF_GRADE_1_OR_MASKED_MEDIUM_RISK	INFERENCE	Medium risk	NGUY CƠ TRUNG BÌNH	\N	{"risk": {"level": "MEDIUM"}}	\N	\N	\N	\N	24	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
bc18f0a9-5f31-749d-19b1-b65596d769f9	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_LINK_GRADE_1_OR_MASKED_MEDIUM_RISK_TO_TREE_3	LINK	Treatment Threshold and BP Target Tree	Cây 3: Ngưỡng và đích điều trị	\N	\N	\N	\N	treatment-threshold-and-bp-target	\N	25	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
d77ec0d8-f756-6377-6f0a-e8cb2f5e8a15	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_GRADE_2_RISK_FACTOR_COUNT_AT_LEAST_1	CONDITION	At least 1 risk factor	≥1 YTNC	{"op": "gte", "path": "input.risk_factor_count", "value": 1}	\N	\N	\N	\N	\N	26	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
fc7fc2c0-c399-0786-26b1-836ef99c51c4	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_INF_GRADE_2_HIGH_RISK	INFERENCE	High risk	NGUY CƠ CAO	\N	{"risk": {"level": "HIGH"}}	\N	\N	\N	\N	27	2026-06-27 08:31:00.446744+00	2026-06-27 08:31:00.446744+00
1e4d5cba-38ba-630f-2597-8590c916e1d4	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_START_BP_AND_AGE_INFORMATION	START	Patient blood-pressure and age information	Thông tin huyết áp bệnh nhân và tuổi	\N	\N	\N	\N	\N	\N	1	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
bc44960d-3c0a-ffd7-6949-e4da0dc6d7f4	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_GLOBAL_AGE_80_THRESHOLD_NOTE	GLOBAL	At age ≥80, comorbidity status does not affect the treatment threshold. Above-threshold blood pressure should be treated.	>= 80 tuổi không cần care tới có bệnh đồng mắc hay không, trên ngưỡng huyết áp thì điều trị (same cho cả có bệnh đồng mắc và không có bệnh đồng mắc)	\N	\N	\N	{"scope": "AGE_AT_LEAST_80", "purpose": "Comorbidity-independent treatment threshold for patients aged 80 years or older."}	\N	\N	2	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
b2658dcd-838f-ca57-50d3-0ad0e007dcc4	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_AGE_18_TO_69	CONDITION	Age group 18–69	Nhóm Tuổi 18 - 69	{"all": [{"op": "gte", "path": "input.age", "value": 18}, {"op": "lte", "path": "input.age", "value": 69}]}	\N	\N	\N	\N	\N	3	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
b9153f61-98ce-673a-b1bf-9bcb80671d62	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_AGE_70_OR_HIGHER	CONDITION	Age group ≥70	Nhóm tuổi >= 70	{"op": "gte", "path": "input.age", "value": 70}	\N	\N	\N	\N	\N	4	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
a8e8f94a-73e3-90e0-bb13-d5391d228a46	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_NO_COMORBIDITY	CONDITION	No comorbidity	Không có bệnh đồng mắc	{"all": [{"op": "eq", "path": "input.has_coronary_artery_disease", "value": false}, {"op": "eq", "path": "input.has_type_2_diabetes", "value": false}, {"op": "eq", "path": "input.has_heart_failure", "value": false}, {"op": "eq", "path": "input.has_ckd", "value": false}]}	\N	\N	\N	\N	\N	5	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
24dbca8b-981c-416b-e3c9-3189ff36c8d7	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_COMORBIDITY_PRESENT	CONDITION	Comorbidity present	Có bệnh đồng mắc	{"any": [{"op": "eq", "path": "input.has_coronary_artery_disease", "value": true}, {"op": "eq", "path": "input.has_type_2_diabetes", "value": true}, {"op": "eq", "path": "input.has_heart_failure", "value": true}, {"op": "eq", "path": "input.has_ckd", "value": true}]}	\N	\N	\N	\N	\N	6	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
a568efbe-4123-a88c-7824-dce7c9f4744c	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_18_69_NO_COMORBIDITY_BELOW_THRESHOLD	CONDITION	SBP <140 mmHg AND DBP <90 mmHg	HATT < 140 VÀ HATTr < 90	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	7	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
86deea06-0fd7-f7d1-052f-80aadbd34f2d	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_18_69_NO_COMORBIDITY_AT_OR_ABOVE_THRESHOLD	CONDITION	SBP ≥140 mmHg OR DBP ≥90 mmHg	HATT >= 140 HOẶC HATTr >= 90	{"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 140}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	8	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
0c92a137-09dd-cc40-8d65-a16871ae8176	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_ACTION_18_69_NO_COMORBIDITY_LIFESTYLE_AND_FOLLOW_UP	ACTION	Lifestyle modification and continued monitoring	Thay đổi lối sống và tiếp tục theo dõi	\N	\N	{"action_type": "LIFESTYLE_AND_CONTINUED_MONITORING", "follow_up_mode": "NEW_ENCOUNTER", "restart_tree_key": "hypertension-diagnosis", "follow_up_required": true}	\N	\N	\N	9	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
732bb6a9-f802-9e67-8377-bec03ab0ccab	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_INF_18_69_NO_COMORBIDITY_BP_TARGET	INFERENCE	Target SBP 120–<140 mmHg or lower\nTarget DBP <80 mmHg	Đích điều trị HATT 120 - < 140 mmHg hoặc thấp hơn\nĐích điều trị HATTr <80	\N	{"treatment": {"bp_target": {"dbp": {"upper_exclusive_mmhg": 80}, "sbp": {"or_lower": true, "lower_reference_mmhg": 120, "upper_exclusive_mmhg": 140}, "source": "TREE_3_GENERIC"}}}	\N	\N	\N	\N	10	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
07c0033a-c673-f236-3f59-093f5e236863	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_ESSENTIAL_TREATMENT_STRATEGY	LINK	Essential Treatment Strategy Tree	Cây Chiến lược điều trị thiết yếu	{"op": "eq", "path": "input.facility_capability", "value": "LIMITED_RESOURCES"}	\N	\N	\N	essential-treatment-strategy	\N	11	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
38bf4156-78bc-b9f5-2bb4-3ad381e87a28	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_OPTIMAL_TREATMENT_STRATEGY	LINK	Optimal Treatment Strategy Tree	Cây Chiến lược điều trị tối ưu	{"op": "eq", "path": "input.facility_capability", "value": "FULL_RESOURCES"}	\N	\N	\N	optimal-treatment-strategy	\N	12	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
7cee6dc2-7420-d2db-e172-43e3cb73ebf8	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_18_69_COMORBIDITY_BELOW_THRESHOLD	CONDITION	SBP <130 mmHg AND DBP <90 mmHg	HATT < 130 VÀ HATTr < 90	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 130}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	13	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
aac650db-813f-8d02-d74f-52d83aec84f9	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_18_69_COMORBIDITY_AT_OR_ABOVE_THRESHOLD	CONDITION	SBP ≥130 mmHg OR DBP ≥90 mmHg	HATT >= 130 HOẶC HATTr >= 90	{"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	14	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
b03048ca-27aa-09c2-bff4-ee361ac09378	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_ACTION_18_69_COMORBIDITY_LIFESTYLE_AND_FOLLOW_UP	ACTION	Lifestyle modification and continued monitoring	Thay đổi lối sống và tiếp tục theo dõi	\N	\N	{"action_type": "LIFESTYLE_AND_CONTINUED_MONITORING", "follow_up_mode": "NEW_ENCOUNTER", "restart_tree_key": "hypertension-diagnosis", "follow_up_required": true}	\N	\N	\N	15	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
95569744-0278-46a5-b937-6c519a461eec	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_INF_18_69_COMORBIDITY_BP_TARGET	INFERENCE	Target SBP 120–<130 mmHg or lower\nTarget DBP <80 mmHg	Đích điều trị HATT 120 - <130 hoặc thấp hơn\nĐích điều trị HATTr <80	\N	{"treatment": {"bp_target": {"dbp": {"upper_exclusive_mmhg": 80}, "sbp": {"or_lower": true, "lower_reference_mmhg": 120, "upper_exclusive_mmhg": 130}, "source": "TREE_3_GENERIC"}}, "orchestration": {"after_parallel_modifier_trees": {"mode": "SELECT_ONE_BY_INPUT", "input_path": "input.facility_capability", "destinations": {"FULL_RESOURCES": "optimal-treatment-strategy", "LIMITED_RESOURCES": "essential-treatment-strategy"}}}}	\N	\N	\N	\N	16	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
4d190229-83b8-5716-5df3-ac5e80e502a0	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_18_69_HEART_FAILURE_MODIFIER	LINK	Hypertension and Heart Failure Tree	Cây THA + suy tim	{"op": "eq", "path": "input.has_heart_failure", "value": true}	\N	\N	\N	hypertension-heart-failure	\N	17	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
b7e4c349-510a-fc5e-2729-5a95584e8f6d	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_18_69_CORONARY_ARTERY_DISEASE_MODIFIER	LINK	Hypertension and Coronary Artery Disease Tree	Cây THA + bệnh mạch vành	{"op": "eq", "path": "input.has_coronary_artery_disease", "value": true}	\N	\N	\N	hypertension-coronary-artery-disease	\N	18	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
db629483-4764-0a45-10a7-56515b08c8be	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_18_69_TYPE_2_DIABETES_MODIFIER	LINK	Hypertension and Type 2 Diabetes Tree	Cây THA + Đái tháo đường type 2	{"op": "eq", "path": "input.has_type_2_diabetes", "value": true}	\N	\N	\N	hypertension-type-2-diabetes	\N	19	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
06acb6f1-4511-0d26-6ba7-19820b066b76	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_18_69_CHRONIC_KIDNEY_DISEASE_MODIFIER	LINK	Hypertension and Chronic Kidney Disease Tree	Cây THA + Bệnh thận mạn	{"op": "eq", "path": "input.has_ckd", "value": true}	\N	\N	\N	hypertension-chronic-kidney-disease	\N	20	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
d61ccc11-d575-6482-9c9b-231f43424ab1	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_AGE_70_TO_79	CONDITION	Age group 70–79	Nhóm tuổi 70 đến 79	{"all": [{"op": "gte", "path": "input.age", "value": 70}, {"op": "lte", "path": "input.age", "value": 79}]}	\N	\N	\N	\N	\N	21	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
e9e05195-a8f6-b2bd-e31e-6cfa937d1d56	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_AGE_80_OR_HIGHER	CONDITION	Age group ≥80	Nhóm tuổi >= 80	{"op": "gte", "path": "input.age", "value": 80}	\N	\N	\N	\N	\N	22	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
c10efb3e-1efc-6aa1-e0c1-b2e799e2c77b	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_70_79_BELOW_THRESHOLD	CONDITION	SBP <140 mmHg AND DBP <90 mmHg	HATT < 140 VÀ HATTr < 90	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	23	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
fc6394bc-6d70-5ab1-f750-1a26069ac9b7	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_70_79_AT_OR_ABOVE_THRESHOLD	CONDITION	SBP ≥140 mmHg OR DBP ≥90 mmHg	HATT >= 140 HOẶC HATTr >= 90	{"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 140}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	24	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
314a95d2-649f-4168-ffca-5ae74bd586c4	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_ACTION_70_79_LIFESTYLE_AND_FOLLOW_UP	ACTION	Lifestyle modification and continued monitoring	Thay đổi lối sống và tiếp tục theo dõi	\N	\N	{"action_type": "LIFESTYLE_AND_CONTINUED_MONITORING", "follow_up_mode": "NEW_ENCOUNTER", "restart_tree_key": "hypertension-diagnosis", "follow_up_required": true}	\N	\N	\N	25	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
d8ed1b7c-c4d6-ffab-aa92-f41a3acac47b	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_80_OR_HIGHER_BELOW_THRESHOLD	CONDITION	SBP <160 mmHg AND DBP <90 mmHg	HATT < 160 VÀ HATTr < 90	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 160}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	26	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
e3a963b3-778c-bd6c-6346-31ef75b22c12	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_80_OR_HIGHER_AT_OR_ABOVE_THRESHOLD	CONDITION	SBP ≥160 mmHg OR DBP ≥90 mmHg	HATT >= 160 HOẶC HATTr >= 90	{"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 160}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	27	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
9261e551-a1e4-f52d-776f-256476cde602	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_ACTION_80_OR_HIGHER_LIFESTYLE_AND_FOLLOW_UP	ACTION	Lifestyle modification and continued monitoring	Thay đổi lối sống và tiếp tục theo dõi	\N	\N	{"action_type": "LIFESTYLE_AND_CONTINUED_MONITORING", "follow_up_mode": "NEW_ENCOUNTER", "restart_tree_key": "hypertension-diagnosis", "follow_up_required": true}	\N	\N	\N	28	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
c9e3529b-2291-4756-1e9c-13b00c5fdd0f	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_INF_AGE_70_OR_HIGHER_BP_TARGET	INFERENCE	Target SBP <140 mmHg, or <130 mmHg if tolerated\nTarget DBP <80 mmHg	Đích điều trị HATT <140 hoặc <130 nếu dung nạp được\nĐích điều trị HATTr <80	\N	{"treatment": {"bp_target": {"dbp": {"upper_exclusive_mmhg": 80}, "sbp": {"upper_exclusive_mmhg": 140, "preferred_upper_exclusive_if_tolerated_mmhg": 130}, "source": "TREE_3_GENERIC"}}, "orchestration": {"after_parallel_modifier_trees": {"mode": "SELECT_ONE_BY_INPUT", "input_path": "input.facility_capability", "destinations": {"FULL_RESOURCES": "optimal-treatment-strategy", "LIMITED_RESOURCES": "essential-treatment-strategy"}}}}	\N	\N	\N	\N	29	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
68fa1969-490f-f26f-97a2-9923fbd618e7	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_AGE_70_OR_HIGHER_HEART_FAILURE_MODIFIER	LINK	Hypertension and Heart Failure Tree	Cây THA + suy tim	{"op": "eq", "path": "input.has_heart_failure", "value": true}	\N	\N	\N	hypertension-heart-failure	\N	30	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
87e3c582-d29b-2cf0-c6a0-19e728f05f05	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_AGE_70_OR_HIGHER_OLDER_ADULT_MODIFIER	LINK	Hypertension in Older Adults Tree	Cây THA người cao tuổi	\N	\N	\N	\N	hypertension-older-adults	\N	31	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
33827fa5-414a-7753-525f-a350e9ab9532	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_AGE_70_OR_HIGHER_CORONARY_ARTERY_DISEASE_MODIFIER	LINK	Hypertension and Coronary Artery Disease Tree	Cây THA + bệnh mạch vành	{"op": "eq", "path": "input.has_coronary_artery_disease", "value": true}	\N	\N	\N	hypertension-coronary-artery-disease	\N	32	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
956d7df4-6501-0c1b-0bf0-78db627ce19e	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_AGE_70_OR_HIGHER_TYPE_2_DIABETES_MODIFIER	LINK	Hypertension and Type 2 Diabetes Tree	Cây THA + Đái tháo đường type 2	{"op": "eq", "path": "input.has_type_2_diabetes", "value": true}	\N	\N	\N	hypertension-type-2-diabetes	\N	33	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
6d654d4f-aa3a-6835-0c2c-65b55413c439	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_LINK_AGE_70_OR_HIGHER_CHRONIC_KIDNEY_DISEASE_MODIFIER	LINK	Hypertension and Chronic Kidney Disease Tree	Cây THA + Bệnh thận mạn	{"op": "eq", "path": "input.has_ckd", "value": true}	\N	\N	\N	hypertension-chronic-kidney-disease	\N	34	2026-06-27 10:16:47.50998+00	2026-06-27 10:16:47.50998+00
ebd2cf1d-a6d6-e606-f1b7-d83ae2028e4e	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_INF_GRADE_2_ZERO_RISK_FACTOR_HIGH_RISK	INFERENCE	High risk	NGUY CƠ CAO	\N	{"risk": {"level": "HIGH"}}	\N	\N	\N	\N	30	2026-06-27 08:31:00.446744+00	2026-06-27 12:12:43.995138+00
16af59eb-1c84-0708-9259-f351eeb59ae5	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_LINK_GRADE_2_ZERO_RISK_FACTOR_HIGH_RISK_TO_TREE_3	LINK	Treatment Threshold and BP Target Tree	Cây 3: Ngưỡng và đích điều trị	\N	\N	\N	\N	treatment-threshold-and-bp-target	\N	31	2026-06-27 08:31:00.446744+00	2026-06-27 12:12:43.995138+00
cfb91d03-1e28-26a1-acc8-44e033cac052	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_INF_18_69_NO_COMORBIDITY_HIGH_RISK_HABTC_BP_TARGET	INFERENCE	Target SBP 120–<130 mmHg or lower\nTarget DBP <80 mmHg	Đích điều trị HATT 120 - <130 hoặc thấp hơn\nĐích điều trị HATTr <80	\N	{"treatment": {"bp_target": {"dbp": {"upper_exclusive_mmhg": 80}, "sbp": {"or_lower": true, "lower_reference_mmhg": 120, "upper_exclusive_mmhg": 130}, "source": "TREE_3_HIGH_NORMAL_HIGH_RISK"}}}	\N	\N	\N	\N	37	2026-06-27 13:26:06.240489+00	2026-06-27 13:26:06.240489+00
012c8740-0d0a-ffa9-93ff-41f19bf24ee7	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_18_69_NO_COMORBIDITY_BELOW_THRESHOLD_HIGH_RISK_HABTC	CONDITION	High-normal BP and high risk	HABTC và nguy cơ cao	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}, {"op": "eq", "path": "context.risk.level", "value": "HIGH"}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}]}	\N	\N	\N	\N	\N	35	2026-06-27 13:26:06.240489+00	2026-06-27 14:53:38.8633+00
d49ed998-c9d4-c06f-9859-ebd4459f4457	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_18_69_NO_COMORBIDITY_BELOW_THRESHOLD_NOT_HIGH_RISK_HABTC	CONDITION	Below 140/90 without high-risk high-normal BP	HATT <140 VÀ HATTr <90, không thuộc HABTC nguy cơ cao	{"not": {"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}, {"op": "eq", "path": "context.risk.level", "value": "HIGH"}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}]}}	\N	\N	\N	\N	\N	36	2026-06-27 13:26:06.240489+00	2026-06-27 14:53:38.8633+00
7ba7c905-6d36-3414-e4c5-0116b03bcdbf	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_HIGH_RISK_COMORBIDITY_PRESENT	CONDITION	At least 3 of: target-organ damage, CKD stage 3 or higher, diabetes, TIA, stroke, or cardiovascular disease	Có ít nhất 3 trong các yếu tố: TTCQĐ, BTM giai đoạn ≥3, ĐTĐ, TIA, Stroke hoặc Bệnh tim mạch	{"any": [{"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}]}	\N	\N	\N	\N	\N	4	2026-06-27 08:31:00.446744+00	2026-06-27 14:43:43.947879+00
8ceb98a6-3e3f-0fce-ab0d-6b746ac16f7a	8a07bf19-f7e7-bcf8-f0f8-80500bfce38d	T2_C_NO_HIGH_RISK_COMORBIDITY	CONDITION	Fewer than 3 of: target-organ damage, CKD stage 3 or higher, diabetes, TIA, stroke, or cardiovascular disease	Có dưới 3 trong các yếu tố: TTCQĐ, BTM giai đoạn ≥3, ĐTĐ, TIA, Stroke hoặc Bệnh tim mạch	{"not": {"any": [{"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_target_organ_damage", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_ckd_stage_3_or_higher", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_diabetes", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}, {"all": [{"op": "eq", "path": "input.has_tia", "value": true}, {"op": "eq", "path": "input.has_stroke", "value": true}, {"op": "eq", "path": "input.has_cardiovascular_disease", "value": true}]}]}}	\N	\N	\N	\N	\N	10	2026-06-27 08:31:00.446744+00	2026-06-27 14:43:43.947879+00
24fd4dc9-e461-86fe-73ee-72f28c410793	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_18_69_COMORBIDITY_DBP_85_TO_89_TREATMENT	CONDITION	SBP below 130 mmHg and DBP 85–89 mmHg	HATT <130 VÀ HATTr 85–89	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	38	2026-06-27 14:53:38.8633+00	2026-06-27 14:53:38.8633+00
1cd09c61-8f8a-ef32-ef53-eb47481b78c8	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_18_69_COMORBIDITY_DBP_BELOW_85_LIFESTYLE	CONDITION	SBP below 130 mmHg and DBP below 85 mmHg	HATT <130 VÀ HATTr <85	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 130}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 85}]}	\N	\N	\N	\N	\N	39	2026-06-27 14:53:38.8633+00	2026-06-27 14:53:38.8633+00
b262908e-c083-362b-db10-0d10ca4ed024	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_IS_MEDICATION_FOLLOW_UP	CONDITION	Medication follow-up visit	Tái khám sau điều trị thuốc	{"all": [{"op": "eq", "path": "input.is_medication_follow_up", "value": true}]}	\N	\N	\N	\N	\N	3	2026-06-27 15:49:12.978633+00	2026-06-27 15:49:12.978633+00
377554d0-1f57-6179-b0ee-6f03230ff8b0	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_IS_LIFESTYLE_FOLLOW_UP	CONDITION	Lifestyle-management follow-up visit	Tái khám sau thay đổi lối sống	{"all": [{"op": "eq", "path": "input.is_medication_follow_up", "value": false}, {"op": "eq", "path": "input.is_lifestyle_follow_up", "value": true}]}	\N	\N	\N	\N	\N	4	2026-06-27 15:49:12.978633+00	2026-06-27 15:49:12.978633+00
c8edac54-9f97-7fd4-3867-9e14861e3ba2	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_INITIAL_ENCOUNTER	CONDITION	Initial encounter or non-follow-up encounter	Lần khám đầu tiên hoặc không phải lần tái khám	{"all": [{"op": "eq", "path": "input.is_medication_follow_up", "value": false}, {"op": "eq", "path": "input.is_lifestyle_follow_up", "value": false}]}	\N	\N	\N	\N	\N	5	2026-06-27 15:49:12.978633+00	2026-06-27 15:49:12.978633+00
98253717-e67b-66a9-3791-fafcd2bedf4c	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_LIFESTYLE_RESPONSE_ADEQUATE	CONDITION	Lifestyle BP response adequate	Đáp ứng thay đổi lối sống đạt yêu cầu	{"all": [{"op": "gte", "left": {"left_path": "input.pre_lifestyle_clinic_sbp", "expression": "subtract", "right_path": "input.current_clinic_sbp"}, "value": 10}, {"op": "gte", "left": {"left_path": "input.pre_lifestyle_clinic_dbp", "expression": "subtract", "right_path": "input.current_clinic_dbp"}, "value": 5}]}	\N	\N	\N	\N	\N	6	2026-06-27 15:49:12.978633+00	2026-06-27 15:49:12.978633+00
82d39f73-488c-3113-49e7-b92795bd4623	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_C_LIFESTYLE_RESPONSE_INADEQUATE	CONDITION	Lifestyle BP response inadequate	Đáp ứng thay đổi lối sống chưa đạt yêu cầu	{"not": {"all": [{"op": "gte", "left": {"left_path": "input.pre_lifestyle_clinic_sbp", "expression": "subtract", "right_path": "input.current_clinic_sbp"}, "value": 10}, {"op": "gte", "left": {"left_path": "input.pre_lifestyle_clinic_dbp", "expression": "subtract", "right_path": "input.current_clinic_dbp"}, "value": 5}]}}	\N	\N	\N	\N	\N	7	2026-06-27 15:49:12.978633+00	2026-06-27 15:49:12.978633+00
0a1a022d-3fba-8a24-a6ca-602eb97b1936	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_ACTION_LIFESTYLE_FOLLOW_UP_CONTINUE_MONITORING	ACTION	Continue lifestyle management and monitoring	Tiếp tục thay đổi lối sống và theo dõi	\N	\N	{"action_type": "CONTINUE_LIFESTYLE_AND_MONITORING", "rule_origin": "LOCAL_PROJECT_POLICY", "follow_up_mode": "NEW_ENCOUNTER", "restart_tree_key": "hypertension-diagnosis", "follow_up_required": true, "lifestyle_response_threshold_mmhg": {"require_both": true, "minimum_dbp_reduction": 5, "minimum_sbp_reduction": 10}}	\N	\N	\N	8	2026-06-27 15:49:12.978633+00	2026-06-27 15:49:12.978633+00
fe2929b6-a17a-269e-7ffd-23d3ce77c5b5	723b3d9d-5052-a626-1ab8-5f3a2145173e	T3_INF_RESTORE_ACTIVE_BP_TARGET	INFERENCE	Restore active BP target from medication follow-up input	Khôi phục đích huyết áp đang áp dụng từ thông tin tái khám điều trị thuốc	\N	{"operations": [{"op": "COPY_PATH", "to_path": "context.treatment.bp_target", "required": true, "from_path": "input.active_bp_target"}]}	\N	\N	\N	\N	9	2026-06-27 15:51:59.041846+00	2026-06-27 15:51:59.041846+00
c8850768-6a93-5c31-5348-b20795ed8aa2	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_START_BP_AND_AGE_INFORMATION	START	Patient blood pressure and age information	Thông tin huyết áp bệnh nhân và tuổi	\N	\N	\N	\N	\N	\N	1	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
6d02a060-240f-e7b8-2db5-9ade7f4f2708	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_GLOBAL_BP_TARGET_OVERRIDE_NOTE	GLOBAL	Comorbidities may have their own treatment target and override Tree 3 general target. Applies to every BP-target achievement check.	Nếu có bệnh đồng mắc thì có thể bệnh đồng mắc sẽ có đích điều trị riêng và override đích điều trị general của cây 3. Áp dụng cho mọi node condition check HA đã đạt đích điều trị hay chưa	\N	\N	\N	{"applies_to": ["T4_C_INITIAL_REGIMEN_BP_TARGET_REACHED", "T4_C_INITIAL_REGIMEN_BP_TARGET_NOT_REACHED", "T4_C_ESCALATED_REGIMEN_BP_TARGET_REACHED", "T4_C_ESCALATED_REGIMEN_BP_TARGET_NOT_REACHED"], "target_path": "context.treatment.bp_target", "override_rule": "MODIFIER_TREE_TARGET_OVERRIDES_TREE_3_TARGET", "comparison_contract": {"systolic_input_path": "input.current_clinic_sbp", "diastolic_input_path": "input.current_clinic_dbp", "systolic_target_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg", "diastolic_target_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}}	\N	\N	2	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
63be24c7-78b8-e994-a2f9-e8a6c8ff4eff	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_IS_MEDICATION_FOLLOW_UP	CONDITION	Medication follow-up visit	Tái khám sau điều trị thuốc	{"op": "eq", "path": "input.is_medication_follow_up", "value": true}	\N	\N	\N	\N	\N	3	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
4e585981-7ff7-4de4-bbc7-fd1d1faea4fa	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN	CONDITION	Follow-up after initial regimen	Tái khám sau phác đồ điều trị ban đầu	{"op": "eq", "path": "input.medication_follow_up_stage", "value": "INITIAL_REGIMEN"}	\N	\N	\N	\N	\N	4	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
3a6d2484-ceb4-9a84-ffcb-6516984763fc	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_INITIAL_REGIMEN_BP_TARGET_REACHED	CONDITION	Blood pressure target reached	HA đã đạt đích điều trị	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"}, {"op": "lt", "path": "input.current_clinic_dbp", "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}	\N	\N	\N	\N	\N	5	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
ed95f5b7-ca4f-edb5-4809-46868512d5f2	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_INITIAL_REGIMEN_BP_TARGET_NOT_REACHED	CONDITION	Blood pressure target not reached	HA chưa đạt đích điều trị	{"not": {"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"}, {"op": "lt", "path": "input.current_clinic_dbp", "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}}	\N	\N	\N	\N	\N	7	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
0c0f0e4b-15a7-f0ce-7aeb-49e8a356dbce	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_ACTION_INCREASE_DOSE_OR_THREE_DRUG_COMBINATION	ACTION	Increase dose to usual dose or use a three-drug combination; prefer A + C + D with thiazide-like diuretic when available	TĂNG LIỀU (Lên liều chuẩn) HOẶC PHỐI HỢP 3 THUỐC (Ưu tiên A + C + D: Thiazide-like nếu có)	\N	\N	{"action_type": "INCREASE_DOSE_OR_THREE_DRUG_COMBINATION", "dose_strategy": "USUAL_DOSE_OR_ESCALATED_COMBINATION", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "preferred_combination": {"classes": ["A", "C", "D"], "diuretic_preference": "THIAZIDE_LIKE_IF_AVAILABLE"}, "requires_clinician_review": true, "next_medication_follow_up_stage": "ESCALATED_REGIMEN"}	\N	\N	\N	8	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
68bb79f1-675e-1a9d-c435-f31326d2adc0	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_LINK_ESCALATED_REGIMEN_TO_TREE_6	LINK	Tree 6: Drug combination	Cây 6: Phối hợp thuốc	\N	\N	\N	\N	drug-combination	\N	9	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
13be6ff9-6462-cca9-41e1-fe9acdf7a51a	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_MEDICATION_FOLLOW_UP_ESCALATED_REGIMEN	CONDITION	Follow-up after escalated regimen	Tái khám sau phác đồ điều trị đã tăng cường	{"op": "eq", "path": "input.medication_follow_up_stage", "value": "ESCALATED_REGIMEN"}	\N	\N	\N	\N	\N	10	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
e21c65b2-83fd-02e9-eeab-677744d0394d	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_ESCALATED_REGIMEN_BP_TARGET_REACHED	CONDITION	Blood pressure target reached	HA đã đạt đích điều trị	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"}, {"op": "lt", "path": "input.current_clinic_dbp", "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}	\N	\N	\N	\N	\N	11	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
82babd78-5e41-3189-c818-f57ddc5c401a	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_ESCALATED_REGIMEN_BP_TARGET_NOT_REACHED	CONDITION	Blood pressure target not reached	HA chưa đạt đích điều trị	{"not": {"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"}, {"op": "lt", "path": "input.current_clinic_dbp", "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}}	\N	\N	\N	\N	\N	13	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
de0def41-cd3e-8156-7917-89ee6d7aac51	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_INF_DIFFICULT_TO_CONTROL_HYPERTENSION	INFERENCE	Difficult-to-control hypertension	THA KHÓ KIỂM SOÁT (KKS)	\N	{"treatment": {"status": "DIFFICULT_TO_CONTROL_HYPERTENSION"}}	\N	\N	\N	\N	14	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
ac3d43b2-11f0-f354-4c0f-ed81917af056	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_LINK_DIFFICULT_TO_CONTROL_TO_RESISTANT_HYPERTENSION	LINK	Resistant hypertension	Cây 14: THA Kháng Trị	\N	\N	\N	\N	resistant-hypertension	\N	15	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
fd6a45b1-06c0-9242-a3cb-e24239e22545	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_INITIAL_TREATMENT_ENCOUNTER	CONDITION	Initial treatment-selection encounter	Khám chọn chiến lược điều trị ban đầu	{"op": "eq", "path": "input.is_medication_follow_up", "value": false}	\N	\N	\N	\N	\N	16	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
ee91fd5f-c382-4b05-428d-082fb3dd2a4c	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_TWO_DRUG_TREATMENT_ELIGIBILITY	CONDITION	High-normal BP with high risk or comorbidity, or clinic BP at or above 140/90 mmHg	HABTC + nguy cơ cao/bệnh đồng mắc hoặc THA >= 140/90	{"any": [{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}, {"op": "eq", "path": "context.risk.level", "value": "HIGH"}]}, {"op": "eq", "path": "input.has_coronary_artery_disease", "value": true}, {"op": "eq", "path": "input.has_type_2_diabetes", "value": true}, {"op": "eq", "path": "input.has_heart_failure", "value": true}, {"op": "eq", "path": "input.has_ckd", "value": true}, {"op": "gte", "path": "input.current_clinic_sbp", "value": 140}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	17	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
c2ecd9d5-6085-75cd-7e11-2eb129f1b06e	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_ACTION_INITIAL_TWO_DRUG_COMBINATION	ACTION	Use two available medicines, from low dose to usual dose	PHỐI HỢP 2 THUỐC SẴN CÓ: Từ liều thấp đến liều thông thường	\N	\N	{"action_type": "INITIAL_TWO_DRUG_COMBINATION", "dose_strategy": "LOW_TO_USUAL_DOSE", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "requires_clinician_review": true, "next_medication_follow_up_stage": "INITIAL_REGIMEN"}	\N	\N	\N	18	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
c7a3b86a-95cb-9fe8-0e5b-39cb6e6ca392	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_LINK_INITIAL_TWO_DRUG_TO_TREE_6	LINK	Tree 6: Drug combination	Cây 6: Phối hợp thuốc	\N	\N	\N	\N	drug-combination	\N	19	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
38ce5860-b693-4151-ad13-dc7c2ae38f8e	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_HABTC_LOW_OR_MEDIUM_RISK	CONDITION	High-normal BP with low or intermediate risk	HABTC + nguy cơ thấp/TB	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}, {"any": [{"op": "eq", "path": "context.risk.level", "value": "LOW"}, {"op": "eq", "path": "context.risk.level", "value": "MEDIUM"}]}]}	\N	\N	\N	\N	\N	20	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
619dadfb-5f0d-d2e4-bc1f-ea5f22452602	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_C_MONOTHERAPY_ELIGIBILITY	CONDITION	Persistent high-normal BP after lifestyle management, age 80 or older, or frailty syndrome	HABTC không đạt mục tiêu sau thay đổi lối sống hoặc tuổi >= 80 hoặc hội chứng lão hóa	{"any": [{"op": "eq", "path": "input.is_lifestyle_follow_up", "value": true}, {"op": "gte", "path": "input.age", "value": 80}, {"op": "eq", "path": "input.has_frailty_syndrome", "value": true}]}	\N	\N	\N	\N	\N	21	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
83e7a716-298f-e77b-8869-9f273f1fb5b2	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_ACTION_CONSIDER_MONOTHERAPY	ACTION	Consider monotherapy: A (ACE inhibitor/ARB), B, C (calcium-channel blocker), or D (thiazide-like diuretic)	Xem xét ĐƠN TRỊ LIỆU: A (ƯCMC/CTTA), B, C (CKCa), hoặc D (Lợi tiểu Thiazide-like)	\N	\N	{"action_type": "CONSIDER_MONOTHERAPY", "drug_options": [{"class": "A", "description": "ACE inhibitor or ARB"}, {"class": "B", "description": "Beta-blocker", "requires_indication": true}, {"class": "C", "description": "Calcium-channel blocker"}, {"class": "D", "description": "Thiazide-like diuretic"}], "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "requires_clinician_review": true, "next_medication_follow_up_stage": "INITIAL_REGIMEN", "beta_blocker_requires_indication": true}	\N	\N	\N	22	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
1b836c93-2ca3-ccaf-ada5-ab9585830572	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_LINK_MONOTHERAPY_TO_TREE_6	LINK	Tree 6: Drug combination	Cây 6: Phối hợp thuốc	\N	\N	\N	\N	drug-combination	\N	23	2026-06-27 16:01:18.770793+00	2026-06-27 16:01:18.770793+00
22908966-252c-f62a-b264-bd7bd917b22c	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_END_MAINTAIN_REGIMEN	END	Continue monitoring and maintain regimen	Tiếp tục theo dõi và duy trì phác đồ	\N	\N	{"action_type": "MAINTAIN_CURRENT_REGIMEN", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "next_medication_follow_up_stage": "INITIAL_REGIMEN"}	\N	\N	\N	6	2026-06-27 16:01:18.770793+00	2026-06-28 04:53:28.115396+00
3ce3bd7c-f086-2a3b-c594-4d18cf02a7b2	e7ffabdc-c629-b367-585c-5c081b7e3ee5	T4_END_CONTINUE_MONITORING	END	Continue monitoring and maintain regimen	Tiếp tục theo dõi và duy trì phác đồ	\N	\N	{"action_type": "CONTINUE_MONITORING", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "next_medication_follow_up_stage": "ESCALATED_REGIMEN"}	\N	\N	\N	12	2026-06-27 16:01:18.770793+00	2026-06-28 04:53:28.115396+00
914f793f-2376-a2c1-dddb-33614c13d6bb	5be98c95-06f2-e474-21d9-cb52308e0455	T5_START_BP_AND_AGE_INFORMATION	START	Patient blood pressure and age information	Thông tin huyết áp bệnh nhân và tuổi	\N	\N	\N	\N	\N	\N	1	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
74f3cdc3-0390-aa3d-5f21-9d8128a6f3d7	5be98c95-06f2-e474-21d9-cb52308e0455	T5_GLOBAL_BP_TARGET_OVERRIDE_NOTE	GLOBAL	Comorbidities may have their own treatment target and override Tree 3 general target. Applies to every BP-target achievement check.	Nếu có bệnh đồng mắc thì có thể bệnh đồng mắc sẽ có đích điều trị riêng và override đích điều trị general của cây 3. Áp dụng cho mọi node condition check HA đã đạt đích điều trị hay chưa	\N	\N	\N	{"applies_to": ["T5_C_INITIAL_REGIMEN_BP_TARGET_REACHED", "T5_C_INITIAL_REGIMEN_BP_TARGET_NOT_REACHED", "T5_C_ESCALATED_REGIMEN_BP_TARGET_REACHED", "T5_C_ESCALATED_REGIMEN_BP_TARGET_NOT_REACHED"], "target_path": "context.treatment.bp_target", "override_rule": "MODIFIER_TREE_TARGET_OVERRIDES_TREE_3_TARGET", "comparison_contract": {"systolic_input_path": "input.current_clinic_sbp", "diastolic_input_path": "input.current_clinic_dbp", "systolic_target_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg", "diastolic_target_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}}	\N	\N	2	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
7c65f813-54a4-e49b-6761-998010679793	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_IS_MEDICATION_FOLLOW_UP	CONDITION	Medication follow-up visit	Tái khám sau điều trị thuốc	{"op": "eq", "path": "input.is_medication_follow_up", "value": true}	\N	\N	\N	\N	\N	3	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
cad9430a-f29b-3654-69d2-6522e78fd10b	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_MEDICATION_FOLLOW_UP_INITIAL_REGIMEN	CONDITION	Follow-up after initial regimen	Tái khám sau phác đồ điều trị ban đầu	{"op": "eq", "path": "input.medication_follow_up_stage", "value": "INITIAL_REGIMEN"}	\N	\N	\N	\N	\N	4	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
98a3e03c-3fe0-aefc-fa04-b34573372eab	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_INITIAL_REGIMEN_BP_TARGET_REACHED	CONDITION	Blood pressure target reached	HA đã đạt đích điều trị	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"}, {"op": "lt", "path": "input.current_clinic_dbp", "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}	\N	\N	\N	\N	\N	5	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
0380de58-e79b-5348-28bb-b502643bdf13	5be98c95-06f2-e474-21d9-cb52308e0455	T5_END_INITIAL_REGIMEN_TARGET_REACHED	END	Continue monitoring and maintain regimen	Tiếp tục theo dõi và duy trì phác đồ	\N	\N	{"action_type": "CONTINUE_MONITORING_AND_MAINTAIN_REGIMEN", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "next_medication_follow_up_stage": "INITIAL_REGIMEN"}	\N	\N	\N	6	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
35bc4ca0-b4e1-eb55-4aec-24103ff89e87	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_INITIAL_REGIMEN_BP_TARGET_NOT_REACHED	CONDITION	Blood pressure target not reached	HA chưa đạt đích điều trị	{"not": {"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"}, {"op": "lt", "path": "input.current_clinic_dbp", "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}}	\N	\N	\N	\N	\N	7	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
5c6c7d16-4242-c6df-8601-559b06c8df6e	5be98c95-06f2-e474-21d9-cb52308e0455	T5_ACTION_FIXED_DOSE_THREE_DRUG_COMBINATION	ACTION	Fixed-dose three-drug combination in one pill: A + C + D	VIÊN PHỐI HỢP 3 THUỐC (1 viên): A+C+D	\N	\N	{"classes": ["A", "C", "D"], "pill_count": 1, "action_type": "FIXED_DOSE_THREE_DRUG_COMBINATION", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "fixed_dose_combination": true, "requires_clinician_review": true, "next_medication_follow_up_stage": "ESCALATED_REGIMEN"}	\N	\N	\N	8	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
58b9fa36-356d-7ed4-f695-88d943509db5	5be98c95-06f2-e474-21d9-cb52308e0455	T5_LINK_THREE_DRUG_TO_TREE_6	LINK	Tree 6: Drug combination	Cây 6: Phối hợp thuốc	\N	\N	\N	\N	drug-combination	\N	9	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
329f1d88-b1c0-0dfb-e483-04e44d7a8cb7	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_MEDICATION_FOLLOW_UP_ESCALATED_REGIMEN	CONDITION	Follow-up after escalated regimen	Tái khám sau phác đồ điều trị đã tăng cường	{"op": "eq", "path": "input.medication_follow_up_stage", "value": "ESCALATED_REGIMEN"}	\N	\N	\N	\N	\N	10	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
54aa834e-dedb-0126-4412-13764f18e243	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_ESCALATED_REGIMEN_BP_TARGET_REACHED	CONDITION	Blood pressure target reached	HA đã đạt đích điều trị	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"}, {"op": "lt", "path": "input.current_clinic_dbp", "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}	\N	\N	\N	\N	\N	11	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
75c0a05c-7687-2266-8952-473fe7b86d06	5be98c95-06f2-e474-21d9-cb52308e0455	T5_END_ESCALATED_REGIMEN_TARGET_REACHED	END	Continue monitoring and maintain regimen	Tiếp tục theo dõi và duy trì phác đồ	\N	\N	{"action_type": "CONTINUE_MONITORING_AND_MAINTAIN_REGIMEN", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "next_medication_follow_up_stage": "ESCALATED_REGIMEN"}	\N	\N	\N	12	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
ef355d74-058e-da5d-ee4f-f98a16f6b826	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_ESCALATED_REGIMEN_BP_TARGET_NOT_REACHED	CONDITION	Blood pressure target not reached	HA chưa đạt đích điều trị	{"not": {"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg"}, {"op": "lt", "path": "input.current_clinic_dbp", "value_from_path": "context.treatment.bp_target.dbp.upper_exclusive_mmhg"}]}}	\N	\N	\N	\N	\N	13	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
2d8f35fd-3fe7-7869-49f5-bc9cbb752ea1	5be98c95-06f2-e474-21d9-cb52308e0455	T5_INF_RESISTANT_HYPERTENSION_TREATMENT_STEP	INFERENCE	Resistant hypertension: add MRA, another diuretic, alpha-blocker, or beta-blocker; increase to two pills	THA KHÁNG TRỊ: Thêm MRA, Lợi tiểu khác, chẹn alpha hoặc beta (Lên 2 viên)	\N	{"treatment": {"status": "RESISTANT_HYPERTENSION", "pill_count": 2, "additional_options": ["MRA", "ANOTHER_DIURETIC", "ALPHA_BLOCKER", "BETA_BLOCKER"]}}	\N	\N	\N	\N	14	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
30170f69-9377-9632-126e-7bb8214811a2	5be98c95-06f2-e474-21d9-cb52308e0455	T5_LINK_RESISTANT_HYPERTENSION	LINK	Resistant hypertension	Cây 14: THA Kháng Trị	\N	\N	\N	\N	resistant-hypertension	\N	15	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
eda6c713-9824-ea0b-c265-dcbbcde38fe4	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_INITIAL_TREATMENT_ENCOUNTER	CONDITION	Initial treatment-selection encounter	Khám chọn chiến lược điều trị ban đầu	{"op": "eq", "path": "input.is_medication_follow_up", "value": false}	\N	\N	\N	\N	\N	16	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
fd5f90fd-3e68-39f1-46ab-441095c17fd8	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_TWO_DRUG_TREATMENT_ELIGIBILITY	CONDITION	High-normal BP with high risk or comorbidity, or clinic BP at or above 140/90 mmHg	HABTC + nguy cơ cao/bệnh đồng mắc hoặc THA >= 140/90	{"any": [{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}, {"op": "eq", "path": "context.risk.level", "value": "HIGH"}]}, {"op": "eq", "path": "input.has_coronary_artery_disease", "value": true}, {"op": "eq", "path": "input.has_type_2_diabetes", "value": true}, {"op": "eq", "path": "input.has_heart_failure", "value": true}, {"op": "eq", "path": "input.has_ckd", "value": true}, {"op": "gte", "path": "input.current_clinic_sbp", "value": 140}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	17	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
c3ba5d02-6f67-3af6-016c-6d9649bed79b	5be98c95-06f2-e474-21d9-cb52308e0455	T5_ACTION_FIXED_DOSE_TWO_DRUG_COMBINATION	ACTION	Fixed-dose two-drug combination in one pill: A + C or A + D; start at half the usual dose	VIÊN PHỐI HỢP 2 THUỐC (1 viên): A+C hoặc A+D (Khởi đầu 1/2 liều thông thường)	\N	\N	{"pill_count": 1, "action_type": "FIXED_DOSE_TWO_DRUG_COMBINATION", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "combination_options": [["A", "C"], ["A", "D"]], "fixed_dose_combination": true, "requires_clinician_review": true, "next_medication_follow_up_stage": "INITIAL_REGIMEN", "starting_dose_fraction_of_usual": 0.5}	\N	\N	\N	18	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
f9fd109c-05a1-f132-af67-590edb731f71	5be98c95-06f2-e474-21d9-cb52308e0455	T5_LINK_INITIAL_TWO_DRUG_TO_TREE_6	LINK	Tree 6: Drug combination	Cây 6: Phối hợp thuốc	\N	\N	\N	\N	drug-combination	\N	19	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
aa012536-8918-710b-0209-3b1da478cd70	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_HABTC_LOW_OR_MEDIUM_RISK	CONDITION	High-normal BP with low or intermediate risk	HABTC + nguy cơ thấp/TB	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}, {"any": [{"op": "eq", "path": "context.risk.level", "value": "LOW"}, {"op": "eq", "path": "context.risk.level", "value": "MEDIUM"}]}]}	\N	\N	\N	\N	\N	20	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
94a026fb-28af-8d31-f0d7-f05073711e3c	5be98c95-06f2-e474-21d9-cb52308e0455	T5_C_MONOTHERAPY_ELIGIBILITY	CONDITION	Persistent high-normal BP after lifestyle management, age 80 or older, or frailty syndrome	HABTC không đạt mục tiêu sau thay đổi lối sống hoặc tuổi >= 80 hoặc hội chứng lão hóa	{"any": [{"op": "eq", "path": "input.is_lifestyle_follow_up", "value": true}, {"op": "gte", "path": "input.age", "value": 80}, {"op": "eq", "path": "input.has_frailty_syndrome", "value": true}]}	\N	\N	\N	\N	\N	21	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
88a2ff70-ecc2-23e0-97e7-ebc3213188cd	5be98c95-06f2-e474-21d9-cb52308e0455	T5_ACTION_CONSIDER_MONOTHERAPY_ONE_PILL	ACTION	Consider monotherapy in one pill: A (ACE inhibitor/ARB/ARNI), B, C (calcium-channel blocker), or D (thiazide-like diuretic)	Xem xét ĐƠN TRỊ LIỆU (1 viên): A (ƯCMC/CTTA/ARNI), B, C (CKCa), hoặc D (Lợi tiểu Thiazide-like)	\N	\N	{"pill_count": 1, "action_type": "CONSIDER_MONOTHERAPY", "drug_options": [{"class": "A", "description": "ACE inhibitor, ARB, or ARNI"}, {"class": "B", "description": "Beta-blocker", "requires_indication": true}, {"class": "C", "description": "Calcium-channel blocker"}, {"class": "D", "description": "Thiazide-like diuretic"}], "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true, "requires_clinician_review": true, "next_medication_follow_up_stage": "INITIAL_REGIMEN", "beta_blocker_requires_indication": true}	\N	\N	\N	22	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
61c0ccb8-5d7d-d019-86c6-9a94b712064e	5be98c95-06f2-e474-21d9-cb52308e0455	T5_LINK_MONOTHERAPY_TO_TREE_6	LINK	Tree 6: Drug combination	Cây 6: Phối hợp thuốc	\N	\N	\N	\N	drug-combination	\N	23	2026-06-28 04:55:48.876854+00	2026-06-28 04:55:48.876854+00
\.

COPY public.decision_edges ("id", "from_node_id", "to_node_id", "traversal_order") FROM stdin;
10cd6b1a-81ba-40c2-aead-22283d34c033	854590f4-9e9c-3158-47af-43695e29611e	af62ea0d-827f-488d-9218-ffb2d0e4e0b0	1
d969c060-cb00-4068-a9d5-06762ce7df73	854590f4-9e9c-3158-47af-43695e29611e	8a14e0bd-3f41-4672-9b28-f236d56cfe99	2
81fe5658-af2c-4b1f-bab4-3ca14dd44965	af62ea0d-827f-488d-9218-ffb2d0e4e0b0	8a526e4b-cfd9-4b7b-8fc5-06c18cad2dd8	1
e683dce1-92d1-420a-8493-72f55ae08fe6	8a14e0bd-3f41-4672-9b28-f236d56cfe99	a04f0087-1e67-7368-d086-d6fcccdaedb1	1
9a624eb5-da84-4ecf-aec4-2b84969caf3f	8a14e0bd-3f41-4672-9b28-f236d56cfe99	6538e358-5110-978e-fdeb-9f9163930524	2
1bff8c2b-2e3e-c7cd-a976-7df20869808e	a04f0087-1e67-7368-d086-d6fcccdaedb1	bfbb746b-d5ff-6d27-a5e6-5376a31d2841	1
3083677e-0c15-2332-6c31-a8400c4cddb7	bfbb746b-d5ff-6d27-a5e6-5376a31d2841	b8778eca-3e96-47d7-fc9d-c8ff3c68e3f7	1
c3924e37-5b4e-9c17-42e1-061c4d794d41	6538e358-5110-978e-fdeb-9f9163930524	7bc03fb5-45fa-4d03-6732-b8f4d0fb67d8	1
34969d9c-0588-f37f-1580-4ae44845ecfa	6538e358-5110-978e-fdeb-9f9163930524	8902d0f7-7e45-05f3-57b4-3cbab88a2766	2
971ab6a9-963a-bfa5-87c8-7e96ffe3de17	7bc03fb5-45fa-4d03-6732-b8f4d0fb67d8	82e84f39-0a8b-ed8e-14f1-78a9db7c991c	1
22471da9-259f-a668-6dcb-a65b40d881bb	7bc03fb5-45fa-4d03-6732-b8f4d0fb67d8	c4c213f6-cc3f-b126-965c-7cc29a920737	2
3b34888b-3452-3f4d-4a4e-243a017a0bf6	7bc03fb5-45fa-4d03-6732-b8f4d0fb67d8	f61c1dae-7953-1d8c-7397-3d1014a9a56e	3
f29e244d-e382-3fa7-4533-2c3f3c85651d	82e84f39-0a8b-ed8e-14f1-78a9db7c991c	b252d144-2b2d-17d1-97d6-ebe8419d6347	1
c2d3f2c8-035d-ca82-bffe-a7c094fa74b8	b252d144-2b2d-17d1-97d6-ebe8419d6347	024340ba-69f5-8b5f-ee24-1a8ac453af3f	1
6d9aa590-1d00-b46f-271b-de078434f164	024340ba-69f5-8b5f-ee24-1a8ac453af3f	993144cf-893d-ef87-efb3-a1adb2aff1b7	1
efc4722c-47c6-9f90-f2b4-bab6714e3ccb	024340ba-69f5-8b5f-ee24-1a8ac453af3f	6ef8e7ef-9791-2d7a-de78-92bcf0157fd3	2
b354c1ef-d3ad-67f5-45be-da8273e5bcc3	993144cf-893d-ef87-efb3-a1adb2aff1b7	4156b708-5a62-f921-c8f8-c4fcc66ac355	1
63f50904-3209-c3fa-950f-d0786bfdda98	4156b708-5a62-f921-c8f8-c4fcc66ac355	b96559b4-f6fe-70e4-1704-7ea3325dbd6e	1
53f35a1e-7458-76e1-832b-935bc4fd2370	6ef8e7ef-9791-2d7a-de78-92bcf0157fd3	f71ef072-f987-4bdf-74ea-9831561c847d	1
ce5527f8-130f-c5db-bee2-4b62dc8e9f38	f71ef072-f987-4bdf-74ea-9831561c847d	392d4dcf-3a87-5994-7a28-319df16913e1	1
8791f3f8-e336-2065-645b-db6a0559a089	c4c213f6-cc3f-b126-965c-7cc29a920737	50183af5-180d-684d-ca85-0a39375047f6	1
44bcc9df-8c5c-9fc1-4f24-5b6dbad382fe	50183af5-180d-684d-ca85-0a39375047f6	3b3d3e10-8020-0e11-85ab-694d7e2606d7	1
5ad63253-6b70-3261-dd9b-9c36dd15fb7f	f61c1dae-7953-1d8c-7397-3d1014a9a56e	82622d63-8358-42e4-5396-5b0de98cb992	1
be3fd640-7aaa-4e98-9278-5a8629f3ad26	82622d63-8358-42e4-5396-5b0de98cb992	71abd56d-80ba-11c6-f7f4-ea0fea899e94	1
294ca110-ffd5-a616-2561-5e153697db38	8902d0f7-7e45-05f3-57b4-3cbab88a2766	bc1e94e0-c24f-60dc-0183-55a69caf4364	1
e60e4993-264d-c0df-8d8e-a8a894669bed	8902d0f7-7e45-05f3-57b4-3cbab88a2766	0120ac75-acdf-48e0-db92-0d53f45198ad	2
413bddbc-cc6b-86e0-d3f7-70bfaac4a0fe	bc1e94e0-c24f-60dc-0183-55a69caf4364	ae850596-a036-f3d1-021b-462917f62055	1
d1985cd0-c8e0-a599-8730-cc245faa5484	bc1e94e0-c24f-60dc-0183-55a69caf4364	15b24644-6822-aeec-5228-6c66fe4e4c34	2
71912611-6079-ce3a-34da-6db734b8e29c	ae850596-a036-f3d1-021b-462917f62055	f75e07aa-b64c-f05a-3f40-beb41b32da8b	1
6979e174-cc53-9fc1-ea4f-c38a160a8531	ae850596-a036-f3d1-021b-462917f62055	a28ba521-9617-68bd-700b-bd1ea531ef83	2
fb0952c9-c9e6-3cf8-d1c7-9df2adb3d645	a28ba521-9617-68bd-700b-bd1ea531ef83	e76d51eb-d7f0-3ac8-9f48-bd5e57eb2e0c	1
7769074d-14da-893b-6e83-ff19ccc5f66b	e76d51eb-d7f0-3ac8-9f48-bd5e57eb2e0c	75763523-d572-842e-ea01-b32478244bd0	1
dc2a98d3-2e41-c419-be44-adf43ac34f4e	f75e07aa-b64c-f05a-3f40-beb41b32da8b	056a6e9f-05e4-2371-5783-3ba963d00c8b	1
f65198ef-9306-46f4-c4f8-9ba2b2e95621	f75e07aa-b64c-f05a-3f40-beb41b32da8b	8c055fa2-1e69-33ea-7281-0d0e7fc668d4	2
428882a0-6efe-9504-8e4d-6043a7748a66	f75e07aa-b64c-f05a-3f40-beb41b32da8b	dcdfb9e6-8424-7c53-10c2-c59c612d0016	3
66227e20-c467-90c0-2680-d0330f7a3354	056a6e9f-05e4-2371-5783-3ba963d00c8b	ad79523f-69d2-df24-dfe2-d932d2cebd3b	1
05d179ed-4a52-b494-54fb-db329b5f7a69	ad79523f-69d2-df24-dfe2-d932d2cebd3b	9c646ad6-5544-914d-f5b4-272ff4613e77	1
3cca1055-3084-ae2a-07f8-f7c1bc9e0eb6	9c646ad6-5544-914d-f5b4-272ff4613e77	b01e9357-c88c-04f0-365b-f6f88b91cd45	1
092dbd9e-c700-d7b2-e8c2-1afff966c53e	9c646ad6-5544-914d-f5b4-272ff4613e77	889df3c8-b8f3-d06b-8122-5e868cdee57c	2
980287e6-7804-847b-c15f-e01e08737535	b01e9357-c88c-04f0-365b-f6f88b91cd45	6b917a54-139e-9612-88fb-d7a07f13d854	1
1daaab82-87cf-ed2a-20d2-1436dd36cedc	6b917a54-139e-9612-88fb-d7a07f13d854	f97ae77a-ca30-c1be-b1fe-fddf13b59dc1	1
f26ae75e-f9c8-f017-2ce4-30dac3e908ac	889df3c8-b8f3-d06b-8122-5e868cdee57c	41df521d-823e-bbeb-ed4b-850f86b212a7	1
764dc012-e596-887e-2cf7-b7cc19711e99	41df521d-823e-bbeb-ed4b-850f86b212a7	447978a9-d6cd-ea05-cd0c-819bae969c8f	1
0b2f76c1-59de-53d4-499d-efdf690592e1	8c055fa2-1e69-33ea-7281-0d0e7fc668d4	e2999392-875c-8b00-231c-c0d860198d0d	1
d0d4c4a9-4ea1-7318-a39c-19664c1741d3	e2999392-875c-8b00-231c-c0d860198d0d	3161f04a-b5d9-012f-fa56-a8ea416aedb1	1
9c146f21-aea7-45ba-6612-ece2fb0c66ce	dcdfb9e6-8424-7c53-10c2-c59c612d0016	e246a50d-938e-801a-9d10-fda5e54e3409	1
09300c66-681b-9a47-cced-700296248703	e246a50d-938e-801a-9d10-fda5e54e3409	581f7d7a-70fe-1ede-6b51-6a6f2a8e3dd1	1
dfe52421-d8ff-0d71-47c6-fa1c50afa64e	15b24644-6822-aeec-5228-6c66fe4e4c34	dee9eca4-41b6-8283-fb90-22d986a02545	1
93d4088a-07a1-ca1b-9804-c151ef1b7b79	15b24644-6822-aeec-5228-6c66fe4e4c34	d65ada75-d44e-f28b-4538-d5b8f7ba7d88	2
effddc9e-9424-0f6c-55f0-191470a0acc6	dee9eca4-41b6-8283-fb90-22d986a02545	150b12aa-ea76-4ef4-4ae9-72e8b3427d57	1
0a8db356-e6f0-bf71-df6b-aabd045c8eac	d65ada75-d44e-f28b-4538-d5b8f7ba7d88	901b8971-4490-05eb-0fb4-7b009bb8929e	1
778781a9-73a2-5f7a-1f58-3c491beb0f76	0120ac75-acdf-48e0-db92-0d53f45198ad	2ccf9a48-c739-b8c8-3ff3-58e07085dada	1
48989122-1d6a-4716-1868-76f249617092	2ccf9a48-c739-b8c8-3ff3-58e07085dada	0da5ee04-82fe-8681-957d-0ab16678ad1f	1
9c6b9562-aef2-d675-072e-108407f92f62	2ccf9a48-c739-b8c8-3ff3-58e07085dada	cd0e9072-3ea2-ae16-3d22-9c27c95e0bf5	2
952ff6a2-2672-9711-d972-6b5767413049	2ccf9a48-c739-b8c8-3ff3-58e07085dada	578ce908-3403-1df1-378a-79136a9eedb3	3
a2ece51c-4e7d-b61e-47ed-3237c63eca64	0da5ee04-82fe-8681-957d-0ab16678ad1f	e9270ac1-7ccd-40d7-92d4-a8e4d065f611	1
b42e06c4-7380-0d8f-3661-97544cfcbb56	e9270ac1-7ccd-40d7-92d4-a8e4d065f611	67ab35c9-30ea-85e4-ffb8-1a15cfb906e1	1
7ad6d701-9274-32a1-e293-b68fc4dd165a	e9270ac1-7ccd-40d7-92d4-a8e4d065f611	60c1e457-4b7d-614b-8ef7-61506403ef5f	2
75922197-ea80-da5c-c403-2554bfd7e888	67ab35c9-30ea-85e4-ffb8-1a15cfb906e1	42a86643-3a3d-4e13-e45f-c160a278e0b9	1
a8ba8ec1-8fbe-2dfa-9208-55650393604a	42a86643-3a3d-4e13-e45f-c160a278e0b9	da558a72-f0f4-eb91-e3b1-e823f6b4054b	1
56c35a70-3380-20a3-9bee-50d97423d558	60c1e457-4b7d-614b-8ef7-61506403ef5f	1bfbc013-8b60-85f8-0e6f-16bb8b2e08f3	1
184ed309-1c67-9ada-5453-28ae7a6ebc8b	1bfbc013-8b60-85f8-0e6f-16bb8b2e08f3	e13a27c1-391e-20de-a536-a24514514629	1
6d85e9fe-f59e-5a5b-1bf4-f17b96bc666b	cd0e9072-3ea2-ae16-3d22-9c27c95e0bf5	28c71bb1-a8df-b8d0-bc32-06c0e5006228	1
7a72ec6b-d038-74c4-6e83-620ee5be96ed	28c71bb1-a8df-b8d0-bc32-06c0e5006228	8130a5fc-4e3c-edb9-6a46-d1eb994e3efd	1
24ac7da9-9c3b-8cd0-ae14-438b81f12f34	578ce908-3403-1df1-378a-79136a9eedb3	c0a64934-faa3-7403-22a9-8db45fb883d9	1
7a595f93-e07c-4990-e493-35e652671be4	4ef64653-acf3-b7b9-e6fc-8e594a02967a	ebd2cf1d-a6d6-e606-f1b7-d83ae2028e4e	1
59404c46-a828-3626-69ed-742e6d29ac7e	ebd2cf1d-a6d6-e606-f1b7-d83ae2028e4e	16af59eb-1c84-0708-9259-f351eeb59ae5	1
1be514ac-f43e-544c-d199-37a62a20bb4a	ec404ee2-7221-4ad8-ca64-c9e9d5363d97	8ceb98a6-3e3f-0fce-ab0d-6b746ac16f7a	3
d4b8e8ac-d57e-fdcf-998f-7e1329895b03	ec404ee2-7221-4ad8-ca64-c9e9d5363d97	3f0e2f17-4775-0538-ce10-6f11dc621c84	2
32a5ae42-e246-66fd-5e4a-ee8122bfd0cf	ec404ee2-7221-4ad8-ca64-c9e9d5363d97	7ba7c905-6d36-3414-e4c5-0116b03bcdbf	1
9513c8ad-8705-3e2c-1da7-ed614f3bb286	7ba7c905-6d36-3414-e4c5-0116b03bcdbf	9dc9020e-d70e-1ebe-f2ea-b390b5346c33	1
a350d472-69f2-9a41-c648-f422ecdc3ed2	9dc9020e-d70e-1ebe-f2ea-b390b5346c33	230600f6-0c3f-ca8c-4f84-7a449004be41	1
0ec9f145-3bf2-02b9-3525-ffc0938f6c0c	3f0e2f17-4775-0538-ce10-6f11dc621c84	23276de5-636d-3312-1636-1dc4f4b6b969	1
cec99beb-0f35-65d0-ea93-7263cbb79cf2	23276de5-636d-3312-1636-1dc4f4b6b969	48152ce5-628b-7448-66f0-833128715fc9	1
af8036f1-0ed2-7b13-a548-21f5ad89b582	8ceb98a6-3e3f-0fce-ab0d-6b746ac16f7a	165c4ea4-8261-4117-9efb-83084a9b3e2a	3
c2cddbd9-5c3f-ed56-d3f9-9ad80925ba99	8ceb98a6-3e3f-0fce-ab0d-6b746ac16f7a	8058aebe-6375-cafe-b718-d5df20ac85c9	2
fc191456-bf3d-1e48-cd96-36731dfad782	8ceb98a6-3e3f-0fce-ab0d-6b746ac16f7a	98cee07d-28ca-dcc6-384c-02c30b0b50fe	1
097a699c-da3a-e936-6dd0-62d96ceeef62	98cee07d-28ca-dcc6-384c-02c30b0b50fe	3ed68451-bfad-5d50-de50-7c968df606af	2
9132bc0b-fa63-0f8b-b465-9e2bff3251b0	98cee07d-28ca-dcc6-384c-02c30b0b50fe	ba1a1c44-b0fd-499d-144c-ac54731ba62d	1
7dea9443-6a0a-9ff1-2a51-d4fdbc68e2ab	8058aebe-6375-cafe-b718-d5df20ac85c9	20a7535d-1695-4d68-0048-c86dc1101221	2
718cb933-e7dc-fec2-5096-716150f25a7e	8058aebe-6375-cafe-b718-d5df20ac85c9	fb7c62d1-4d86-0013-e05e-4f862b4a4d8a	1
535567c6-2d9a-df76-0dd9-0e09231723b6	165c4ea4-8261-4117-9efb-83084a9b3e2a	4ef64653-acf3-b7b9-e6fc-8e594a02967a	2
7f0ec247-a428-3fcb-1eaf-624ab360c43a	165c4ea4-8261-4117-9efb-83084a9b3e2a	d77ec0d8-f756-6377-6f0a-e8cb2f5e8a15	1
8c0d33d1-69f8-3ffd-4a91-2b2dfb1ebeab	ba1a1c44-b0fd-499d-144c-ac54731ba62d	b492a11d-3566-318f-3269-e04bc11d09fa	1
488bbae7-24e3-3bad-c2be-2c286ece183e	b492a11d-3566-318f-3269-e04bc11d09fa	ca8f6031-35f3-7851-80f9-dc274edf0f1d	1
4b7b2d3a-1dce-eb66-3187-ee4d5129e705	3ed68451-bfad-5d50-de50-7c968df606af	03f895d0-ee99-19d6-58c3-35b49042dda3	1
81a419d4-7f40-47be-b9fe-12c1fb81b194	03f895d0-ee99-19d6-58c3-35b49042dda3	943686dd-9e22-48ef-9787-989530941b54	1
44a2cb10-680e-db04-c115-9a0ec0bd8f96	fb7c62d1-4d86-0013-e05e-4f862b4a4d8a	27c4d74f-163b-4131-11d4-9597e6404738	1
800a8f0c-5954-973f-0b8f-a25c783180bb	27c4d74f-163b-4131-11d4-9597e6404738	0365dd82-cd8a-5d80-5236-3ef0f7fe85ac	1
9b96b74c-f961-de5c-5005-bc92f335ed33	20a7535d-1695-4d68-0048-c86dc1101221	d186b9cc-2b53-3662-e66d-655fff3ba7c6	1
450aa77b-b85b-982b-bb6a-53aa27ae8beb	d186b9cc-2b53-3662-e66d-655fff3ba7c6	bc18f0a9-5f31-749d-19b1-b65596d769f9	1
0281eecb-d94e-0002-88b2-baf80e4ba6ec	d77ec0d8-f756-6377-6f0a-e8cb2f5e8a15	fc7fc2c0-c399-0786-26b1-836ef99c51c4	1
af4503ff-db60-5051-5705-3e366123f3ac	fc7fc2c0-c399-0786-26b1-836ef99c51c4	f568eca7-99d1-6a0a-db05-08b1ef7f342a	1
8ac61a34-c7ba-8317-9a02-bd808bd13c4e	b2658dcd-838f-ca57-50d3-0ad0e007dcc4	a8e8f94a-73e3-90e0-bb13-d5391d228a46	1
24ba355a-253e-a150-20df-850de2bf9f5a	b2658dcd-838f-ca57-50d3-0ad0e007dcc4	24dbca8b-981c-416b-e3c9-3189ff36c8d7	2
f8d871fa-a947-f09b-1aec-57906007a3c8	a8e8f94a-73e3-90e0-bb13-d5391d228a46	a568efbe-4123-a88c-7824-dce7c9f4744c	1
12f86a13-0918-4792-af21-1825f8ec70f2	a8e8f94a-73e3-90e0-bb13-d5391d228a46	86deea06-0fd7-f7d1-052f-80aadbd34f2d	2
aa3e7f7c-07f8-6a7a-c87f-26870234ada6	86deea06-0fd7-f7d1-052f-80aadbd34f2d	732bb6a9-f802-9e67-8377-bec03ab0ccab	1
0b1bb767-ce06-3c0c-7dbc-16563b8b33ac	732bb6a9-f802-9e67-8377-bec03ab0ccab	07c0033a-c673-f236-3f59-093f5e236863	1
d41dbf0e-1859-66c5-5ed3-014571d61ada	732bb6a9-f802-9e67-8377-bec03ab0ccab	38bf4156-78bc-b9f5-2bb4-3ad381e87a28	2
772a00da-612e-a7df-af77-77f2bfd1130c	24dbca8b-981c-416b-e3c9-3189ff36c8d7	7cee6dc2-7420-d2db-e172-43e3cb73ebf8	1
e861c69c-e649-f38e-6bfc-4cb31717fcaf	24dbca8b-981c-416b-e3c9-3189ff36c8d7	aac650db-813f-8d02-d74f-52d83aec84f9	2
e6398cd1-5a0d-0151-00c6-9ff1f01c6eb0	aac650db-813f-8d02-d74f-52d83aec84f9	95569744-0278-46a5-b937-6c519a461eec	1
d8f3ba4e-236d-0f63-5f28-4b76650a805f	95569744-0278-46a5-b937-6c519a461eec	4d190229-83b8-5716-5df3-ac5e80e502a0	1
64969dea-e925-b8e2-d1b1-7725e468f033	95569744-0278-46a5-b937-6c519a461eec	b7e4c349-510a-fc5e-2729-5a95584e8f6d	2
e3111be4-af9f-5f3d-2a89-00d1c5a9cf80	95569744-0278-46a5-b937-6c519a461eec	db629483-4764-0a45-10a7-56515b08c8be	3
46098767-77c9-e2ac-634a-6f43e975ada9	95569744-0278-46a5-b937-6c519a461eec	06acb6f1-4511-0d26-6ba7-19820b066b76	4
1f114dc1-48fe-0dda-eb8d-30efbaaf6ae8	b9153f61-98ce-673a-b1bf-9bcb80671d62	d61ccc11-d575-6482-9c9b-231f43424ab1	1
059c31d4-7b63-1336-8168-c6fe5486379c	b9153f61-98ce-673a-b1bf-9bcb80671d62	e9e05195-a8f6-b2bd-e31e-6cfa937d1d56	2
edf81cfa-84cb-6ec4-4c27-4d65a9febac0	d61ccc11-d575-6482-9c9b-231f43424ab1	c10efb3e-1efc-6aa1-e0c1-b2e799e2c77b	1
a8f2824d-4d1d-0896-2bd7-291b30107394	d61ccc11-d575-6482-9c9b-231f43424ab1	fc6394bc-6d70-5ab1-f750-1a26069ac9b7	2
410fe7bb-1ffc-3744-ae77-180577dceeba	e9e05195-a8f6-b2bd-e31e-6cfa937d1d56	d8ed1b7c-c4d6-ffab-aa92-f41a3acac47b	1
9758b265-bbd7-b704-734a-49b62e0160cb	e9e05195-a8f6-b2bd-e31e-6cfa937d1d56	e3a963b3-778c-bd6c-6346-31ef75b22c12	2
385f3a9d-3b2f-bd53-dba6-e8dd396a8896	e3a963b3-778c-bd6c-6346-31ef75b22c12	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	1
b429d36a-803f-d921-020d-003aa8f98790	fc6394bc-6d70-5ab1-f750-1a26069ac9b7	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	1
6a0d8c84-d5f7-f00d-cb49-fc969215a8d1	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	68fa1969-490f-f26f-97a2-9923fbd618e7	1
4628c36a-92d3-ae81-0e00-4feb514bde6f	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	87e3c582-d29b-2cf0-c6a0-19e728f05f05	2
1bb1c96c-cd99-4d08-dae5-f2bfcf75326d	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	33827fa5-414a-7753-525f-a350e9ab9532	3
3296256e-fda4-c9e9-47b8-6610f64ec10b	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	956d7df4-6501-0c1b-0bf0-78db627ce19e	4
1e1865a9-680a-ab84-7474-9b03f0123175	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	6d654d4f-aa3a-6835-0c2c-65b55413c439	5
dc265fb0-4440-3672-7040-caec51b2d872	a568efbe-4123-a88c-7824-dce7c9f4744c	0c92a137-09dd-cc40-8d65-a16871ae8176	3
652b8535-95fc-437d-92e5-be2f516ed890	a568efbe-4123-a88c-7824-dce7c9f4744c	d49ed998-c9d4-c06f-9859-ebd4459f4457	2
732a9fa5-2d95-39c4-a5fb-60cb82bef5b4	a568efbe-4123-a88c-7824-dce7c9f4744c	012c8740-0d0a-ffa9-93ff-41f19bf24ee7	1
cac9a75d-8d43-ef4e-9b68-9858a7b2285c	012c8740-0d0a-ffa9-93ff-41f19bf24ee7	cfb91d03-1e28-26a1-acc8-44e033cac052	1
b9e80076-4ba6-124c-dc52-296437ace7da	d49ed998-c9d4-c06f-9859-ebd4459f4457	0c92a137-09dd-cc40-8d65-a16871ae8176	1
5bddd1d5-4fc8-c798-dd82-6a0dc4fc126a	cfb91d03-1e28-26a1-acc8-44e033cac052	38bf4156-78bc-b9f5-2bb4-3ad381e87a28	2
1e33d0c7-202a-5bb2-6fb6-e4d7f9698cdb	cfb91d03-1e28-26a1-acc8-44e033cac052	07c0033a-c673-f236-3f59-093f5e236863	1
1a196840-07a3-79a4-e6cd-d6c03d0379d3	c10efb3e-1efc-6aa1-e0c1-b2e799e2c77b	314a95d2-649f-4168-ffca-5ae74bd586c4	1
11133cee-270a-50ef-bfaf-542c329386f0	d8ed1b7c-c4d6-ffab-aa92-f41a3acac47b	9261e551-a1e4-f52d-776f-256476cde602	1
7f2772c3-a498-a26b-e079-6d88039627c7	7cee6dc2-7420-d2db-e172-43e3cb73ebf8	1cd09c61-8f8a-ef32-ef53-eb47481b78c8	2
5be8ebfb-bbaf-e1a5-ff80-eb55d0445b6e	7cee6dc2-7420-d2db-e172-43e3cb73ebf8	24fd4dc9-e461-86fe-73ee-72f28c410793	1
5b6ba9f8-a257-d4ba-7941-ac12a453390d	24fd4dc9-e461-86fe-73ee-72f28c410793	95569744-0278-46a5-b937-6c519a461eec	1
fe2be24f-e103-4139-f66c-ba4dd3990d80	1cd09c61-8f8a-ef32-ef53-eb47481b78c8	b03048ca-27aa-09c2-bff4-ee361ac09378	1
d332d692-1252-eda4-e428-5cc56e0e53c4	1e4d5cba-38ba-630f-2597-8590c916e1d4	c8edac54-9f97-7fd4-3867-9e14861e3ba2	3
f9b829f1-805a-2c86-3f1e-e8104efce9e3	1e4d5cba-38ba-630f-2597-8590c916e1d4	377554d0-1f57-6179-b0ee-6f03230ff8b0	2
42da0175-1e8e-c682-98b5-6fbc7f006199	1e4d5cba-38ba-630f-2597-8590c916e1d4	b262908e-c083-362b-db10-0d10ca4ed024	1
992b78aa-2320-332c-439f-f06a7649ac75	377554d0-1f57-6179-b0ee-6f03230ff8b0	82d39f73-488c-3113-49e7-b92795bd4623	2
c74a538a-eb4a-5b9c-7e45-9d555916451e	377554d0-1f57-6179-b0ee-6f03230ff8b0	98253717-e67b-66a9-3791-fafcd2bedf4c	1
6a27cc99-d9fa-60f6-1b1c-362abbdb23ec	c8edac54-9f97-7fd4-3867-9e14861e3ba2	b9153f61-98ce-673a-b1bf-9bcb80671d62	2
85aff0b8-181d-fa6c-84c1-3e2a0c084a10	c8edac54-9f97-7fd4-3867-9e14861e3ba2	b2658dcd-838f-ca57-50d3-0ad0e007dcc4	1
c4339a18-7ca1-db09-88bb-9afef69a3b7e	98253717-e67b-66a9-3791-fafcd2bedf4c	0a1a022d-3fba-8a24-a6ca-602eb97b1936	1
4ed791bf-709b-45b1-97de-ee89ce67696b	82d39f73-488c-3113-49e7-b92795bd4623	38bf4156-78bc-b9f5-2bb4-3ad381e87a28	2
201230d9-2179-9af3-23c6-7c805e4f0a6b	82d39f73-488c-3113-49e7-b92795bd4623	07c0033a-c673-f236-3f59-093f5e236863	1
8ede9d5d-cff4-6d2e-597b-a2fe3ba6d77c	b262908e-c083-362b-db10-0d10ca4ed024	fe2929b6-a17a-269e-7ffd-23d3ce77c5b5	1
0debc439-2266-f749-6e93-966c7f796107	fe2929b6-a17a-269e-7ffd-23d3ce77c5b5	38bf4156-78bc-b9f5-2bb4-3ad381e87a28	2
f7ea0c58-cbff-3efa-ca81-a0e1ab2fc6a5	fe2929b6-a17a-269e-7ffd-23d3ce77c5b5	07c0033a-c673-f236-3f59-093f5e236863	1
bd10b395-b6b0-7198-58a3-66f24be46509	c8850768-6a93-5c31-5348-b20795ed8aa2	fd6a45b1-06c0-9242-a3cb-e24239e22545	2
d997c1d0-eaf1-f091-aa07-2fbe7f442ad9	c8850768-6a93-5c31-5348-b20795ed8aa2	63be24c7-78b8-e994-a2f9-e8a6c8ff4eff	1
518dd177-c9b8-08b0-763f-468d058ff68d	63be24c7-78b8-e994-a2f9-e8a6c8ff4eff	13be6ff9-6462-cca9-41e1-fe9acdf7a51a	2
89b0e649-8e94-c027-9ab7-4657aac454db	63be24c7-78b8-e994-a2f9-e8a6c8ff4eff	4e585981-7ff7-4de4-bbc7-fd1d1faea4fa	1
8191310d-dab8-619c-cb61-ff258ab7eb7d	4e585981-7ff7-4de4-bbc7-fd1d1faea4fa	ed95f5b7-ca4f-edb5-4809-46868512d5f2	2
9a846e95-3f85-f5b3-07d7-890a55c504bc	4e585981-7ff7-4de4-bbc7-fd1d1faea4fa	3a6d2484-ceb4-9a84-ffcb-6516984763fc	1
d9470c3e-fdd8-fe95-d6b2-e6d30d3dba52	3a6d2484-ceb4-9a84-ffcb-6516984763fc	22908966-252c-f62a-b264-bd7bd917b22c	1
2ed61797-0502-ae11-74f4-1366d77248bc	ed95f5b7-ca4f-edb5-4809-46868512d5f2	0c0f0e4b-15a7-f0ce-7aeb-49e8a356dbce	1
64584426-655b-34c7-8a2f-7d0e01b87b5b	0c0f0e4b-15a7-f0ce-7aeb-49e8a356dbce	68bb79f1-675e-1a9d-c435-f31326d2adc0	1
835e1bfe-1586-c3f8-55af-8363361ebb50	13be6ff9-6462-cca9-41e1-fe9acdf7a51a	82babd78-5e41-3189-c818-f57ddc5c401a	2
85ac43df-d73c-db36-4555-afc2d2caccde	13be6ff9-6462-cca9-41e1-fe9acdf7a51a	e21c65b2-83fd-02e9-eeab-677744d0394d	1
1568bd12-9be8-680e-c9e9-6b9e2ff4050f	e21c65b2-83fd-02e9-eeab-677744d0394d	3ce3bd7c-f086-2a3b-c594-4d18cf02a7b2	1
a0a5ede0-da36-9730-daae-b42f08b946d7	82babd78-5e41-3189-c818-f57ddc5c401a	de0def41-cd3e-8156-7917-89ee6d7aac51	1
6660854c-a938-1fa7-631e-aec2faca67d8	de0def41-cd3e-8156-7917-89ee6d7aac51	ac3d43b2-11f0-f354-4c0f-ed81917af056	1
4bc329ca-0707-4497-95ac-63e4fc0bb341	fd6a45b1-06c0-9242-a3cb-e24239e22545	38ce5860-b693-4151-ad13-dc7c2ae38f8e	2
65eb3412-6f02-dd23-0b63-045789d362f0	fd6a45b1-06c0-9242-a3cb-e24239e22545	ee91fd5f-c382-4b05-428d-082fb3dd2a4c	1
10fda9c8-ac9c-13ad-ee5b-6496b6756fdc	ee91fd5f-c382-4b05-428d-082fb3dd2a4c	c2ecd9d5-6085-75cd-7e11-2eb129f1b06e	1
257470d7-3e2b-5bb1-7a09-f7cc12c4cec8	c2ecd9d5-6085-75cd-7e11-2eb129f1b06e	c7a3b86a-95cb-9fe8-0e5b-39cb6e6ca392	1
fcd2afd8-e227-e248-f8f3-eea8c3ff17d3	38ce5860-b693-4151-ad13-dc7c2ae38f8e	619dadfb-5f0d-d2e4-bc1f-ea5f22452602	1
aa0dcec3-f8c9-e6cc-5cae-03e430ea2750	619dadfb-5f0d-d2e4-bc1f-ea5f22452602	83e7a716-298f-e77b-8869-9f273f1fb5b2	1
696fdc14-a7ff-e98a-388d-a8c24a1ae605	83e7a716-298f-e77b-8869-9f273f1fb5b2	1b836c93-2ca3-ccaf-ada5-ab9585830572	1
7f580a2d-ba09-3510-aba8-e6af29a6ccd6	914f793f-2376-a2c1-dddb-33614c13d6bb	eda6c713-9824-ea0b-c265-dcbbcde38fe4	2
31b3958c-13e4-69d7-d15c-78ee66ff58e7	914f793f-2376-a2c1-dddb-33614c13d6bb	7c65f813-54a4-e49b-6761-998010679793	1
74e0e72b-4973-9941-1160-72681a5ec08d	7c65f813-54a4-e49b-6761-998010679793	329f1d88-b1c0-0dfb-e483-04e44d7a8cb7	2
cdf885df-b3c4-a48e-f872-c00bb66761ab	7c65f813-54a4-e49b-6761-998010679793	cad9430a-f29b-3654-69d2-6522e78fd10b	1
a6f240ad-dab6-1c70-41b1-b9aec73756bf	cad9430a-f29b-3654-69d2-6522e78fd10b	35bc4ca0-b4e1-eb55-4aec-24103ff89e87	2
9a2597db-bccd-f318-f80d-f51c9cbf56f6	cad9430a-f29b-3654-69d2-6522e78fd10b	98a3e03c-3fe0-aefc-fa04-b34573372eab	1
3a33fe63-dfbe-ee8d-4be4-46c5f2c492fe	98a3e03c-3fe0-aefc-fa04-b34573372eab	0380de58-e79b-5348-28bb-b502643bdf13	1
e7fa3d62-10a1-0eb1-179b-ead940e51612	35bc4ca0-b4e1-eb55-4aec-24103ff89e87	5c6c7d16-4242-c6df-8601-559b06c8df6e	1
99117de2-48a3-0d05-ec75-cb15776e9e8b	5c6c7d16-4242-c6df-8601-559b06c8df6e	58b9fa36-356d-7ed4-f695-88d943509db5	1
d56d956b-a59b-6224-3ae8-fc75a6acdc59	329f1d88-b1c0-0dfb-e483-04e44d7a8cb7	ef355d74-058e-da5d-ee4f-f98a16f6b826	2
0f64515b-1bc7-a684-555e-a1b04b189b38	329f1d88-b1c0-0dfb-e483-04e44d7a8cb7	54aa834e-dedb-0126-4412-13764f18e243	1
041c616d-2acb-cf0b-d693-a3691cc386e2	54aa834e-dedb-0126-4412-13764f18e243	75c0a05c-7687-2266-8952-473fe7b86d06	1
672ddd64-cc32-a3df-cf65-214e972b3d3b	ef355d74-058e-da5d-ee4f-f98a16f6b826	2d8f35fd-3fe7-7869-49f5-bc9cbb752ea1	1
ef6bc006-1f20-874c-d3e3-5625c0e89e64	2d8f35fd-3fe7-7869-49f5-bc9cbb752ea1	30170f69-9377-9632-126e-7bb8214811a2	1
205e651c-2cd5-ec04-8de5-6864c342ab23	eda6c713-9824-ea0b-c265-dcbbcde38fe4	aa012536-8918-710b-0209-3b1da478cd70	2
7574aee0-813e-e113-1dab-c4b394aba1fc	eda6c713-9824-ea0b-c265-dcbbcde38fe4	fd5f90fd-3e68-39f1-46ab-441095c17fd8	1
8dae7a7b-80d3-5d9f-70be-e145f0f57fc1	fd5f90fd-3e68-39f1-46ab-441095c17fd8	c3ba5d02-6f67-3af6-016c-6d9649bed79b	1
e9638d59-f758-ac01-815a-7d3d8ae2d871	c3ba5d02-6f67-3af6-016c-6d9649bed79b	f9fd109c-05a1-f132-af67-590edb731f71	1
2df979c2-7e7a-f421-6e95-75ededf683bf	aa012536-8918-710b-0209-3b1da478cd70	94a026fb-28af-8d31-f0d7-f05073711e3c	1
5023ebda-3b22-02d6-9dc8-fd02915a321d	94a026fb-28af-8d31-f0d7-f05073711e3c	88a2ff70-ecc2-23e0-97e7-ebc3213188cd	1
cd454155-994d-581b-6794-e62240d2b7bd	88a2ff70-ecc2-23e0-97e7-ebc3213188cd	61c0ccb8-5d7d-d019-86c6-9a94b712064e	1
\.

COPY public.node_source_references ("id", "node_id", "source_title", "section_path", "locator", "locator_detail", "printed_page_numbers", "pdf_page_numbers", "reference_note", "reference_order") FROM stdin;
a0edded4-20c3-3b4e-e6d1-a2140ac21f5d	a04f0087-1e67-7368-d086-d6fcccdaedb1	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
04178b2d-3fb7-6661-24a7-7e5d1e94a51d	6538e358-5110-978e-fdeb-9f9163930524	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
cb7ed687-309b-93e9-3a5f-ebf409a3f5ed	7bc03fb5-45fa-4d03-6732-b8f4d0fb67d8	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
556f8244-baaf-98ec-947f-68b1702171e2	8902d0f7-7e45-05f3-57b4-3cbab88a2766	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
35ada4af-6a87-b743-4e53-09da5e786892	2ccf9a48-c739-b8c8-3ff3-58e07085dada	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
e9d98520-f403-3407-d01f-95f00177facd	f61c1dae-7953-1d8c-7397-3d1014a9a56e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
76cd3910-50ce-0c0a-0fe6-b414cfd7ca10	c4c213f6-cc3f-b126-965c-7cc29a920737	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
17e83024-de94-71d4-80ae-b4b3f47bd301	6ef8e7ef-9791-2d7a-de78-92bcf0157fd3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
499006b9-3b4e-b8ba-a58c-9e45e1564b02	993144cf-893d-ef87-efb3-a1adb2aff1b7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
7bf0071e-6169-41f8-a9d7-60c27d794f8d	82e84f39-0a8b-ed8e-14f1-78a9db7c991c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
bb97ffbf-91ff-9399-5774-463e6c34377a	e3a963b3-778c-bd6c-6346-31ef75b22c12	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Bảng 6. Ngưỡng huyết áp khởi trị theo tuổi và bệnh đồng mắc	Treatment-threshold classification used by Tree 3.	\N	\N	\N	2
911e3643-0717-1d73-1034-010e89dbfdc8	f75e07aa-b64c-f05a-3f40-beb41b32da8b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
66cb7d30-dbb9-365a-c267-8bec27c9aaa1	a28ba521-9617-68bd-700b-bd1ea531ef83	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
c66b5c63-6b4f-2f98-7b12-aa370bdb6d71	dcdfb9e6-8424-7c53-10c2-c59c612d0016	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
7c062787-ed7b-e60c-0d11-669e4990ad73	8c055fa2-1e69-33ea-7281-0d0e7fc668d4	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
723eafc7-de3d-6309-71bc-e7aad2f516d7	889df3c8-b8f3-d06b-8122-5e868cdee57c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
bc86dd9d-79d5-0766-cda6-33e99206aeab	b01e9357-c88c-04f0-365b-f6f88b91cd45	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
323c6389-cc3a-3765-7cb3-775cb7a0b95c	056a6e9f-05e4-2371-5783-3ba963d00c8b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
c2a63230-8448-db17-f1d5-a6032e1ae413	60c1e457-4b7d-614b-8ef7-61506403ef5f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
ac307e17-9776-50b9-6308-c04589f2dec9	67ab35c9-30ea-85e4-ffb8-1a15cfb906e1	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
b8a9e70b-bd9a-d062-78f4-761b3945c796	cd0e9072-3ea2-ae16-3d22-9c27c95e0bf5	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
853b8b47-e82f-b759-d93c-8e4142c17096	732bb6a9-f802-9e67-8377-bec03ab0ccab	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Bảng 7. Đích điều trị huyết áp theo tuổi và bệnh đồng mắc	Generic blood-pressure treatment target before any applicable modifier tree overrides or supplements it.	\N	\N	\N	2
3fbfd75f-43f4-77ce-68ad-9b1949549e09	0da5ee04-82fe-8681-957d-0ab16678ad1f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
4ac3a97f-c984-5691-e254-2eb18e29d7cd	0120ac75-acdf-48e0-db92-0d53f45198ad	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
0c79217b-9541-04b4-5888-7e26d6185876	578ce908-3403-1df1-378a-79136a9eedb3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
89921539-6225-e5ef-3269-e56651eeded5	dee9eca4-41b6-8283-fb90-22d986a02545	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
70d0a016-e0f1-3e14-e96c-4a24e5d72a82	d65ada75-d44e-f28b-4538-d5b8f7ba7d88	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
24800c6a-3058-c0ef-08d6-907789dd99f9	bc1e94e0-c24f-60dc-0183-55a69caf4364	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
a5480ac9-5e53-c174-845b-0a6fa4c4e8ab	ae850596-a036-f3d1-021b-462917f62055	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
783677bf-b646-b5a8-9709-99b61f404bed	15b24644-6822-aeec-5228-6c66fe4e4c34	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
05a7c8a6-01c6-49a5-6885-682e41cc40b1	150b12aa-ea76-4ef4-4ae9-72e8b3427d57	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
b7a7ece9-1a9c-4190-2130-2fc5d79fbcce	82622d63-8358-42e4-5396-5b0de98cb992	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
77b95227-4ddc-2eca-bc47-b6b04d733d73	95569744-0278-46a5-b937-6c519a461eec	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Bảng 7. Đích điều trị huyết áp theo tuổi và bệnh đồng mắc	Generic blood-pressure treatment target before any applicable modifier tree overrides or supplements it.	\N	\N	\N	2
718201b2-cd20-35df-d615-1c04b476819c	50183af5-180d-684d-ca85-0a39375047f6	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
79353ebe-2b4a-69a3-ee65-6e43d414d0b7	f71ef072-f987-4bdf-74ea-9831561c847d	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
af1d441b-d58e-a9d1-a895-f142b0d702ef	4156b708-5a62-f921-c8f8-c4fcc66ac355	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
a24fcbb3-9dc1-d04a-b24f-d3c65fb98bb4	b252d144-2b2d-17d1-97d6-ebe8419d6347	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
c8fe03fc-f217-170b-5f0c-86500e133111	024340ba-69f5-8b5f-ee24-1a8ac453af3f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
8f1bd02b-a46b-f1da-85cc-181df29a580a	e246a50d-938e-801a-9d10-fda5e54e3409	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
e7fd943e-4028-9dab-9602-bb714a7963d8	e2999392-875c-8b00-231c-c0d860198d0d	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
a3a3398f-142d-59b9-a80d-832aadefcfa2	41df521d-823e-bbeb-ed4b-850f86b212a7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
f5444e91-8013-3e25-14a3-eb7a6660082a	6b917a54-139e-9612-88fb-d7a07f13d854	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
9389435d-1cc9-d4db-8964-34da6cc4a1e4	ad79523f-69d2-df24-dfe2-d932d2cebd3b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
2dea4c23-d94d-9124-bfb8-6b2d40701557	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Bảng 7. Đích điều trị huyết áp theo tuổi và bệnh đồng mắc	Generic blood-pressure treatment target before any applicable modifier tree overrides or supplements it.	\N	\N	\N	2
9884b6f7-1182-5f9f-6e16-f9a67fda6e62	9c646ad6-5544-914d-f5b4-272ff4613e77	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
5838d15b-3878-f2fe-0511-b0337972e8ac	1bfbc013-8b60-85f8-0e6f-16bb8b2e08f3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
0128aaea-6325-23af-d1cc-6ce73f1f7bfd	42a86643-3a3d-4e13-e45f-c160a278e0b9	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
812249ad-b551-8ee7-c690-dd1acaffd71c	28c71bb1-a8df-b8d0-bc32-06c0e5006228	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
bf5d9e0b-17e8-2cf0-8d2c-3ab198f085e5	e9270ac1-7ccd-40d7-92d4-a8e4d065f611	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
7a6734e0-e98a-1c22-e051-bae8bef0bafb	c0a64934-faa3-7403-22a9-8db45fb883d9	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
182e5760-86b3-51d0-6561-dd73eaf46a5d	bfbb746b-d5ff-6d27-a5e6-5376a31d2841	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
916776a1-3981-8d60-3a98-7026a9ea327c	e76d51eb-d7f0-3ac8-9f48-bd5e57eb2e0c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
6d9da5ce-aa99-d3f1-87c8-80c959738420	901b8971-4490-05eb-0fb4-7b009bb8929e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Sơ đồ chẩn đoán tăng huyết áp", "number": "1.3"}]	Hình 1. Sơ đồ chẩn đoán tăng huyết áp với phương pháp đo huyết áp tại phòng khám (thiết yếu) và phương pháp đo huyết áp tại nhà, đo huyết áp liên tục (tối ưu)	Tree 1 diagnosis workflow and routing logic.	{8}	{10}	Digitized according to the approved Tree 1 diagram.	1
f75c2154-499c-2914-8bec-e479a0381f7e	a04f0087-1e67-7368-d086-d6fcccdaedb1	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
3aed4640-f325-63a7-90c5-c12cf61a492a	7cee6dc2-7420-d2db-e172-43e3cb73ebf8	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
e8367132-c75a-6e8c-2e05-26f6efcbbe4a	6538e358-5110-978e-fdeb-9f9163930524	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
64659695-0eb9-348f-3b72-6416b531c2e0	7bc03fb5-45fa-4d03-6732-b8f4d0fb67d8	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
7227c6fd-bcb3-42d2-21a2-939d3e0f6eed	8902d0f7-7e45-05f3-57b4-3cbab88a2766	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
185fb95b-77b4-e4ae-4272-45445d4120d4	82e84f39-0a8b-ed8e-14f1-78a9db7c991c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
d600e92f-3378-60b9-b752-0a9b6c76b69a	b252d144-2b2d-17d1-97d6-ebe8419d6347	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
e489bb48-6c20-8375-660a-f8c09daf2427	993144cf-893d-ef87-efb3-a1adb2aff1b7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
ffa1c981-bde6-800d-0c7f-a9df5fb111d5	4156b708-5a62-f921-c8f8-c4fcc66ac355	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
978c395e-2f41-c51f-1dd8-687224600dd2	6ef8e7ef-9791-2d7a-de78-92bcf0157fd3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
d4dc6ef6-8e76-f8ed-faee-119cd5ecfb90	f71ef072-f987-4bdf-74ea-9831561c847d	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
526ca2bd-8e2e-2efb-0b62-faf380595a92	c4c213f6-cc3f-b126-965c-7cc29a920737	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
49ea6e91-ae16-3c78-3008-543239e03c51	50183af5-180d-684d-ca85-0a39375047f6	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
9b35f877-cc32-f858-bff4-0dd6731090df	f61c1dae-7953-1d8c-7397-3d1014a9a56e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
f26bbcd5-1d6d-cb33-4383-746383389ea7	82622d63-8358-42e4-5396-5b0de98cb992	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
76086983-3968-21f3-a90b-87bfd2fe75c2	f75e07aa-b64c-f05a-3f40-beb41b32da8b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
b6229115-00c4-45ee-fc78-cbb67e9fe9e0	a28ba521-9617-68bd-700b-bd1ea531ef83	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
38bd0fa5-a2dd-2c74-e4aa-9755a42f3bc4	056a6e9f-05e4-2371-5783-3ba963d00c8b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
eb064b4e-2ada-754c-7726-559fe2512a46	ad79523f-69d2-df24-dfe2-d932d2cebd3b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
ca5713a4-d593-d53f-c05b-e801c8873449	b01e9357-c88c-04f0-365b-f6f88b91cd45	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
33508c5a-97e7-00ea-6108-6bbeb89089f4	6b917a54-139e-9612-88fb-d7a07f13d854	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
f6ca9f45-3e32-93b7-8b09-ca29cc7b015f	889df3c8-b8f3-d06b-8122-5e868cdee57c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
1f044899-3a33-9717-2c63-01dd84eef71f	41df521d-823e-bbeb-ed4b-850f86b212a7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
2ca4400f-0b13-ba2a-883f-9cf3893616ad	8c055fa2-1e69-33ea-7281-0d0e7fc668d4	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
691e657e-b036-677a-3440-b5bef4319cee	e2999392-875c-8b00-231c-c0d860198d0d	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
d90545d9-a473-e766-7483-16dd13700b88	dcdfb9e6-8424-7c53-10c2-c59c612d0016	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
320e3944-4e4d-ff26-4b95-b600a380869b	e246a50d-938e-801a-9d10-fda5e54e3409	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
23f5c6e4-2105-beeb-72cd-9882c434f1d8	dee9eca4-41b6-8283-fb90-22d986a02545	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
8cca79d7-22e3-632a-b052-81224442d4e8	d65ada75-d44e-f28b-4538-d5b8f7ba7d88	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
36253f6e-47cc-17b0-67a0-ba033b7ffb08	0da5ee04-82fe-8681-957d-0ab16678ad1f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
8d2a07db-6a4e-ca8f-36e7-e67e81e9a951	e9270ac1-7ccd-40d7-92d4-a8e4d065f611	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
e208c1dc-0299-e113-595a-99a21277f8a0	67ab35c9-30ea-85e4-ffb8-1a15cfb906e1	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
ed0d04da-ed49-25b9-e34f-36aac80e78bb	42a86643-3a3d-4e13-e45f-c160a278e0b9	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
ca5f6545-1f29-7137-94b3-fa6de915005e	60c1e457-4b7d-614b-8ef7-61506403ef5f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
12cfcaf8-bb6c-49d2-baac-e7fd8af7ce82	1bfbc013-8b60-85f8-0e6f-16bb8b2e08f3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
85075b17-de81-bd3f-eccc-ef3a5e46eb16	cd0e9072-3ea2-ae16-3d22-9c27c95e0bf5	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
85710b63-b3eb-24e8-ba25-24bd20e6e338	28c71bb1-a8df-b8d0-bc32-06c0e5006228	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
e9b42f67-ee25-1a03-c97b-79b658d7d0d0	578ce908-3403-1df1-378a-79136a9eedb3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
8b8f272d-f1a8-3f53-647d-f9d6a4595943	c0a64934-faa3-7403-22a9-8db45fb883d9	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Clinic BP thresholds for normal BP, high-normal BP, Grade 1 hypertension, Grade 2 hypertension, hypertensive emergency, and isolated systolic hypertension.	{7}	{9}	\N	2
fc7c10ae-8e64-e9c3-e7ad-83b1bd1148d7	901b8971-4490-05eb-0fb4-7b009bb8929e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Định nghĩa và phân loại tăng huyết áp", "number": "1.2"}]	Bảng 1. Chẩn đoán tăng huyết áp theo ngưỡng huyết áp đo tại phòng khám	Normal BP classification: SBP <130 mmHg and DBP <85 mmHg.	{7}	{9}	Applied to the final Tree 1 normal out-of-office BP path.	2
c406b519-5e7e-06d8-4dd7-9c3478a4c74f	4ef64653-acf3-b7b9-e6fc-8e594a02967a	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
af6bcb23-393f-6099-e149-08ad7b93ff7f	ebd2cf1d-a6d6-e606-f1b7-d83ae2028e4e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
87efde60-6424-85bc-efd5-d3650c1e3850	677ced6a-83c9-f393-be9d-1f520be5bada	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
46a16dd3-2e02-461b-e9ba-6ba207a8043b	15d21cbf-d095-e977-4b20-b71b993a7aad	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
7d92526e-31e5-1877-4fae-31a76a463bd7	7ba7c905-6d36-3414-e4c5-0116b03bcdbf	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
aabbecc7-5311-a444-8c6e-43adca6db8f8	9dc9020e-d70e-1ebe-f2ea-b390b5346c33	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
067a420c-bc99-c9eb-bc74-584e6e40cbc4	fc6394bc-6d70-5ab1-f750-1a26069ac9b7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Bảng 6. Ngưỡng huyết áp khởi trị theo tuổi và bệnh đồng mắc	Treatment-threshold classification used by Tree 3.	\N	\N	\N	2
fc97fa1d-f292-08e4-bf2d-9e47d0be42fe	3f0e2f17-4775-0538-ce10-6f11dc621c84	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
8dee95a5-d5cf-2d35-ffe5-a695a521fe5d	23276de5-636d-3312-1636-1dc4f4b6b969	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
291c9310-1d52-35bd-7238-1d871f229bc9	8ceb98a6-3e3f-0fce-ab0d-6b746ac16f7a	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
08237b25-0cf2-860a-4eb7-2f224cf8b078	98cee07d-28ca-dcc6-384c-02c30b0b50fe	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
f9a0aeb5-ed6c-4e8a-dd58-571160d99ccc	8058aebe-6375-cafe-b718-d5df20ac85c9	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
3a2b9cb2-e219-44fe-067e-897835d7647c	165c4ea4-8261-4117-9efb-83084a9b3e2a	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
e881996e-eeb1-80db-c331-4f01329f14ce	ba1a1c44-b0fd-499d-144c-ac54731ba62d	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
0be6b1eb-5f24-12e9-d397-bcde65a00867	b492a11d-3566-318f-3269-e04bc11d09fa	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
e87ff68c-328c-e11d-ff02-c1cd4d6bf043	3ed68451-bfad-5d50-de50-7c968df606af	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
c2548457-b9a3-fe2d-5ce0-e7a02ccd59e6	03f895d0-ee99-19d6-58c3-35b49042dda3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
cd8ea5a0-f160-41bb-b4e9-c2e53a4e4584	fb7c62d1-4d86-0013-e05e-4f862b4a4d8a	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
aada0213-b8a4-61de-a921-131821358e27	27c4d74f-163b-4131-11d4-9597e6404738	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
c1c2302b-0d3a-5ab3-150b-45843e151216	20a7535d-1695-4d68-0048-c86dc1101221	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
28d95fe6-493b-c58a-54ae-06c4e3c1df0a	d186b9cc-2b53-3662-e66d-655fff3ba7c6	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
ea77249b-d6b3-d92e-e796-068aa2e1cf1e	d77ec0d8-f756-6377-6f0a-e8cb2f5e8a15	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
f4f51b89-fc46-1b73-7eb6-ae2134465717	fc7fc2c0-c399-0786-26b1-836ef99c51c4	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Chẩn đoán tăng huyết áp", "number": "I"}, {"title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp", "number": "1.5"}]	Bảng 2. Phân tầng nguy cơ trong tăng huyết áp	Risk-factor list, high-risk comorbidities, and risk classification by BP category and risk-factor count.	{9}	{11}	Digitized according to the approved Tree 2 diagram.	1
de9ddc3c-37cc-eca0-e958-a8c45620d142	bc44960d-3c0a-ffd7-6949-e4da0dc6d7f4	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
7208160c-9c55-17d6-bb07-ca8ac825b956	b2658dcd-838f-ca57-50d3-0ad0e007dcc4	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
67b07d50-d4f9-91d8-df53-bae1157d9961	b9153f61-98ce-673a-b1bf-9bcb80671d62	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
2bc4abf8-c49c-f5ab-0483-020be25b58b7	a8e8f94a-73e3-90e0-bb13-d5391d228a46	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
d14997b0-a04a-3988-8a47-608d117e51d9	24dbca8b-981c-416b-e3c9-3189ff36c8d7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
2ee5f4f9-d1d6-8d91-e960-9711b1585f15	a568efbe-4123-a88c-7824-dce7c9f4744c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
0b9a74c3-2100-cc0a-16e5-b17fcdb6ce22	86deea06-0fd7-f7d1-052f-80aadbd34f2d	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
bc1f6961-f7a8-9b54-35bb-c59543cd5134	0c92a137-09dd-cc40-8d65-a16871ae8176	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
eded1a7d-ec4e-9f8c-c6f6-07b33f3d5cd7	732bb6a9-f802-9e67-8377-bec03ab0ccab	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
77a8814e-6730-a4eb-5c1c-8455810161d9	aac650db-813f-8d02-d74f-52d83aec84f9	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
9e4a52fe-913c-bc3f-1cc3-ccc2fed327e9	b03048ca-27aa-09c2-bff4-ee361ac09378	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
aff36608-b1cd-f8b8-b8fb-ed4a258bfb78	95569744-0278-46a5-b937-6c519a461eec	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
fc1bccb1-07b7-d298-e74a-cf8a4d9c35d9	d61ccc11-d575-6482-9c9b-231f43424ab1	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
9637bce8-0a6d-2158-ca2f-0baac0e51999	e9e05195-a8f6-b2bd-e31e-6cfa937d1d56	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
02df737e-50f8-59a5-0fd1-df54ead1115f	c10efb3e-1efc-6aa1-e0c1-b2e799e2c77b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
b1a1025b-4cda-a671-93d3-21a55181e0a7	fc6394bc-6d70-5ab1-f750-1a26069ac9b7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
a426b026-284e-361f-cb58-662d94ce3157	314a95d2-649f-4168-ffca-5ae74bd586c4	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
1061dbd9-a224-f827-681e-e8b98d861215	d8ed1b7c-c4d6-ffab-aa92-f41a3acac47b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
a633afd9-2154-ef7a-d9d8-f69ee0360716	e3a963b3-778c-bd6c-6346-31ef75b22c12	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
fda12520-0a10-3d3c-2b45-46d18211cb4a	9261e551-a1e4-f52d-776f-256476cde602	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
96722b49-ca24-2659-2c04-672204739974	c9e3529b-2291-4756-1e9c-13b00c5fdd0f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Hình 2. Ngưỡng huyết áp khởi trị và đích điều trị theo tuổi, huyết áp và bệnh đồng mắc	Tree 3 age group routing, comorbidity routing, lifestyle action path, and treatment-target routing.	\N	\N	Digitized according to the approved Tree 3 diagram.	1
302f70e6-3756-1c9a-1f83-bc0bc09f85c7	86deea06-0fd7-f7d1-052f-80aadbd34f2d	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Bảng 6. Ngưỡng huyết áp khởi trị theo tuổi và bệnh đồng mắc	Treatment-threshold classification used by Tree 3.	\N	\N	\N	2
ec7f280e-d0e7-f954-3eaf-e6a2bbdc14e3	aac650db-813f-8d02-d74f-52d83aec84f9	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "II"}]	Bảng 6. Ngưỡng huyết áp khởi trị theo tuổi và bệnh đồng mắc	Treatment-threshold classification used by Tree 3.	\N	\N	\N	2
1b72c1e6-c409-9674-b85e-72624ff61038	012c8740-0d0a-ffa9-93ff-41f19bf24ee7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Ngưỡng huyết áp ban đầu cần điều trị và ranh giới đích điều trị tăng huyết áp", "number": "3.1"}]	Hình 2. Tóm tắt ngưỡng huyết áp ban đầu & đích huyết áp phòng khám ở THA người lớn	High-normal BP with high cardiovascular risk enters the medication-treatment pathway.	{14}	{16}	Tree 3 patch: high-risk HABTC is not lifestyle-only.	1
35acebc5-c7e3-af53-7727-6add2ab19df6	d49ed998-c9d4-c06f-9859-ebd4459f4457	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Ngưỡng huyết áp ban đầu cần điều trị và ranh giới đích điều trị tăng huyết áp", "number": "3.1"}]	Hình 2. Tóm tắt ngưỡng huyết áp ban đầu & đích huyết áp phòng khám ở THA người lớn	High-normal BP with high cardiovascular risk enters the medication-treatment pathway.	{14}	{16}	Tree 3 patch: high-risk HABTC is not lifestyle-only.	1
54f3f25b-1e6b-b595-2736-774e81669285	cfb91d03-1e28-26a1-acc8-44e033cac052	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Ngưỡng huyết áp ban đầu cần điều trị và ranh giới đích điều trị tăng huyết áp", "number": "3.1"}]	Hình 2. Tóm tắt ngưỡng huyết áp ban đầu & đích huyết áp phòng khám ở THA người lớn	High-normal BP with high cardiovascular risk enters the medication-treatment pathway.	{14}	{16}	Tree 3 patch: high-risk HABTC is not lifestyle-only.	1
eaf58956-6717-8de1-9251-a06b4f925c75	cfb91d03-1e28-26a1-acc8-44e033cac052	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Ngưỡng huyết áp ban đầu cần điều trị và ranh giới đích điều trị tăng huyết áp", "number": "3.1"}]	Bảng 7. Mục tiêu huyết áp phòng khám trong điều trị tăng huyết áp theo nhóm tuổi	Treatment target for high-normal BP with high cardiovascular risk.	{16}	{18}	\N	2
06600c37-587d-62f8-5a52-19200752fb17	24fd4dc9-e461-86fe-73ee-72f28c410793	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Ngưỡng huyết áp ban đầu cần điều trị và ranh giới đích điều trị tăng huyết áp", "number": "3.1"}]	Bảng 6. Ngưỡng huyết áp phòng khám cho điều trị tăng huyết áp theo nhóm tuổi	Age 18–69 with comorbidity: DBP treatment threshold is 85 mmHg.	{15}	{17}	\N	1
be553db4-d638-7651-8d74-b6ff2259972f	1cd09c61-8f8a-ef32-ef53-eb47481b78c8	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Ngưỡng huyết áp ban đầu cần điều trị và ranh giới đích điều trị tăng huyết áp", "number": "3.1"}]	Bảng 6. Ngưỡng huyết áp phòng khám cho điều trị tăng huyết áp theo nhóm tuổi	Age 18–69 with comorbidity: DBP treatment threshold is 85 mmHg.	{15}	{17}	\N	1
e2dd5707-d77d-2a3e-4658-06744b6254ae	38ce5860-b693-4151-ad13-dc7c2ae38f8e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	High-normal BP with low/intermediate risk follows the monotherapy-consideration branch.	{17}	{19}	\N	1
ba97bcec-eb9a-b102-1190-84e80951e9e7	377554d0-1f57-6179-b0ee-6f03230ff8b0	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Follow-up after lifestyle change; medication consideration when BP remains uncontrolled after lifestyle management.	{17}	{19}	The 10 mmHg SBP and 5 mmHg DBP thresholds are local project policy, not numeric thresholds stated in the guideline figure.	1
520d32c0-a388-08b9-e6c9-c9fc2908f14f	98253717-e67b-66a9-3791-fafcd2bedf4c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Follow-up after lifestyle change; medication consideration when BP remains uncontrolled after lifestyle management.	{17}	{19}	The 10 mmHg SBP and 5 mmHg DBP thresholds are local project policy, not numeric thresholds stated in the guideline figure.	1
4b183b8e-25d5-ee92-f759-566636245518	82d39f73-488c-3113-49e7-b92795bd4623	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Follow-up after lifestyle change; medication consideration when BP remains uncontrolled after lifestyle management.	{17}	{19}	The 10 mmHg SBP and 5 mmHg DBP thresholds are local project policy, not numeric thresholds stated in the guideline figure.	1
e4b2e707-9900-d3b5-8eaf-e95c4dab1737	0a1a022d-3fba-8a24-a6ca-602eb97b1936	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Follow-up after lifestyle change; medication consideration when BP remains uncontrolled after lifestyle management.	{17}	{19}	The 10 mmHg SBP and 5 mmHg DBP thresholds are local project policy, not numeric thresholds stated in the guideline figure.	1
a6d9f914-4c89-8ac3-a8fe-faceb041d983	6d02a060-240f-e7b8-2db5-9ade7f4f2708	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Tree 4 uses the current accumulated BP target, including any modifier-tree override.	{17}	{19}	Implementation note for target propagation across Tree 3 and modifier trees.	1
0187ba07-7fdb-dd6f-9926-9bd2c0be2a4e	3a6d2484-ceb4-9a84-ffcb-6516984763fc	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Treatment follow-up checks whether clinic BP has reached the active target.	{17}	{19}	Runtime target comparison uses context.treatment.bp_target.	1
44e4a4af-450b-a03a-e8f2-1f2ad35e2800	0c0f0e4b-15a7-f0ce-7aeb-49e8a356dbce	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Escalation to usual dose or three-drug combination, prioritizing A+C+D when available.	{17}	{19}	\N	1
3107cf97-17cd-db23-3125-db19ec41b853	e21c65b2-83fd-02e9-eeab-677744d0394d	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Treatment follow-up checks whether clinic BP has reached the active target.	{17}	{19}	Runtime target comparison uses context.treatment.bp_target.	1
d4b77049-6ec4-d9a0-dfac-4fb1d6d17f8c	de0def41-cd3e-8156-7917-89ee6d7aac51	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Persistent failure after escalated regimen leads to difficult-to-control hypertension and specialist/resistant-hypertension pathway.	{17}	{19}	\N	1
3a3363b3-05a5-2c75-289f-7ef006f2bd3a	ee91fd5f-c382-4b05-428d-082fb3dd2a4c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	High-normal BP with high risk or comorbidity, or hypertension >=140/90, enters the two-drug strategy.	{17}	{19}	\N	1
e28b8597-d016-cf8d-1682-f3f8cfee0939	c2ecd9d5-6085-75cd-7e11-2eb129f1b06e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Two available medicines, from low dose to usual dose.	{17}	{19}	\N	1
388f61c8-3b07-7d1f-a5b0-f1235456e601	619dadfb-5f0d-d2e4-bc1f-ea5f22452602	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	Monotherapy may be considered after lifestyle management when BP remains uncontrolled, or for age >=80 / frailty.	{17}	{19}	\N	1
4de34061-2713-0ac2-f20a-f22851b0ec67	83e7a716-298f-e77b-8869-9f273f1fb5b2	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 3. Sơ đồ điều trị tăng huyết áp thiết yếu VSH/VNHA 2022	A, B, C, or D; beta-blocker only when indicated; thiazide-like diuretic preferred.	{17}	{19}	\N	1
9ad64ebe-8d98-2678-09e0-9a397359fc06	74f3cdc3-0390-aa3d-5f21-9d8128a6f3d7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	Tree 5 uses the current accumulated BP target, including modifier-tree overrides.	{18}	{20}	Implementation note for target propagation across Tree 3 and modifier trees.	1
e57d52cd-dbee-066b-bc2c-99c64454c750	98a3e03c-3fe0-aefc-fa04-b34573372eab	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	Treatment follow-up checks whether clinic BP has reached the active target.	{18}	{20}	Runtime target comparison uses context.treatment.bp_target.	1
29df3401-4760-e1b3-7a14-a96531b8c9f7	5c6c7d16-4242-c6df-8601-559b06c8df6e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	One-pill fixed-dose A+C+D combination.	{18}	{20}	\N	1
eaea46ad-616a-4fcc-25a2-8396fc4d68b8	54aa834e-dedb-0126-4412-13764f18e243	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	Treatment follow-up checks whether clinic BP has reached the active target.	{18}	{20}	Runtime target comparison uses context.treatment.bp_target.	1
729cbbd3-0ab8-d04e-0f0d-610256d8d158	2d8f35fd-3fe7-7869-49f5-bc9cbb752ea1	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	Resistant-hypertension treatment step before transition to the resistant-hypertension tree.	{18}	{20}	\N	1
a7fb39c2-4cd7-8bdc-7aa6-8471ba8520ac	fd5f90fd-3e68-39f1-46ab-441095c17fd8	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	High-normal BP with high risk or comorbidity, or hypertension >=140/90, enters the two-drug strategy.	{18}	{20}	\N	1
deab63a5-49ad-5f4d-3bc7-0c723570c90d	c3ba5d02-6f67-3af6-016c-6d9649bed79b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	One-pill fixed-dose two-drug combination, starting at half the usual dose.	{18}	{20}	\N	1
1a8d6914-7ebe-a572-5569-97a1e795101e	aa012536-8918-710b-0209-3b1da478cd70	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	High-normal BP with low/intermediate risk follows the monotherapy-consideration branch.	{18}	{20}	\N	1
c43d9257-2df1-facf-3454-ea4fa9c2db0d	94a026fb-28af-8d31-f0d7-f05073711e3c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	Monotherapy may be considered after lifestyle management when BP remains uncontrolled, or for age >=80 / frailty.	{18}	{20}	\N	1
99178c76-adb6-5f07-a0de-58e2c908440c	88a2ff70-ecc2-23e0-97e7-ebc3213188cd	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)	[{"title": "Điều trị tăng huyết áp", "number": "III"}, {"title": "Chiến lược điều trị tăng huyết áp", "number": "3.2"}]	Hình 4. Sơ đồ điều trị tăng huyết áp tối ưu VSH/VNHA 2022	One-pill monotherapy options: A, B, C, or D. Beta-blocker requires an appropriate indication.	{18}	{20}	\N	1
\.


-- ================================================================
-- Tree 6: drug-combination (source: tree6.sql)
-- ================================================================
--
-- CDSS decision-tree insert script (sixth pass — specific-clinical-situation
-- beta-blocker check now gates every regimen tier; fifth pass cross-checked
-- against Tree 4/Tree 5 and drug-list removed; fourth pass rebuilt to match
-- the author's own 5-image board description, verbatim)
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
        'T6_ACTION_COMPARE_WITH_CURRENT_PRESCRIPTION', 'ACTION',
        'Compare with current prescription', 'So sánh với đơn thuốc hiện tại',
        NULL::jsonb,
        '{"treatment":{"has_dosage_adjustment_request":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_dosage_adjustment_request","to_path":"context.treatment.has_dosage_adjustment_request","required":false}]}'::jsonb,
        '{"action_type":"COMPARE_WITH_CURRENT_PRESCRIPTION","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
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
        'T6_ACTION_ADJUST_REGIMEN', 'ACTION', 'Adjust regimen', 'Điều chỉnh phác đồ',
        NULL::jsonb, '{"treatment":{"status":"ADJUST_REGIMEN"}}'::jsonb,
        '{"action_type":"ADJUST_REGIMEN","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 9
    ),
    (
        'T6_ACTION_MAINTAIN_REGIMEN_NO_ADJUSTMENT', 'ACTION', 'Maintain regimen', 'Duy trì phác đồ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"MAINTAIN_CURRENT_REGIMEN","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 10
    ),
    -- --- Step 2: contraindication determination (reference lookup, see architecture note) ---
    (
        'T6_INF_DETERMINE_CONTRAINDICATIONS', 'INFERENCE',
        'Determine contraindicated drug classes based on patient information and current regimen',
        'Xác định thuốc chống chỉ định dựa trên thông tin bệnh nhân và phác đồ hiện tại',
        NULL::jsonb,
        '{"operations":[{"op":"COPY_PATH","from_path":"input.contraindicated_drug_classes","to_path":"context.treatment.contraindicated_drug_classes","required":false}]}'::jsonb,
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
    -- --- Step 3: duplicate drug-class check (runs unconditionally, per author) ---
    (
        'T6_ACTION_CHECK_DUPLICATE_DRUG_CLASS', 'ACTION',
        'Check duplicate drug class', 'Kiểm tra trùng nhóm thuốc',
        NULL::jsonb,
        '{"treatment":{"has_duplicate_drug_class":false,"has_duplicate_ras_inhibitor":false},"operations":[{"op":"COPY_PATH","from_path":"input.has_duplicate_drug_class","to_path":"context.treatment.has_duplicate_drug_class","required":false},{"op":"COPY_PATH","from_path":"input.has_duplicate_ras_inhibitor","to_path":"context.treatment.has_duplicate_ras_inhibitor","required":false}]}'::jsonb,
        '{"action_type":"CHECK_DUPLICATE_DRUG_CLASS","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 13
    ),
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
        'T6_ACTION_KEEP_ONE_OR_REMOVE_BOTH', 'ACTION',
        'Keep only 1 drug or remove both; prefer keeping the one already in use, only remove both for a special requirement',
        'Chỉ giữ lại 1 thuốc hoặc loại bỏ cả hai. Ưu tiên giữ lại thuốc đã hoặc đang dùng trước đó, chỉ loại bỏ cả hai khi có yêu cầu đặc biệt',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"KEEP_ONE_OR_REMOVE_BOTH_DUPLICATE_RAS_INHIBITORS","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 18
    ),
    (
        'T6_ACTION_KEEP_ONE_DRUG', 'ACTION', 'Keep only 1 drug', 'Chỉ giữ lại 1 thuốc',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"KEEP_ONE_DRUG_DUPLICATE_CLASS","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
        NULL::jsonb, NULL::text, NULL::text, 19
    ),
    (
        'T6_ACTION_MAINTAIN_REGIMEN_NO_DUPLICATE', 'ACTION', 'Maintain regimen', 'Duy trì phác đồ',
        NULL::jsonb, NULL::jsonb,
        '{"action_type":"MAINTAIN_CURRENT_REGIMEN","follow_up_mode":"NEW_ENCOUNTER","follow_up_required":false}'::jsonb,
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
    -- Step 2 -> Step 3 (unconditional, runs for every patient)
    ('T6_INF_DETERMINE_CONTRAINDICATIONS', 'T6_ACTION_CHECK_DUPLICATE_DRUG_CLASS', 1),
    -- Step 3
    ('T6_ACTION_CHECK_DUPLICATE_DRUG_CLASS', 'T6_C_HAS_DUPLICATE_DRUG_CLASS', 1),
    ('T6_ACTION_CHECK_DUPLICATE_DRUG_CLASS', 'T6_C_NO_DUPLICATE_DRUG_CLASS', 2),
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
    ('T6_ACTION_CHECK_DUPLICATE_DRUG_CLASS',
     'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
     '[{"number": "3.4", "title": "Điều trị Tăng huyết áp bằng thuốc"}]'::jsonb,
     'Bảng 9. Chiến lược điều trị tăng huyết áp bằng thuốc',
     'Dual RAS-inhibitor blockade is not recommended (Class III, Level A).',
     ARRAY[20]::smallint[], ARRAY[22]::smallint[],
     'Việc phối hợp hai nhóm thuốc ức chế hệ renin-angiotensin không được khuyến cáo.', 1),
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

-- ================================================================
-- Tree 8: hypertension-type-2-diabetes (source: tree8.sql)
-- ================================================================
--
-- CDSS decision-tree insert script
-- Tree: "Cây 8: THA + Đái tháo đường týp 2 - Minh"
-- Source: Bảng 18, Bảng 2, Bảng 6, Bảng 7 (Khuyến cáo THA VNHA 2022.pdf)
--
-- This script inserts one decision tree and all its nodes/edges/references
-- into the existing cdss schema. See backups/shared_conventions.txt for the
-- full naming/shape audit this file was brought into line with (extracted
-- from the 5 real seeded trees).
--
-- IDs are generated by gen_random_uuid() (core since PG13). Timestamps are
-- generated by now() at insert time — nothing is hardcoded. Each statement
-- re-resolves the parent id it needs (tree_id by tree_key, node ids by
-- node_key) via a join back to the row inserted by the previous statement.
--
-- Regimen-selection redesign (this pass):
--   The four separate ACEI+CCB / ARB+CCB / ACEI+D / ARB+D INFERENCE nodes
--   had no distinguishing condition, so the engine always took the first
--   in traversal order — there was no real way to choose between them, and
--   picking one arbitrarily would ignore contraindications. Trees 4 and 5
--   (essential-treatment-strategy / optimal-treatment-strategy), which this
--   tree links into, already solve this exact problem: they never resolve
--   ACEI-vs-ARB or a specific drug themselves. They state the class-level
--   option (letter "A" covers both ACEI and ARB) via
--   treatment_preferences.combination_options (see
--   T5_ACTION_FIXED_DOSE_TWO_DRUG_COMBINATION's
--   "combination_options": [["A","C"],["A","D"]]) and hand off to
--   link_target_tree_key = "drug-combination" (Tree 6) for the actual
--   contraindication-based agent pick. Collapsed the four nodes into one
--   T8_INF_REGIMEN_OPTIONS emitting the same combination_options shape,
--   removing the arbitrary always-picks-first behavior and the duplicate
--   fan-out into T8_C_HAS_CV_RISK / T8_C_NO_CV_RISK. Tree 6 itself is not
--   yet seeded (0 rows) — this only makes Tree 8 consistent with Tree 4/5's
--   already-established design, it does not build Tree 6.
--
-- Other fixes applied in an earlier pass (cross-checked against
-- backups/Khuyến cáo THA VNHA 2022.pdf, section 3.7.1, p.34):
--   * The SGLT2i/GLP-1RA trigger condition previously listed six risk
--     factors including invented fields has_atherosclerotic_ckd and
--     has_high_cardiovascular_risk. The actual source text only says
--     "khi có bệnh tim mạch do xơ vữa và/hoặc nguy cơ cao" (atherosclerotic
--     CVD and/or high risk) — no CKD or target-organ-damage mention here.
--     Rebuilt using the established fields has_cardiovascular_disease,
--     has_coronary_artery_disease, has_stroke (ASCVD's components per
--     Bảng 2's own definition) and context.risk.level == "HIGH".
--   * T8_INF_MAINTAIN_REGIMEN uses treatment.status, matching T4's
--     status-flag pattern.
--   * GLOBAL node restructured to the kind/purpose metadata shape used by
--     every real GLOBAL node (was a flat glossary object).
--   * node_source_references: locator/locator_detail were swapped to match
--     convention (locator = full printed caption; locator_detail = terse
--     English usage note). Bảng 2/6/7 given their own reference rows
--     (established convention is one row per distinct source).
--
-- Node type mapping (per legend colors in the source flowchart):
--   green  (Start Node)          -> START
--   yellow (Condition Check)     -> CONDITION
--   blue   (Trigger/Input Node)  -> INFERENCE (applies a context_patch)
--   pink   (Link Node)           -> LINK
--   gray   (glossary/legend box) -> GLOBAL (global_config)
--
-- Safe to run against an empty/staging database. Wrap in a transaction.
-- Use: cmd /c "docker compose exec -T postgres psql -U cdss -d cdss < backups\tree8.sql"
--

-- ============================================================
-- 1. Tree
-- ============================================================
INSERT INTO public.decision_trees (
        "id",
        "tree_key",
        "name_en",
        "name_vi",
        "created_at",
        "updated_at"
    )
VALUES (
        gen_random_uuid(),
        'hypertension-type-2-diabetes',
        'Hypertension With Type 2 Diabetes',
        'THA + Đái Tháo Đường Týp 2',
        now(),
        now()
    );
-- ============================================================
-- 2. Nodes
-- ============================================================
WITH tree_ctx AS (
    SELECT id AS tree_id
    FROM public.decision_trees
    WHERE tree_key = 'hypertension-type-2-diabetes'
),
node_seed (
    node_key,
    node_type,
    text_en,
    text_vi,
    condition_definition,
    context_patch,
    action_payload,
    global_config,
    link_target_tree_key,
    link_target_node_key,
    display_order
) AS (
    VALUES (
            'T8_START_BP_TARGET_STATUS',
            'START',
            'Tree 3: Blood pressure threshold and treatment target',
            'Cây 3: Ngưỡng huyết áp và đích điều trị',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            0
        ),
        (
            'T8_C_BELOW_TARGET',
            'CONDITION',
            'SBP < 130 mmHg and DBP < 85 mmHg',
            'HATT < 130 mmHg và HATTr < 85 mmHg',
            '{"all":[{"path":"input.current_clinic_sbp","op":"lt","value":130},{"path":"input.current_clinic_dbp","op":"lt","value":85}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            1
        ),
        (
            'T8_C_ABOVE_TARGET',
            'CONDITION',
            'SBP >= 130 mmHg or DBP >= 85 mmHg',
            'HATT >= 130 mmHg hoặc HATTr >= 85 mmHg',
            '{"any":[{"path":"input.current_clinic_sbp","op":"gte","value":130},{"path":"input.current_clinic_dbp","op":"gte","value":85}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            2
        ),
        (
            'T8_INF_REGIMEN_OPTIONS',
            'INFERENCE',
            'A + C, or A + D (ACE inhibitor/ARB + calcium-channel blocker, or ACE inhibitor/ARB + thiazide-like diuretic)',
            'A + C, hoặc A + D (ƯCMC/CTTA + CKCa, hoặc ƯCMC/CTTA + LT Thiazide-like)',
            NULL::jsonb,
            '{"treatment_preferences":{"combination_options":[["A","C"],["A","D"]]}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            3
        ),
        (
            'T8_C_HAS_CV_RISK',
            'CONDITION',
            'Has atherosclerotic cardiovascular disease (coronary artery disease, stroke, or cardiovascular disease) or high cardiovascular risk',
            'Có bệnh tim mạch do xơ vữa (bệnh mạch vành, đột quỵ, bệnh tim mạch) hoặc nguy cơ tim mạch cao',
            '{"any":[{"path":"input.has_coronary_artery_disease","op":"eq","value":true},{"path":"input.has_stroke","op":"eq","value":true},{"path":"input.has_cardiovascular_disease","op":"eq","value":true},{"path":"context.risk.level","op":"eq","value":"HIGH"}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            4
        ),
        (
            'T8_C_NO_CV_RISK',
            'CONDITION',
            'No atherosclerotic cardiovascular disease and not high cardiovascular risk',
            'Không có bệnh tim mạch do xơ vữa và không thuộc nhóm nguy cơ tim mạch cao',
            '{"not":{"any":[{"path":"input.has_coronary_artery_disease","op":"eq","value":true},{"path":"input.has_stroke","op":"eq","value":true},{"path":"input.has_cardiovascular_disease","op":"eq","value":true},{"path":"context.risk.level","op":"eq","value":"HIGH"}]}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            5
        ),
        (
            'T8_INF_ADD_SGLT2I_GLP1RA',
            'INFERENCE',
            'Add SGLT2i or GLP-1RA',
            'Bổ sung SGLT2i hoặc GLP-1RA',
            NULL::jsonb,
            '{"treatment_preferences":{"additional_drug_classes":["SGLT2_INHIBITOR","GLP1_RECEPTOR_AGONIST"]}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            6
        ),
        (
            'T8_INF_MAINTAIN_REGIMEN',
            'INFERENCE',
            'Maintain current regimen',
            'Duy trì phác đồ',
            NULL::jsonb,
            '{"treatment":{"status":"MAINTAIN_CURRENT_REGIMEN"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            7
        ),
        (
            'T8_LINK_A_ESSENTIAL_TREATMENT_STRATEGY',
            'LINK',
            'Tree 4: Essential treatment strategy',
            'Cây 4: Chiến lược điều trị thiết yếu',
            '{"path":"input.facility_capability","op":"eq","value":"LIMITED_RESOURCES"}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            'essential-treatment-strategy',
            NULL::text,
            8
        ),
        (
            'T8_LINK_A_OPTIMAL_TREATMENT_STRATEGY',
            'LINK',
            'Tree 5: Optimal treatment strategy',
            'Cây 5: Chiến lược điều trị tối ưu',
            '{"path":"input.facility_capability","op":"eq","value":"FULL_RESOURCES"}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            'optimal-treatment-strategy',
            NULL::text,
            9
        ),
        (
            'T8_LINK_B_ESSENTIAL_TREATMENT_STRATEGY',
            'LINK',
            'Tree 4: Essential treatment strategy',
            'Cây 4: Chiến lược điều trị thiết yếu',
            '{"path":"input.facility_capability","op":"eq","value":"LIMITED_RESOURCES"}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            'essential-treatment-strategy',
            NULL::text,
            10
        ),
        (
            'T8_LINK_B_OPTIMAL_TREATMENT_STRATEGY',
            'LINK',
            'Tree 5: Optimal treatment strategy',
            'Cây 5: Chiến lược điều trị tối ưu',
            '{"path":"input.facility_capability","op":"eq","value":"FULL_RESOURCES"}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            'optimal-treatment-strategy',
            NULL::text,
            11
        ),
        (
            'T8_GLOBAL_ABBREVIATION_GLOSSARY',
            'GLOBAL',
            'Abbreviation glossary',
            'Chú giải viết tắt',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            '{"kind":"ABBREVIATION_GLOSSARY","purpose":"Chú giải các chữ viết tắt nhóm thuốc dùng trong Cây 8 (hệ thống A/B/C/D), theo chú thích Bảng 18.","entries":{"1_A_uc_che_he_RAS":{"label":"A: ức chế hệ RAS","UCMC":"ức chế men chuyển","CTTA":"chẹn thụ thể angiotensin II","ARNI":"chẹn thụ thể Angiotensine-neprisyline"},"4_B_chen_Beta":{"label":"B: chẹn Beta","CB":"chẹn Beta"},"3_C_chen_kenh_Canxi":{"label":"C: chẹn kênh Canxi","CKCa":"chẹn kênh Canxi"},"2_D_loi_tieu":{"label":"D: lợi tiểu","LT":"lợi tiểu"},"6_MRA":{"label":"MRA: thuốc đối kháng thụ thể mineralocorticoid"},"5_SGLT2i":{"label":"SGLT2i: thuốc ức chế đồng vận chuyển Natri-glucose 2"}}}'::jsonb,
            NULL::text,
            NULL::text,
            99
        )
)
INSERT INTO public.decision_nodes (
        "id",
        "tree_id",
        "node_key",
        "node_type",
        "text_en",
        "text_vi",
        "condition_definition",
        "context_patch",
        "action_payload",
        "global_config",
        "link_target_tree_key",
        "link_target_node_key",
        "display_order",
        "created_at",
        "updated_at"
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
    SELECT id AS tree_id
    FROM public.decision_trees
    WHERE tree_key = 'hypertension-type-2-diabetes'
),
edge_seed (
    from_node_key,
    to_node_key,
    traversal_order
) AS (
    VALUES (
            'T8_START_BP_TARGET_STATUS',
            'T8_C_BELOW_TARGET',
            1
        ),
        (
            'T8_START_BP_TARGET_STATUS',
            'T8_C_ABOVE_TARGET',
            2
        ),
        (
            'T8_C_BELOW_TARGET',
            'T8_LINK_A_ESSENTIAL_TREATMENT_STRATEGY',
            1
        ),
        (
            'T8_C_BELOW_TARGET',
            'T8_LINK_A_OPTIMAL_TREATMENT_STRATEGY',
            2
        ),
        (
            'T8_C_ABOVE_TARGET',
            'T8_INF_REGIMEN_OPTIONS',
            1
        ),
        (
            'T8_INF_REGIMEN_OPTIONS',
            'T8_C_HAS_CV_RISK',
            1
        ),
        (
            'T8_INF_REGIMEN_OPTIONS',
            'T8_C_NO_CV_RISK',
            2
        ),
        (
            'T8_C_HAS_CV_RISK',
            'T8_INF_ADD_SGLT2I_GLP1RA',
            1
        ),
        ('T8_C_NO_CV_RISK', 'T8_INF_MAINTAIN_REGIMEN', 1),
        (
            'T8_INF_ADD_SGLT2I_GLP1RA',
            'T8_LINK_B_ESSENTIAL_TREATMENT_STRATEGY',
            1
        ),
        (
            'T8_INF_ADD_SGLT2I_GLP1RA',
            'T8_LINK_B_OPTIMAL_TREATMENT_STRATEGY',
            2
        ),
        (
            'T8_INF_MAINTAIN_REGIMEN',
            'T8_LINK_B_ESSENTIAL_TREATMENT_STRATEGY',
            1
        ),
        (
            'T8_INF_MAINTAIN_REGIMEN',
            'T8_LINK_B_OPTIMAL_TREATMENT_STRATEGY',
            2
        )
)
INSERT INTO public.decision_edges (
        "id",
        "from_node_id",
        "to_node_id",
        "traversal_order"
    )
SELECT gen_random_uuid(),
    from_node.id,
    to_node.id,
    edge_seed.traversal_order
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
    SELECT id AS tree_id
    FROM public.decision_trees
    WHERE tree_key = 'hypertension-type-2-diabetes'
),
reference_seed (
    node_key,
    source_title,
    section_path,
    locator,
    locator_detail,
    printed_page_numbers,
    pdf_page_numbers,
    reference_note,
    reference_order
) AS (
    VALUES (
            'T8_START_BP_TARGET_STATUS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "1.5", "title": "Phân tầng nguy cơ tim mạch trong tăng huyết áp"}]'::jsonb,
            'Bảng 2. Phân tầng nguy cơ trong tăng huyết áp (2)',
            'Background risk-stratification context carried over from Tree 3, before branching into the diabetes-specific Bảng 18 strategy.',
            ARRAY [11]::smallint [],
            ARRAY [11]::smallint [],
            'Tiếp nối bối cảnh phân tầng nguy cơ từ Cây 3.',
            1
        ),
        (
            'T8_START_BP_TARGET_STATUS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.1", "title": "Ngưỡng huyết áp ban đầu cần điều trị và ranh giới đích điều trị tăng huyết áp"}]'::jsonb,
            'Bảng 6. Ngưỡng huyết áp phòng khám cho điều trị tăng huyết áp theo nhóm tuổi',
            'General clinic-BP treatment threshold by age, inherited from Tree 3 before this diabetes-specific branch.',
            ARRAY [15]::smallint [],
            ARRAY [17]::smallint [],
            'Ngưỡng điều trị chung theo nhóm tuổi, kế thừa từ Cây 3.',
            2
        ),
        (
            'T8_START_BP_TARGET_STATUS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.1", "title": "Ngưỡng huyết áp ban đầu cần điều trị và ranh giới đích điều trị tăng huyết áp"}]'::jsonb,
            'Bảng 7. Mục tiêu huyết áp phòng khám trong điều trị tăng huyết áp theo nhóm tuổi',
            'General clinic-BP treatment target by age, inherited from Tree 3 before this diabetes-specific branch.',
            ARRAY [16]::smallint [],
            ARRAY [18]::smallint [],
            'Đích điều trị chung theo nhóm tuổi, kế thừa từ Cây 3.',
            3
        ),
        (
            'T8_C_BELOW_TARGET',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Clinic BP threshold for hypertension with type 2 diabetes is >=130/85 mmHg; below-target branch.',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Ngưỡng HA phòng khám ở bệnh nhân THA kèm đái tháo đường týp 2 khi >= 130/85 mmHg.',
            1
        ),
        (
            'T8_C_ABOVE_TARGET',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Clinic BP threshold for hypertension with type 2 diabetes is >=130/85 mmHg; at/above-target branch.',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Ngưỡng HA phòng khám ở bệnh nhân THA kèm đái tháo đường týp 2 khi >= 130/85 mmHg.',
            1
        ),
        (
            'T8_INF_REGIMEN_OPTIONS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Combination strategy should include one RAS-inhibitor class (A: ACEI or ARB) and one calcium-channel-blocker or thiazide-like-diuretic class (C or D). Matching Trees 4/5''s own pattern, the specific agent within each class (e.g. ACEI vs ARB) is resolved downstream against contraindications in Tree 6 (drug-combination), not decided here.',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Chiến lược điều trị nên bao gồm một nhóm thuốc ức chế RAS và một nhóm thuốc chẹn kênh canxi hoặc lợi tiểu thiazide-like.',
            1
        ),
        (
            'T8_C_HAS_CV_RISK',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'SGLT2i/GLP-1RA is prioritized when atherosclerotic cardiovascular disease and/or high risk is present.',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Điều trị hạ glucose máu với SGLT2-i hoặc GLP-1 RA được ưu tiên khi có bệnh tim mạch do xơ vữa và/hoặc nguy cơ cao.',
            1
        ),
        (
            'T8_C_NO_CV_RISK',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Complement of the SGLT2i/GLP-1RA trigger: no atherosclerotic cardiovascular disease and not high risk.',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Phần bù của điều kiện kích hoạt SGLT2-i/GLP-1 RA: không có bệnh tim mạch do xơ vữa và không thuộc nhóm nguy cơ cao.',
            1
        ),
        (
            'T8_INF_ADD_SGLT2I_GLP1RA',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Glucose-lowering therapy with SGLT2i or GLP-1RA is prioritized for its demonstrated cardiovascular benefit.',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Điều trị hạ glucose máu với SGLT2-i hoặc GLP-1 RA được ưu tiên với những lợi ích bệnh tim mạch đã được chứng minh.',
            1
        ),
        (
            'T8_INF_MAINTAIN_REGIMEN',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'No indication to add SGLT2i/GLP-1RA: continue the current RAS-inhibitor + CCB/diuretic regimen.',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Không có chỉ định bổ sung SGLT2-i/GLP-1 RA: tiếp tục phác đồ ức chế RAS + CKCa/lợi tiểu hiện tại.',
            1
        ),
        (
            'T8_LINK_A_ESSENTIAL_TREATMENT_STRATEGY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Exit point of the "at target" branch: continue the essential treatment strategy (limited-resource facility).',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Điểm thoát của nhánh "đạt đích": tiếp tục chiến lược điều trị thiết yếu.',
            1
        ),
        (
            'T8_LINK_A_OPTIMAL_TREATMENT_STRATEGY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Exit point of the "at target" branch: continue the optimal treatment strategy (full-resource facility).',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Điểm thoát của nhánh "đạt đích": tiếp tục chiến lược điều trị tối ưu.',
            1
        ),
        (
            'T8_LINK_B_ESSENTIAL_TREATMENT_STRATEGY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Exit point of the "not at target" branch: continue the essential treatment strategy (limited-resource facility).',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Điểm thoát của nhánh "chưa đạt đích": tiếp tục chiến lược điều trị thiết yếu.',
            1
        ),
        (
            'T8_LINK_B_OPTIMAL_TREATMENT_STRATEGY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2)',
            'Exit point of the "not at target" branch: continue the optimal treatment strategy (full-resource facility).',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Điểm thoát của nhánh "chưa đạt đích": tiếp tục chiến lược điều trị tối ưu.',
            1
        ),
        (
            'T8_GLOBAL_ABBREVIATION_GLOSSARY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.7.1", "title": "Tăng huyết áp và Đái tháo đường týp 2"}]'::jsonb,
            'Bảng 18. Chiến lược điều trị tăng huyết áp kèm theo đái tháo đường (2), chú thích',
            'Footnote abbreviation glossary for the drug classes named in Bảng 18.',
            ARRAY [32]::smallint [],
            ARRAY [34]::smallint [],
            'Chú thích Bảng 18: RAS: Hệ renin-angiotensin-aldosterone; GLP-1 RA: thuốc đồng vận thụ thể GLP-1; SGLT2i: Thuốc ức chế SGLT2.',
            1
        )
)
INSERT INTO public.node_source_references (
        "id",
        "node_id",
        "source_title",
        "section_path",
        "locator",
        "locator_detail",
        "printed_page_numbers",
        "pdf_page_numbers",
        "reference_note",
        "reference_order"
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

-- ================================================================
-- Tree 9: hypertension-coronary-artery-disease (source: seed_hypertension_coronary_artery_disease.sql)
-- ================================================================
COPY public.decision_trees ("id", "tree_key", "name_en", "name_vi", "created_at", "updated_at") FROM stdin;
c185afaa-623f-5f0d-b8b2-792899dee988	hypertension-coronary-artery-disease	Hypertension + Coronary Artery Disease	Cây 9: THA + bệnh mạch vành	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
\.

COPY public.decision_nodes ("id", "tree_id", "node_key", "node_type", "text_en", "text_vi", "condition_definition", "context_patch", "action_payload", "global_config", "link_target_tree_key", "link_target_node_key", "display_order", "created_at", "updated_at") FROM stdin;
d4a79b1e-2fd3-5526-ba61-0afcc5e4549e	c185afaa-623f-5f0d-b8b2-792899dee988	T9_START	START	Tree 3: Blood Pressure Thresholds and Targets	Cây 3 Ngưỡng huyết áp và đích điều trị	\N	\N	\N	\N	\N	\N	1	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
8b75cbfa-8d26-519f-a80b-d346aa4c37fb	c185afaa-623f-5f0d-b8b2-792899dee988	T9_C_BP1	CONDITION	18-69 years and SBP >= 130 or DBP >= 85	18-69 tuổi và HATT >= 130 mmHg HATTr >= 85 mmHg	{"all": [{"all": [{"op": "gte", "path": "input.age", "value": 18}, {"op": "lte", "path": "input.age", "value": 69}]}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}]}	\N	\N	\N	\N	\N	2	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
103a7134-7357-55fd-922e-a4bfb6d3fe11	c185afaa-623f-5f0d-b8b2-792899dee988	T9_C_BP2	CONDITION	>70 years and SBP >= 140 or DBP >= 90	>70 tuổi và HATT >= 140 mmHg HATTr >= 90 mmHg	{"all": [{"op": "gt", "path": "input.age", "value": 70}, {"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 140}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 90}]}]}	\N	\N	\N	\N	\N	3	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
0eca67b2-9c2e-5614-993f-951e970b34ef	c185afaa-623f-5f0d-b8b2-792899dee988	T9_C_BP3	CONDITION	18-69 years and SBP < 130 and DBP < 85	18-69 tuổi và HATT < 130 mmHg HATTr < 85 mmHg	{"all": [{"op": "gte", "path": "input.age", "value": 18}, {"op": "lte", "path": "input.age", "value": 69}, {"op": "lt", "path": "input.current_clinic_sbp", "value": 130}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 85}]}	\N	\N	\N	\N	\N	4	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
d4050ff3-58a2-53b2-ba4a-876f8d3fc3e7	c185afaa-623f-5f0d-b8b2-792899dee988	T9_C_BP4	CONDITION	>70 years and SBP < 140 and DBP < 90	>70 tuổi và HATT < 140 mmHg HATTr < 90 mmHg	{"all": [{"op": "gt", "path": "input.age", "value": 70}, {"op": "lt", "path": "input.current_clinic_sbp", "value": 140}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 90}]}	\N	\N	\N	\N	\N	5	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
f551f2cf-18f7-5261-a322-a02e58f1bf30	c185afaa-623f-5f0d-b8b2-792899dee988	T9_C_AMI	CONDITION	Myocardial Infarction or Acute Coronary Syndrome	Nhồi máu cơ tim hoặc hội chứng vành cấp	{"op": "eq", "path": "input.has_mi_acs", "value": true}	\N	\N	\N	\N	\N	6	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
d26f0496-b35f-5909-8975-c2329b388ea9	c185afaa-623f-5f0d-b8b2-792899dee988	T9_C_CCS_ANGINA	CONDITION	Chronic Coronary Syndrome with Angina	Hội chứng vành mạn có cơn đau thắt ngực	{"op": "eq", "path": "input.has_ccs_angina", "value": true}	\N	\N	\N	\N	\N	7	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
6de65559-da01-52b5-94e5-a2a916e248e8	c185afaa-623f-5f0d-b8b2-792899dee988	T9_C_CCS_REVASC	CONDITION	Chronic Coronary Syndrome after Revascularization	Hội chứng vành mạn sau tái thông	{"op": "eq", "path": "input.has_ccs_revasc", "value": true}	\N	\N	\N	\N	\N	8	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
e178b23e-f8e8-5d9f-8207-34404155166b	c185afaa-623f-5f0d-b8b2-792899dee988	T9_C_CABG	CONDITION	Post CABG	Sau phẫu thuật bắc cầu vành CABG	{"op": "eq", "path": "input.has_cabg", "value": true}	\N	\N	\N	\N	\N	9	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
6299ea87-2ba4-52b4-9752-bbd2a796e0ff	c185afaa-623f-5f0d-b8b2-792899dee988	T9_A_B_3Y	INFERENCE	Combine Beta-blocker for 3 years	Phối hợp thuốc B trong 3 năm	\N	{"regimen_modifier": "add_beta_blocker_3_years"}	{"action_type": "BETA_BLOCKER_3_YEARS"}	\N	\N	\N	10	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
b2f92cb6-82fc-52ba-a4ca-54257fc2f0b7	c185afaa-623f-5f0d-b8b2-792899dee988	T9_A_B_OR_C	INFERENCE	Combine Beta-blocker or CCB	Phối hợp thuốc B hoặc C	\N	{"regimen_modifier": "add_beta_blocker_or_ccb"}	{"action_type": "BETA_BLOCKER_OR_CCB"}	\N	\N	\N	11	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
ef39acd8-3c32-5eda-bca8-a6c79adfcaf2	c185afaa-623f-5f0d-b8b2-792899dee988	T9_A_NO_B	INFERENCE	No routine indication for Beta-blocker	Không có chỉ định thuốc B thường quy	\N	{"regimen_modifier": "no_routine_beta_blocker"}	{"action_type": "NO_ROUTINE_BETA_BLOCKER"}	\N	\N	\N	12	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
bc668dbe-04db-5f5d-a80d-fd1a51f5037b	c185afaa-623f-5f0d-b8b2-792899dee988	T9_A_B_EARLY	INFERENCE	Start Beta-blocker as early as possible	Bắt đầu thuốc B sớm nhất có thể	\N	{"regimen_modifier": "early_beta_blocker"}	{"action_type": "EARLY_BETA_BLOCKER"}	\N	\N	\N	13	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
de89d76b-1556-5e3c-b13d-902195434de3	c185afaa-623f-5f0d-b8b2-792899dee988	T9_LINK_4_5	LINK	Tree 4: Essential Strategy or Tree 5: Optimal Strategy	Cây 4: Chiến lược điều trị thiết yếu hoặc Cây 5: Chiến lược điều trị tối ưu	\N	\N	\N	\N	essential-optimal-strategy	\N	14	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
c92773f1-5078-502d-b5eb-a9a8c72f9b52	c185afaa-623f-5f0d-b8b2-792899dee988	T9_G_DRUGS	GLOBAL	First-line drugs: A + B. Add C, D or MRA when necessary	Thuốc chỉ định hàng đầu: A + B thêm thuốc C, D hoặc MRA khi cần	\N	\N	\N	{"first_line_drugs": ["A", "B"], "add_on_drugs": ["C", "D", "MRA"]}	\N	\N	15	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
\.

COPY public.decision_edges ("id", "from_node_id", "to_node_id", "traversal_order") FROM stdin;
d1dde666-6bc9-558f-b5f3-32de9f51c365	d4a79b1e-2fd3-5526-ba61-0afcc5e4549e	8b75cbfa-8d26-519f-a80b-d346aa4c37fb	1
34aac5e5-71d5-5f2e-a9b0-aa85b828c887	d4a79b1e-2fd3-5526-ba61-0afcc5e4549e	103a7134-7357-55fd-922e-a4bfb6d3fe11	2
3196bcf2-a70e-57a4-b3f1-ea1b2c1e31cf	d4a79b1e-2fd3-5526-ba61-0afcc5e4549e	0eca67b2-9c2e-5614-993f-951e970b34ef	3
e0d6cefe-8a23-5104-b12e-c48071b4633a	d4a79b1e-2fd3-5526-ba61-0afcc5e4549e	d4050ff3-58a2-53b2-ba4a-876f8d3fc3e7	4
486a05a6-3946-569d-bb93-39059f287955	8b75cbfa-8d26-519f-a80b-d346aa4c37fb	f551f2cf-18f7-5261-a322-a02e58f1bf30	1
a7a360e8-8941-591b-9429-1e2754e9aeca	8b75cbfa-8d26-519f-a80b-d346aa4c37fb	d26f0496-b35f-5909-8975-c2329b388ea9	2
0c8f0fb6-9c0f-50dc-975e-5038bd665202	8b75cbfa-8d26-519f-a80b-d346aa4c37fb	6de65559-da01-52b5-94e5-a2a916e248e8	3
26a29ff7-6426-552e-8bee-ace4f234ca1e	8b75cbfa-8d26-519f-a80b-d346aa4c37fb	e178b23e-f8e8-5d9f-8207-34404155166b	4
beee2c29-de53-5a58-a91d-8dba76522a72	103a7134-7357-55fd-922e-a4bfb6d3fe11	f551f2cf-18f7-5261-a322-a02e58f1bf30	1
25b975f1-3232-5263-8f5e-26e81e7c3fda	103a7134-7357-55fd-922e-a4bfb6d3fe11	d26f0496-b35f-5909-8975-c2329b388ea9	2
0e3ca9b1-e038-5377-9f4d-0de3d703b3ef	103a7134-7357-55fd-922e-a4bfb6d3fe11	6de65559-da01-52b5-94e5-a2a916e248e8	3
8a0de5cc-fce5-55b1-b98b-5c170a49ecd6	103a7134-7357-55fd-922e-a4bfb6d3fe11	e178b23e-f8e8-5d9f-8207-34404155166b	4
f02c666c-2fa8-56a7-a8ec-16c4fa0e1279	0eca67b2-9c2e-5614-993f-951e970b34ef	de89d76b-1556-5e3c-b13d-902195434de3	1
28765cdf-5c26-5be5-baec-da1903ff58e7	d4050ff3-58a2-53b2-ba4a-876f8d3fc3e7	de89d76b-1556-5e3c-b13d-902195434de3	1
4fa5272a-e55b-575c-97dc-41c1fffdd7a8	f551f2cf-18f7-5261-a322-a02e58f1bf30	6299ea87-2ba4-52b4-9752-bbd2a796e0ff	1
fc87d331-7753-507f-b254-cf8f0e048988	d26f0496-b35f-5909-8975-c2329b388ea9	b2f92cb6-82fc-52ba-a4ca-54257fc2f0b7	1
7ade7690-1566-57d2-ad0f-e0bbae54c049	6de65559-da01-52b5-94e5-a2a916e248e8	ef39acd8-3c32-5eda-bca8-a6c79adfcaf2	1
d13e07b4-3771-539d-a3c4-f7224cfd25a9	e178b23e-f8e8-5d9f-8207-34404155166b	bc668dbe-04db-5f5d-a80d-fd1a51f5037b	1
1a1582ce-e757-5d37-8e27-65ac488187cd	6299ea87-2ba4-52b4-9752-bbd2a796e0ff	de89d76b-1556-5e3c-b13d-902195434de3	1
efe639d5-0fdb-5d06-826c-e3b960beeb7d	b2f92cb6-82fc-52ba-a4ca-54257fc2f0b7	de89d76b-1556-5e3c-b13d-902195434de3	1
f40d14d7-364c-5418-b791-bceda4a77b1f	ef39acd8-3c32-5eda-bca8-a6c79adfcaf2	de89d76b-1556-5e3c-b13d-902195434de3	1
d2b8bd11-6a7f-5c6e-b8ba-4c6de0a40f73	bc668dbe-04db-5f5d-a80d-fd1a51f5037b	de89d76b-1556-5e3c-b13d-902195434de3	1
\.

COPY public.node_source_references ("id", "node_id", "source_title", "section_path", "locator", "locator_detail", "printed_page_numbers", "pdf_page_numbers", "reference_note", "reference_order") FROM stdin;
2536a09d-9952-5323-9999-66e45b9d0b4f	d4a79b1e-2fd3-5526-ba61-0afcc5e4549e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
d579f79d-50da-55c2-b0ef-e2121a6b3dba	8b75cbfa-8d26-519f-a80b-d346aa4c37fb	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
511c3ec6-61e4-509a-9964-98c956e3f734	103a7134-7357-55fd-922e-a4bfb6d3fe11	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
a2cc2994-d716-55d4-99e5-d3d11c8f83f2	0eca67b2-9c2e-5614-993f-951e970b34ef	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
1e708b9f-4976-5ea4-b07d-fdfe9a57ad16	d4050ff3-58a2-53b2-ba4a-876f8d3fc3e7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
1aadc806-a790-5269-aa6d-cfd8e8ef79c7	f551f2cf-18f7-5261-a322-a02e58f1bf30	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
e4c9819a-ad53-564f-80e8-5c2dffffd38c	d26f0496-b35f-5909-8975-c2329b388ea9	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
8c2a4899-b814-556e-acf8-762b5adc4903	6de65559-da01-52b5-94e5-a2a916e248e8	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
1319318a-c0bf-59d8-a373-172544ef2a38	e178b23e-f8e8-5d9f-8207-34404155166b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
d81384bc-bd29-5307-9042-38417d2619f8	6299ea87-2ba4-52b4-9752-bbd2a796e0ff	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
cecab4a3-57e2-5199-8826-1f5549f0cbc6	b2f92cb6-82fc-52ba-a4ca-54257fc2f0b7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
31882bf4-1488-5904-8267-046f668f0128	ef39acd8-3c32-5eda-bca8-a6c79adfcaf2	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
507db48f-5edf-5e1e-b65f-8c0336b33ec5	bc668dbe-04db-5f5d-a80d-fd1a51f5037b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
7d316700-9551-5c6a-8557-cb92f6f7a023	de89d76b-1556-5e3c-b13d-902195434de3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
e1989e2b-d545-5022-9e71-e7b02ca1a852	c92773f1-5078-502d-b5eb-a9a8c72f9b52	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.2. T\u0103ng huy\u1ebft \u00e1p v\u00e0 B\u1ec7nh m\u1ea1ch v\u00e0nh"]	Bảng 19. Điều trị tăng huyết áp có bệnh mạch vành	\N	{33}	{35}	\N	1
\.


-- ================================================================
-- Tree 10: hypertension-heart-failure (source: seed_hypertension_heart_failure.sql)
-- ================================================================
COPY public.decision_trees ("id", "tree_key", "name_en", "name_vi", "created_at", "updated_at") FROM stdin;
1c456604-8db8-59b5-8811-6e638ca7ab6e	hypertension-heart-failure	Hypertension + Heart Failure	Cây 10: THA + suy tim	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
\.

COPY public.decision_nodes ("id", "tree_id", "node_key", "node_type", "text_en", "text_vi", "condition_definition", "context_patch", "action_payload", "global_config", "link_target_tree_key", "link_target_node_key", "display_order", "created_at", "updated_at") FROM stdin;
0878afaa-2a79-5188-94f6-c27d064f9402	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_START	START	Tree 3: Blood Pressure Thresholds and Targets	Cây 3 Ngưỡng huyết áp và đích điều trị	\N	\N	\N	\N	\N	\N	1	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
9bc0e11b-2f69-5420-a680-6165ec1e61fd	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_C_BP1	CONDITION	SBP < 130 and DBP < 85	HATT < 130 mmHg và HATTr < 85 mmHg	{"all": [{"op": "lt", "path": "input.current_clinic_sbp", "value": 130}, {"op": "lt", "path": "input.current_clinic_dbp", "value": 85}]}	\N	\N	\N	\N	\N	2	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
0d880900-1578-512f-993d-012bf287ed9c	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_C_BP2	CONDITION	SBP >= 130 or DBP >= 85	HATT >= 130 mmHg Hoặc HATTr >= 85 mmHg	{"any": [{"op": "gte", "path": "input.current_clinic_sbp", "value": 130}, {"op": "gte", "path": "input.current_clinic_dbp", "value": 85}]}	\N	\N	\N	\N	\N	3	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
31a12b62-51e6-595b-bb87-5e214f2f8f97	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_A_EVAL_EF	INFERENCE	Evaluate ejection fraction (EF) and heart structure	Đánh giá phân suất tống máu(EF) và cấu trúc tim	\N	\N	{"action_type": "EVALUATE_EF_AND_STRUCTURE"}	\N	\N	\N	4	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
4e8ed9cf-1693-5ca9-9c3e-6c1abbfc8143	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_C_HFREF	CONDITION	Heart Failure with reduced EF (HFrEF)	Suy tim EF giảm (HFrEF)	{"op": "eq", "path": "input.has_hfref", "value": true}	\N	\N	\N	\N	\N	5	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
3bef0da4-1b69-573b-b077-07a8d46a1584	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_C_HFMREF	CONDITION	Heart Failure with mildly reduced EF (HFmrEF)	Suy tim EF giảm nhẹ (HFmrEF)	{"op": "eq", "path": "input.has_hfmref", "value": true}	\N	\N	\N	\N	\N	6	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
4227dbf8-f310-59cc-9f5f-75bdf08459c8	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_C_HFPEF	CONDITION	Heart Failure with preserved EF (HFpEF)	Suy tim EF bảo tồn (HFpEF)	{"op": "eq", "path": "input.has_hfpef", "value": true}	\N	\N	\N	\N	\N	7	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
49dfc288-d480-5262-a05e-9edad085b25a	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_C_LVH	CONDITION	Left ventricular hypertrophy (LVH)	Phì đại thất trái (LVH)	{"op": "eq", "path": "input.has_lvh", "value": true}	\N	\N	\N	\N	\N	8	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
877ac137-c482-5091-9494-bd882b0cf7cd	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_HFREF	INFERENCE	Combine A + B + D and/or Aldosterone antagonist + SGLT2i. B: (bisoprolol, carvedilol, metoprolol, nebivolol)	Phối hợp A + B + D và/hoặc kháng aldosterone + SGLT2i. B: (bisoprolol, carvedilol, metoprolol, nebivolol)	\N	\N	{"action_type": "COMBINE_ABD_ALDO_SGLT2I"}	\N	\N	\N	9	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
465565d5-433a-563c-8b06-78b98785b814	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_HFMREF_1	INFERENCE	Combine D and SGLT2i and Aldosterone antagonist	Phối hợp D và SGLT2i và kháng Aldosterone	\N	\N	{"action_type": "COMBINE_D_SGLT2I_ALDO"}	\N	\N	\N	10	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
339634e2-d9f3-5366-b8b0-60cba53abba6	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_HFMREF_2	INFERENCE	Add A (ARNI or CTTA or UCMC)	Phối hợp thêm A (ARNI hoặc CTTA hoặc UCMC)	\N	\N	{"action_type": "ADD_A_ARNI_CTTA_UCMC"}	\N	\N	\N	11	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
30cee5c4-7eba-556e-8b51-dea56475179e	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_HFPEF_1	INFERENCE	Combine D and SGLT2i and Aldosterone antagonist	Phối hợp D và SGLT2i và kháng Aldosterone	\N	\N	{"action_type": "COMBINE_D_SGLT2I_ALDO"}	\N	\N	\N	12	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
debdecef-88df-5601-8cfc-b5eb91b8b08f	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_HFPEF_2	INFERENCE	Add A (ARNI and CTTA)	Phối hợp thêm A (ARNI và CTTA)	\N	\N	{"action_type": "ADD_A_ARNI_CTTA"}	\N	\N	\N	13	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
5880accb-c184-5bfe-a6c0-78845c4ba7be	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_LVH	INFERENCE	Combine A + C or A + D	Phối hợp A + C hoặc A + D	\N	\N	{"action_type": "COMBINE_AC_OR_AD"}	\N	\N	\N	14	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
93fcb99c-db2a-53b3-82f7-a1d4ecb58f0e	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_C_TARGET_NOT_REACHED	CONDITION	BP target not reached	HA không đạt đích điều trị	{"op": "eq", "path": "input.bp_target_reached", "value": false}	\N	\N	\N	\N	\N	15	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
d8271d2d-79ff-50e5-be69-ee29cc68f432	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_C_TARGET_REACHED	CONDITION	BP target reached	HA đã đạt đích điều trị	{"op": "eq", "path": "input.bp_target_reached", "value": true}	\N	\N	\N	\N	\N	16	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
3f8ae7a2-1a20-5a7a-8f80-0abb5eed489e	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_ADD_CCB	INFERENCE	Add Dihydropyridine CCB	Thêm CKCa nhóm Dihydropyridine	\N	\N	{"action_type": "ADD_DIHYDROPYRIDINE_CCB"}	\N	\N	\N	17	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
ca0c7576-4117-510d-b28b-6eff717791f7	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_ADJUST	INFERENCE	Adjust drug dosage and monitor	Điều chỉnh liều lượng thuốc và theo dõi	\N	\N	{"action_type": "ADJUST_DOSAGE_AND_MONITOR"}	\N	\N	\N	18	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
1208d7cb-f28c-5131-afad-9249828c164c	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_I_MAINTAIN	INFERENCE	Maintain regimen	Duy trì phác đồ	\N	\N	{"action_type": "MAINTAIN_REGIMEN"}	\N	\N	\N	19	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
a1b2c3d4-e5f6-5a7b-8c9d-0e1f2a3b4c5d	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_LINK_ESSENTIAL	LINK	Tree 4: Essential Treatment Strategy	Cây 4: Chiến lược điều trị thiết yếu	\N	\N	\N	\N	essential-treatment-strategy	\N	20	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
b2c3d4e5-f6a7-5b8c-9d0e-1f2a3b4c5d6e	1c456604-8db8-59b5-8811-6e638ca7ab6e	T10_LINK_OPTIMAL	LINK	Tree 5: Optimal Treatment Strategy	Cây 5: Chiến lược điều trị tối ưu	\N	\N	\N	\N	optimal-treatment-strategy	\N	21	2026-07-05 00:00:00.000000+00	2026-07-05 00:00:00.000000+00
\.

COPY public.decision_edges ("id", "from_node_id", "to_node_id", "traversal_order") FROM stdin;
17ec4ab3-c516-5bbc-8d3f-7939b2750532	0878afaa-2a79-5188-94f6-c27d064f9402	9bc0e11b-2f69-5420-a680-6165ec1e61fd	1
4da9327a-b69b-56ca-a9e1-30e035facb51	0878afaa-2a79-5188-94f6-c27d064f9402	0d880900-1578-512f-993d-012bf287ed9c	2
1ec8426a-e5ac-5944-bc14-f2db7559fd2f	0d880900-1578-512f-993d-012bf287ed9c	31a12b62-51e6-595b-bb87-5e214f2f8f97	1
d3a01d27-5f8a-5c7b-9125-073e76eb67a4	31a12b62-51e6-595b-bb87-5e214f2f8f97	4e8ed9cf-1693-5ca9-9c3e-6c1abbfc8143	1
3838d992-8e37-51f2-8daa-5897392c54a8	31a12b62-51e6-595b-bb87-5e214f2f8f97	3bef0da4-1b69-573b-b077-07a8d46a1584	2
be94686c-fc70-5479-a28b-3c5209e9cff7	31a12b62-51e6-595b-bb87-5e214f2f8f97	4227dbf8-f310-59cc-9f5f-75bdf08459c8	3
e8580ea2-2802-5ac6-ace9-f14cfb1b4d42	31a12b62-51e6-595b-bb87-5e214f2f8f97	49dfc288-d480-5262-a05e-9edad085b25a	4
0c873821-a364-52f2-be42-f66535f910ed	4e8ed9cf-1693-5ca9-9c3e-6c1abbfc8143	877ac137-c482-5091-9494-bd882b0cf7cd	1
34d494d9-586f-5727-8e6b-eefde78de6d0	877ac137-c482-5091-9494-bd882b0cf7cd	93fcb99c-db2a-53b3-82f7-a1d4ecb58f0e	1
9f1a2b3c-4d5e-6f7a-8b9c-0d1e2f3a4b5c	877ac137-c482-5091-9494-bd882b0cf7cd	d8271d2d-79ff-50e5-be69-ee29cc68f432	2
dfee59ac-2d23-559e-80ba-b60dd8ba33a7	49dfc288-d480-5262-a05e-9edad085b25a	5880accb-c184-5bfe-a6c0-78845c4ba7be	1
c71a44d1-0412-568b-a36b-1bb7bd699b77	5880accb-c184-5bfe-a6c0-78845c4ba7be	93fcb99c-db2a-53b3-82f7-a1d4ecb58f0e	1
a2b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d	5880accb-c184-5bfe-a6c0-78845c4ba7be	d8271d2d-79ff-50e5-be69-ee29cc68f432	2
adf69fd5-7e4b-5b38-aa2d-57308eaa3de9	3bef0da4-1b69-573b-b077-07a8d46a1584	465565d5-433a-563c-8b06-78b98785b814	1
4fbfb060-bf0b-58c9-8d2c-17982208f3ba	465565d5-433a-563c-8b06-78b98785b814	339634e2-d9f3-5366-b8b0-60cba53abba6	1
a69f9f2c-096d-5fb9-972e-f2695b740a25	339634e2-d9f3-5366-b8b0-60cba53abba6	93fcb99c-db2a-53b3-82f7-a1d4ecb58f0e	1
383f2b44-bb73-5080-b05a-95cd2e96db8b	339634e2-d9f3-5366-b8b0-60cba53abba6	d8271d2d-79ff-50e5-be69-ee29cc68f432	2
a7637926-2376-53d3-9cad-9de5387ee27e	4227dbf8-f310-59cc-9f5f-75bdf08459c8	30cee5c4-7eba-556e-8b51-dea56475179e	1
6181d575-f571-53a0-a64a-a57cbde419dc	30cee5c4-7eba-556e-8b51-dea56475179e	debdecef-88df-5601-8cfc-b5eb91b8b08f	1
88179ad8-1767-5b18-97d4-f38fd9b34b8a	debdecef-88df-5601-8cfc-b5eb91b8b08f	93fcb99c-db2a-53b3-82f7-a1d4ecb58f0e	1
e14458f3-a3d0-5aa2-8d38-1f7a5d9735a4	debdecef-88df-5601-8cfc-b5eb91b8b08f	d8271d2d-79ff-50e5-be69-ee29cc68f432	2
b1f6e489-a934-5a25-a8de-4b4d8ce64eea	93fcb99c-db2a-53b3-82f7-a1d4ecb58f0e	3f8ae7a2-1a20-5a7a-8f80-0abb5eed489e	1
fe0dae5c-3849-5dc1-ae5b-0c6c8e84ac63	93fcb99c-db2a-53b3-82f7-a1d4ecb58f0e	ca0c7576-4117-510d-b28b-6eff717791f7	2
cf52cec7-bdb7-5907-b4bd-3cde3b124370	d8271d2d-79ff-50e5-be69-ee29cc68f432	1208d7cb-f28c-5131-afad-9249828c164c	1
712a167a-71d8-49ee-b18e-1cabfb1d9c13	9bc0e11b-2f69-5420-a680-6165ec1e61fd	a1b2c3d4-e5f6-5a7b-8c9d-0e1f2a3b4c5d	1
c6d98ae7-1ad1-46e0-addb-f5d3445262ac	9bc0e11b-2f69-5420-a680-6165ec1e61fd	b2c3d4e5-f6a7-5b8c-9d0e-1f2a3b4c5d6e	2
58ae285c-a1de-42c1-9f96-d71f8e00b424	3f8ae7a2-1a20-5a7a-8f80-0abb5eed489e	a1b2c3d4-e5f6-5a7b-8c9d-0e1f2a3b4c5d	1
fb4d0f5d-fa87-4a9d-850d-50b5674c7046	3f8ae7a2-1a20-5a7a-8f80-0abb5eed489e	b2c3d4e5-f6a7-5b8c-9d0e-1f2a3b4c5d6e	2
47890d90-00f5-4639-b3d2-339470b7fa26	1208d7cb-f28c-5131-afad-9249828c164c	a1b2c3d4-e5f6-5a7b-8c9d-0e1f2a3b4c5d	1
89193e6d-857f-40fd-b3c2-9a4783e4efa2	1208d7cb-f28c-5131-afad-9249828c164c	b2c3d4e5-f6a7-5b8c-9d0e-1f2a3b4c5d6e	2
cc1a2b3c-4d5e-6f7a-8b9c-0d1e2f3a4b5c	ca0c7576-4117-510d-b28b-6eff717791f7	a1b2c3d4-e5f6-5a7b-8c9d-0e1f2a3b4c5d	1
dd2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d	ca0c7576-4117-510d-b28b-6eff717791f7	b2c3d4e5-f6a7-5b8c-9d0e-1f2a3b4c5d6e	2
\.

COPY public.node_source_references ("id", "node_id", "source_title", "section_path", "locator", "locator_detail", "printed_page_numbers", "pdf_page_numbers", "reference_note", "reference_order") FROM stdin;
fbc35f92-b99c-533f-90c5-d39db270946c	0878afaa-2a79-5188-94f6-c27d064f9402	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
e6878866-fd77-5967-bf57-7986acbf53e8	9bc0e11b-2f69-5420-a680-6165ec1e61fd	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
b18ac834-249a-5861-807f-b6b39768e9ab	0d880900-1578-512f-993d-012bf287ed9c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
f5306c91-17fd-58d6-876a-bb3792d1230a	31a12b62-51e6-595b-bb87-5e214f2f8f97	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
6af72ade-a0d0-5c68-903a-4645d43d246a	4e8ed9cf-1693-5ca9-9c3e-6c1abbfc8143	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
79033623-bf6c-5298-9fa8-f8861a4de5ba	3bef0da4-1b69-573b-b077-07a8d46a1584	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
ff922ddd-e0c1-5a80-addd-78c96e2aed80	4227dbf8-f310-59cc-9f5f-75bdf08459c8	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
5b5f9261-df08-5c62-a64a-72b1ce42f424	49dfc288-d480-5262-a05e-9edad085b25a	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
239eac03-1367-5ec7-97e1-3c087c91a94b	877ac137-c482-5091-9494-bd882b0cf7cd	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
525d3af8-ad8d-50b6-bbff-2f5fc8202858	465565d5-433a-563c-8b06-78b98785b814	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
0fab1d4c-0b67-59e0-91a6-a4dec32fd463	339634e2-d9f3-5366-b8b0-60cba53abba6	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
ceb115eb-da2f-570b-a6bd-34c27d627b2f	30cee5c4-7eba-556e-8b51-dea56475179e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
67f9d70a-2dc8-5e8e-a1c1-300eb1bdc412	debdecef-88df-5601-8cfc-b5eb91b8b08f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
3c6445b6-2d18-5dd8-baa9-416545a5a798	5880accb-c184-5bfe-a6c0-78845c4ba7be	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
03ddff06-0e41-5a53-b2d8-b30ef5132d84	3f8ae7a2-1a20-5a7a-8f80-0abb5eed489e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
f331fd7c-edbc-5a60-87b0-3f75d56aa3b8	93fcb99c-db2a-53b3-82f7-a1d4ecb58f0e	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
d8909b97-057e-5ab4-863e-5d37c8caecfb	d8271d2d-79ff-50e5-be69-ee29cc68f432	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
0df45abf-3279-5bf5-9057-fe4ade2cfb42	ca0c7576-4117-510d-b28b-6eff717791f7	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
782d3dfd-a68d-527e-b589-acf23529c583	1208d7cb-f28c-5131-afad-9249828c164c	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.7. T\u0103ng huy\u1ebft \u00e1p v\u00e0 m\u1ed9t s\u1ed1 b\u1ec7nh \u0111\u1ed3ng m\u1eafc", "3.7.3. T\u0103ng huy\u1ebft \u00e1p v\u00e0 Suy tim"]	Bảng 20. Khuyến cáo điều trị tăng huyết áp và Suy tim	\N	{33,34}	{35,36}	\N	1
\.



-- ================================================================
-- Tree 11: hypertension-chronic-kidney-disease (source: tree11.sql)
-- ================================================================
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

-- ================================================================
-- Tree 12: hypertension-in-pregnancy (source: tree12.sql)
-- ================================================================
--
-- CDSS decision-tree insert script
-- Tree: "THA trong thai kỳ - Minh"
-- Source: Bảng 15, Bảng 16 (Khuyến cáo THA VNHA 2022.pdf, Mục 3.6.6, pp.31-32)
--
-- IDs are generated by gen_random_uuid() (core since PG13). Timestamps are
-- generated by now() at insert time — nothing is hardcoded. Each statement
-- re-resolves the parent id it needs (tree_id by tree_key, node ids by
-- node_key) via a join back to the row inserted by the previous statement.
--
-- See backups/shared_conventions.txt for the full naming/shape audit this
-- file was brought into line with (extracted from the 5 real seeded trees).
--
-- LATEST PASS: removed the structured drug-name fields (preferred_drug,
-- drug_options, add_on_drug, contraindicated_drugs, drugs_to_avoid,
-- preferred_drugs) from context_patch/action_payload/global_config — a
-- separate drug table is planned, so specific drug names no longer live in
-- tree seed data. Drug-CLASS fields (e.g. "drug_class": "BETA_BLOCKER") are
-- kept, matching the A/B/C/D class system used elsewhere. Node text_en/
-- text_vi labels and node_keys are unchanged (they are this tree's actual
-- node identity, not a "list"). A few INFERENCE nodes now have a NULL
-- context_patch (T12_INF_SEVERE_DRUG_OPTIONS, T12_INF_MAGNESIUM_SUPPLEMENT,
-- T12_INF_LABETALOL_MGSO4, T12_INF_NICARDIPINE_MGSO4) since drug names were
-- their only patch content — this is intentional and not compensated for;
-- the planned drug table will supply this data going forward.
--
-- Fixes applied in an earlier pass:
--   * T12_START_PREGNANCY_HTN_SEQUENCE.text_en was showing "Hypertensive
--     Emergency" (a leftover from an unrelated edit) — restored to the
--     tree's actual entry description.
--   * Every ACTION/END node now carries action_type + follow_up_mode +
--     follow_up_required, matching the universal pattern in the 5 real
--     trees' 15 action_payloads (previously the END nodes had none at all).
--   * GLOBAL nodes restructured to the kind/purpose metadata shape used by
--     every real GLOBAL node (was a flat glossary object).
--   * node_source_references: locator/locator_detail were backwards
--     (locator held a short label, locator_detail held the full caption).
--     Fixed to match convention: locator = full printed figure/table
--     caption verbatim; locator_detail = terse English usage note.
--   * Drug names (Methyldopa, Labetalol, Nifedipine, Nicardipine, Esmolol,
--     Hydralazine, Urapidil, Magnesium Sulfate, Nitroglycerin) and disease
--     terms (chronic/gestational hypertension, preeclampsia, eclampsia,
--     HELLP) were verified directly against Bảng 15/16 (PDF pp.31-32) —
--     all confirmed accurate, no changes needed there.
--
-- All previously-applied dialect fixes (path/op/value comparisons,
-- supported operators only, one logical form per condition object,
-- section_path as {"number","title"} objects, smallint[] casts, and the
-- T12_INF_IV_NITROGLYCERIN/T12_INF_MAGNESIUM_SUPPLEMENT ->
-- T12_C_IMMEDIATE_TARGET edges) are preserved. All clinical-content
-- ambiguities already flagged with '-- VERIFY:' are preserved unchanged;
-- none of the naming/shape work above resolves them.
--
-- IMPORTANT — please verify before running in production:
-- The source flowchart image (Miro export) has several spots that were
-- genuinely hard to read at the available resolution. These are flagged
-- inline with '-- VERIFY:' comments and also noted in text_en for the
-- affected nodes. In particular:
--   1. T12_C_PREECLAMPSIA_RISK_FACTOR: exact risk-factor list text
--   2. T12_C_SEVERE_SIGNS -> T12_INF_ECLAMPSIA_CLASSIFICATION /
--      T12_INF_HELLP_SYNDROME_CLASSIFICATION split: the source column
--      boundary between the eclampsia/HELLP criteria box(es) was
--      ambiguous; verify against the original board
--   3. T12_C_TARGET_NOT_MET: exact time threshold text
--   4. T12_C_BP_TARGET_ACHIEVED / T12_C_BP_TARGET_NOT_ACHIEVED: the DBP
--      figure looked identical (85 mmHg) in both boxes in the source
--      image, which is likely an image-quality artifact, not the real
--      clinical criteria — please confirm the actual numbers
--
-- Node type mapping used (confirmed by sampling the legend swatch colors
-- directly, not just by eye):
--   green   Start Node          -> START
--   yellow  Condition Check      -> CONDITION
--   blue    Trigger/Input Node   -> INFERENCE (context_patch)
--   lavender End Node            -> END
--   pink    Link Node            -> LINK (not used in this tree)
--   orange  Action/Output Node   -> ACTION
--   gray    Global Node         -> GLOBAL
--
-- Use: cmd /c "docker compose exec -T postgres psql -U cdss -d cdss < backups\tree12.sql"
--

-- ============================================================
-- 1. Tree
-- ============================================================
INSERT INTO public.decision_trees (
        "id",
        "tree_key",
        "name_en",
        "name_vi",
        "created_at",
        "updated_at"
    )
VALUES (
        gen_random_uuid(),
        'hypertension-in-pregnancy',
        'Hypertension in Pregnancy',
        'THA trong thai kỳ',
        now(),
        now()
    );
-- ============================================================
-- 2. Nodes
-- ============================================================
WITH tree_ctx AS (
    SELECT id AS tree_id
    FROM public.decision_trees
    WHERE tree_key = 'hypertension-in-pregnancy'
),
node_seed (
    node_key,
    node_type,
    text_en,
    text_vi,
    condition_definition,
    context_patch,
    action_payload,
    global_config,
    link_target_tree_key,
    link_target_node_key,
    display_order
) AS (
    VALUES (
            'T12_START_PREGNANCY_HTN_SEQUENCE',
            'START',
            'Tree 13: Pregnancy sequence / Tree 17: Tree 8 sequence',
            'Cây 13: Trình tự thai kỳ
Cây 17: Trình tự Cây 8',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            0
        ),
        (
            'T12_C_HOME_BP_HIGH',
            'CONDITION',
            'HATN: SBP>=135 mmHg and DBP>=85 mmHg',
            'HATN
HATT >= 135 mmHg
và
HATTr >= 85 mmHg',
            '{"all": [{"path": "input.home_sbp", "op": "gte", "value": 135}, {"path": "input.home_dbp", "op": "gte", "value": 85}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            1
        ),
        (
            'T12_C_CLINIC_BP_HIGH',
            'CONDITION',
            'HAPK: SBP>=140 mmHg and DBP>=90 mmHg',
            'HAPK
HATT >= 140 mmHg
và
HATTr >= 90 mmHg',
            '{"all": [{"path": "input.current_clinic_sbp", "op": "gte", "value": 140}, {"path": "input.current_clinic_dbp", "op": "gte", "value": 90}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            2
        ),
        (
            'T12_C_CLINIC_BP_NORMAL',
            'CONDITION',
            'HAPK: SBP<140 mmHg and DBP<90 mmHg',
            'HAPK
HATT < 140 mmHg
và
HATTr < 90 mmHg',
            '{"all": [{"path": "input.current_clinic_sbp", "op": "lt", "value": 140}, {"path": "input.current_clinic_dbp", "op": "lt", "value": 90}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            3
        ),
        (
            'T12_END_FOLLOW_UP_MONITOR',
            'END',
            'Follow-up / monitor',
            'Theo dõi',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "CONTINUE_MONITORING", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            4
        ),
        (
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            'ACTION',
            'Determine type of hypertensive disorder of pregnancy',
            'Xác định kiểu THA trong thai kỳ',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "CLASSIFY_PREGNANCY_HYPERTENSION_TYPE", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            5
        ),
        (
            'T12_C_CHRONIC_HTN',
            'CONDITION',
            'Chronic HTN before pregnancy/before week 20, persisting >6 weeks postpartum with proteinuria',
            'THA trước khi mang thai hoặc trước tuần 20, tồn tại > 6 tuần sau sinh với protein niệu.',
            '{"all": [{"any": [{"path": "input.has_pre_pregnancy_hypertension", "op": "eq", "value": true}, {"path": "input.has_hypertension_before_week_20", "op": "eq", "value": true}]}, {"all": [{"path": "input.weeks_persisting_postpartum", "op": "gt", "value": 6}, {"path": "input.has_proteinuria", "op": "eq", "value": true}]}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            6
        ),
        (
            'T12_END_PRE_EXISTING_HTN',
            'END',
            'Pre-existing (chronic) hypertension',
            'THA từ trước',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "PRE_EXISTING_HYPERTENSION_DIAGNOSIS", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            7
        ),
        (
            'T12_C_GESTATIONAL_HTN',
            'CONDITION',
            'Gestational HTN after week 20, resolving <6 weeks postpartum',
            'THA sau tuần 20, kéo dài < 6 tuần sau sinh',
            '{"all": [{"path": "input.has_hypertension_after_week_20", "op": "eq", "value": true}, {"path": "input.weeks_resolved_postpartum", "op": "lt", "value": 6}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            8
        ),
        (
            'T12_INF_GESTATIONAL_HTN_CLASSIFICATION',
            'INFERENCE',
            'Gestational hypertension',
            'Thai kỳ',
            NULL::jsonb,
            '{"diagnosis": {"pregnancy_hypertension_type": "GESTATIONAL_HYPERTENSION"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            9
        ),
        (
            'T12_C_PREECLAMPSIA_PROTEINURIA',
            'CONDITION',
            'or gestational HTN with proteinuria >300mg/24h or ACR>=30mg/mmol',
            'hoặc THA thai kỳ có Protein niệu >300mg/24h
hoặc ACR >= 30 mg/mmol',
            '{"any": [{"path": "input.proteinuria_24h_mg", "op": "gt", "value": 300}, {"path": "input.acr_mg_mmol", "op": "gte", "value": 30}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            10
        ),
        -- VERIFY: T12_C_PREECLAMPSIA_RISK_FACTOR exact risk-factor list text (source image partly illegible)
        (
            'T12_C_PREECLAMPSIA_RISK_FACTOR',
            'CONDITION',
            'or has >=1 risk factor (prior gestational HTN, diabetes, chronic kidney disease, autoimmune disease, etc.) [text partly illegible in source image]',
            'hoặc có 1 trong các Yếu Tố Nguy Cơ:
THA trong lần thai trước đó / đái tháo đường / bệnh thận mạn / thai lần đầu hoặc nhiều lần / bệnh tự miễn',
            '{"any": [{"path": "input.has_prior_gestational_hypertension", "op": "eq", "value": true}, {"path": "input.has_diabetes", "op": "eq", "value": true}, {"path": "input.has_ckd", "op": "eq", "value": true}, {"path": "input.has_autoimmune_disease", "op": "eq", "value": true}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            11
        ),
        (
            'T12_INF_PREECLAMPSIA_CLASSIFICATION',
            'INFERENCE',
            'Preeclampsia',
            'Tiền sản giật',
            NULL::jsonb,
            '{"diagnosis": {"pregnancy_hypertension_type": "PREECLAMPSIA"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            12
        ),
        -- VERIFY: T12_C_SEVERE_SIGNS / T12_INF_ECLAMPSIA_CLASSIFICATION / T12_INF_HELLP_SYNDROME_CLASSIFICATION column boundary uncertain in source image
        (
            'T12_C_SEVERE_SIGNS',
            'CONDITION',
            'Severe features: seizure, severe headache, visual disturbance, epigastric pain, hemolysis, elevated liver enzymes, low platelets [column boundary in source image uncertain — see note]',
            'Tán huyết, tăng men gan, giảm tiểu cầu (Hemolysis, elevated liver enzymes, low platelets); có thể kèm co giật, đau đầu dữ dội, rối loạn thị giác, đau thượng vị',
            '{"any": [{"path": "input.has_seizure", "op": "eq", "value": true}, {"path": "input.has_severe_headache", "op": "eq", "value": true}, {"path": "input.has_visual_disturbance", "op": "eq", "value": true}, {"path": "input.has_epigastric_pain", "op": "eq", "value": true}, {"path": "input.has_hemolysis", "op": "eq", "value": true}, {"path": "input.has_elevated_liver_enzymes", "op": "eq", "value": true}, {"path": "input.has_low_platelets", "op": "eq", "value": true}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            13
        ),
        (
            'T12_INF_ECLAMPSIA_CLASSIFICATION',
            'INFERENCE',
            'Eclampsia',
            'Sản giật',
            NULL::jsonb,
            '{"diagnosis": {"pregnancy_hypertension_type": "ECLAMPSIA"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            14
        ),
        (
            'T12_INF_HELLP_SYNDROME_CLASSIFICATION',
            'INFERENCE',
            'HELLP syndrome',
            'Hội chứng HELLP',
            NULL::jsonb,
            '{"diagnosis": {"pregnancy_hypertension_type": "HELLP_SYNDROME"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            15
        ),
        (
            'T12_C_BP_MILD_MODERATE',
            'CONDITION',
            'SBP 140-159 mmHg OR DBP 90-109 mmHg',
            'HATT 140-159 mmHg
HOẶC
HATTr 90-109 mmHg',
            '{"any": [{"all": [{"path": "input.current_clinic_sbp", "op": "gte", "value": 140}, {"path": "input.current_clinic_sbp", "op": "lte", "value": 159}]}, {"all": [{"path": "input.current_clinic_dbp", "op": "gte", "value": 90}, {"path": "input.current_clinic_dbp", "op": "lte", "value": 109}]}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            16
        ),
        (
            'T12_C_BP_SEVERE',
            'CONDITION',
            'SBP>=160 mmHg OR DBP>=110 mmHg',
            'HATT >= 160 mmHg
HOẶC
HATTr >= 110 mmHg',
            '{"any": [{"path": "input.current_clinic_sbp", "op": "gte", "value": 160}, {"path": "input.current_clinic_dbp", "op": "gte", "value": 110}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            17
        ),
        (
            'T12_INF_MILD_MODERATE_SEVERITY',
            'INFERENCE',
            'Mild-moderate',
            'Tính nhẹ - trung bình',
            NULL::jsonb,
            '{"treatment": {"severity": "MILD_MODERATE"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            18
        ),
        (
            'T12_INF_SEVERE_SEVERITY',
            'INFERENCE',
            'Severe hypertension',
            'THA nặng',
            NULL::jsonb,
            '{"treatment": {"severity": "SEVERE"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            19
        ),
        (
            'T12_INF_METHYLDOPA',
            'INFERENCE',
            '(Central alpha-2 agonist) Methyldopa',
            '(Chủ vận chọn lọc alpha-2 giao cảm)
Methyldopa',
            NULL::jsonb,
            '{"treatment_preferences": {"drug_class": "CENTRAL_ALPHA2_AGONIST"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            20
        ),
        (
            'T12_INF_LABETALOL_ORAL',
            'INFERENCE',
            '(Beta blocker) Labetalol',
            '(Chẹn Beta)
Labetalol',
            NULL::jsonb,
            '{"treatment_preferences": {"drug_class": "BETA_BLOCKER"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            21
        ),
        (
            'T12_INF_NIFEDIPINE_OR_NICARDIPINE',
            'INFERENCE',
            '(Dihydropyridine CCB) Nifedipine (avoid capsule form) or Nicardipine',
            '(CKCa - Dihydropyridine)
Nifedipine [trừ viên dạng nang]
hoặc
Nicardipine',
            NULL::jsonb,
            '{"treatment_preferences": {"drug_class": "DIHYDROPYRIDINE_CCB"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            22
        ),
        (
            'T12_INF_ABSOLUTE_CONTRAINDICATIONS',
            'INFERENCE',
            'Absolute contraindication: A (ACEI, ARB), ARNI',
            'Chống chỉ định tuyệt đối:
A (ƯCMC, CTTA)
ARNI',
            NULL::jsonb,
            '{"treatment": {"absolute_contraindications": ["ƯCMC (ức chế men chuyển)", "CTTA (chẹn thụ thể angiotensin II)", "ARNI"]}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            23
        ),
        (
            'T12_INF_SEVERE_DRUG_OPTIONS',
            'INFERENCE',
            'Methyldopa oral, or Nifedipine/Nicardipine, or IV Labetalol/Nicardipine, or Esmolol, Hydralazine, Urapidil',
            'Methyldopa uống
hoặc (CKCa-Dihydropyridine) Nifedipine [trừ viên dạng nang] hoặc Nicardipine
hoặc Labetalol tĩnh mạch
hoặc Nicardipine tĩnh mạch
hoặc Esmolol (Chẹn Beta)
hoặc Hydralazine (Giãn mạch)
hoặc Urapidil',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            24
        ),
        (
            'T12_C_HYPERTENSIVE_CRISIS',
            'CONDITION',
            'Hypertensive crisis',
            'Liên cơn THA',
            '{"path": "input.has_hypertensive_crisis", "op": "eq", "value": true}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            25
        ),
        (
            'T12_C_PULMONARY_EDEMA',
            'CONDITION',
            'Pulmonary edema',
            'Phù phổi',
            '{"path": "input.has_pulmonary_edema", "op": "eq", "value": true}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            26
        ),
        (
            'T12_INF_IV_NITROGLYCERIN',
            'INFERENCE',
            'IV nitroglycerin infusion',
            'Truyền Nitroglycerin tĩnh mạch',
            NULL::jsonb,
            '{"treatment_preferences": {"route": "IV_INFUSION"}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            27
        ),
        (
            'T12_INF_MAGNESIUM_SUPPLEMENT',
            'INFERENCE',
            'Add magnesium',
            'Bổ sung magie',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            28
        ),
        (
            'T12_INF_LABETALOL_MGSO4',
            'INFERENCE',
            'Labetalol + Magnesium Sulfate',
            'Labetalol (Chẹn Beta) +
Magnesium Sulfate',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            29
        ),
        (
            'T12_INF_NICARDIPINE_MGSO4',
            'INFERENCE',
            'Nicardipine + Magnesium Sulfate',
            'Nicardipine (CKCa) +
Magnesium Sulfate',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            30
        ),
        (
            'T12_C_IMMEDIATE_TARGET',
            'CONDITION',
            'Immediate treatment target: SBP<160 mmHg and DBP<105 mmHg',
            'Đích điều trị
Ngay lập tức hạ HA
HATT < 160 mmHg
và
HATTr < 105 mmHg',
            '{"all": [{"path": "input.current_clinic_sbp", "op": "lt", "value": 160}, {"path": "input.current_clinic_dbp", "op": "lt", "value": 105}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            31
        ),
        -- VERIFY: T12_C_TARGET_NOT_MET exact time threshold text illegible in source image
        (
            'T12_C_TARGET_NOT_MET',
            'CONDITION',
            'If target not reached, or visual disturbance / coagulopathy present [exact timing text illegible in source image]',
            'Nếu không đạt được đích điều trị,
hoặc có rối loạn thị giác, rối loạn đông cầm máu',
            '{"any": [{"path": "input.is_treatment_target_not_achieved", "op": "eq", "value": true}, {"path": "input.has_visual_disturbance", "op": "eq", "value": true}, {"path": "input.has_coagulopathy", "op": "eq", "value": true}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            32
        ),
        (
            'T12_END_EMERGENCY_DELIVERY',
            'END',
            'Emergency delivery, terminate pregnancy',
            'Lấy thai cấp cứu, chấm dứt thai kỳ',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "EMERGENCY_DELIVERY", "follow_up_mode": "IMMEDIATE", "follow_up_required": false}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            33
        ),
        (
            'T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM',
            'ACTION',
            'Monitor pregnancy status and postpartum',
            'Theo dõi tình trạng thai kỳ và hậu sản',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "MONITOR_PREGNANCY_AND_POSTPARTUM", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            34
        ),
        (
            'T12_C_CURRENTLY_PREGNANT',
            'CONDITION',
            'Currently pregnant',
            'Đang mang thai',
            '{"path": "input.is_pregnant", "op": "eq", "value": true}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            35
        ),
        (
            'T12_C_POSTPARTUM',
            'CONDITION',
            'Postpartum',
            'Sau sinh',
            '{"path": "input.is_postpartum", "op": "eq", "value": true}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            36
        ),
        (
            'T12_C_HIGH_PREECLAMPSIA_RISK',
            'CONDITION',
            'High risk of preeclampsia',
            'Nguy cơ tiền sản giật cao',
            '{"path": "input.has_high_preeclampsia_risk", "op": "eq", "value": true}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            37
        ),
        (
            'T12_END_ASPIRIN_PROPHYLAXIS',
            'END',
            'Aspirin 75-162mg from week 12-36',
            'Aspirin 75-162 mg từ tuần 12-36',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "ASPIRIN_PROPHYLAXIS", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            38
        ),
        -- VERIFY: T12_C_BP_TARGET_ACHIEVED exact DBP figure uncertain in source image (looked identical to the not-achieved box)
        (
            'T12_C_BP_TARGET_ACHIEVED',
            'CONDITION',
            'BP target achieved: SBP 110-140 mmHg and DBP ~85 mmHg [exact DBP figure uncertain in source image]',
            'HA Đạt Đích Điều Trị
HATT 110 - 140 mmHg
và
HATTr 85 mmHg',
            '{"all": [{"path": "input.current_clinic_sbp", "op": "gte", "value": 110}, {"path": "input.current_clinic_sbp", "op": "lte", "value": 140}, {"path": "input.current_clinic_dbp", "op": "eq", "value": 85}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            39
        ),
        (
            'T12_END_MAINTAIN_REGIMEN_PREGNANT',
            'END',
            'Maintain regimen',
            'Duy trì phác đồ',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "MAINTAIN_CURRENT_REGIMEN", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            40
        ),
        -- VERIFY: T12_C_BP_TARGET_NOT_ACHIEVED criteria text partly illegible in source image, appeared identical to
        -- T12_C_BP_TARGET_ACHIEVED; defined here as that condition's exact negation pending confirmation against the
        -- original board (a CONDITION node cannot carry a placeholder, non-boolean note as its condition_definition)
        (
            'T12_C_BP_TARGET_NOT_ACHIEVED',
            'CONDITION',
            'BP target not achieved [criteria text partly illegible in source image, appears identical range to the achieved box]',
            'HA Không Đạt Đích Điều Trị
HATT 110 - 140 mmHg
và
HATTr 85 mmHg',
            '{"not": {"all": [{"path": "input.current_clinic_sbp", "op": "gte", "value": 110}, {"path": "input.current_clinic_sbp", "op": "lte", "value": 140}, {"path": "input.current_clinic_dbp", "op": "eq", "value": 85}]}}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            41
        ),
        (
            'T12_END_REFER_OBGYN',
            'END',
            'Refer to OB specialist',
            'Chuyển chuyên khoa Sản',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "REFER_TO_OBGYN_SPECIALIST", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            42
        ),
        (
            'T12_C_BREASTFEEDING',
            'CONDITION',
            'Currently breastfeeding',
            'Đang cho con bú',
            '{"path": "input.is_breastfeeding", "op": "eq", "value": true}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            43
        ),
        (
            'T12_C_BP_STILL_HIGH',
            'CONDITION',
            'BP still high: SBP>=140mmHg or DBP>=90mmHg',
            'HA còn cao
HATT >= 140 mmHg
hoặc
HATTr >= 90 mmHg',
            '{"any": [{"path": "input.current_clinic_sbp", "op": "gte", "value": 140}, {"path": "input.current_clinic_dbp", "op": "gte", "value": 90}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            44
        ),
        (
            'T12_C_BP_NOT_HIGH',
            'CONDITION',
            'BP no longer high: SBP<140mmHg and DBP<90mmHg',
            'HA không còn cao
HATT < 140 mmHg
và
HATTr < 90 mmHg',
            '{"all": [{"path": "input.current_clinic_sbp", "op": "lt", "value": 140}, {"path": "input.current_clinic_dbp", "op": "lt", "value": 90}]}'::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            45
        ),
        (
            'T12_ACTION_POSTPARTUM_CONTRAINDICATIONS',
            'ACTION',
            'Mandatory contraindications while breastfeeding / BP still high',
            'Chống chỉ định bắt buộc: Nicardipine
Tránh Atenolol, Propranolol, Nifedipine
Ưu tiên dùng Methyldopa / CKCa kéo dài',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "POSTPARTUM_DRUG_CONTRAINDICATIONS", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            46
        ),
        (
            'T12_END_MAINTAIN_REGIMEN_POSTPARTUM',
            'END',
            'Maintain regimen',
            'Duy trì phác đồ',
            NULL::jsonb,
            NULL::jsonb,
            '{"action_type": "MAINTAIN_CURRENT_REGIMEN", "follow_up_mode": "NEW_ENCOUNTER", "follow_up_required": true}'::jsonb,
            NULL::jsonb,
            NULL::text,
            NULL::text,
            47
        ),
        (
            'T12_GLOBAL_ABBREVIATION_GLOSSARY',
            'GLOBAL',
            'Abbreviation glossary',
            'Chú giải viết tắt',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            '{"kind": "ABBREVIATION_GLOSSARY", "purpose": "Chú giải các chữ viết tắt nhóm thuốc dùng trong Cây 12.", "entries": {"1_A_uc_che_he_RAS": {"label": "A: ức chế hệ RAS", "UCMC": "ức chế men chuyển", "CTTA": "chẹn thụ thể angiotensin II", "ARNI": "chẹn thụ thể Angiotensine-neprisyline"}, "4_B_chen_Beta": {"label": "B: chẹn Beta", "CB": "chẹn Beta"}, "3_C_chen_kenh_Canxi": {"label": "C: chẹn kênh Canxi", "CKCa": "chẹn kênh Canxi"}, "2_D_loi_tieu": {"label": "D: lợi tiểu", "LT": "lợi tiểu"}, "6_MRA": {"label": "MRA: thuốc đối kháng thụ thể mineralocorticoid"}, "5_SGLT2i": {"label": "SGLT2i: thuốc ức chế đồng vận chuyển Natri-glucose 2"}}}'::jsonb,
            NULL::text,
            NULL::text,
            98
        ),
        (
            'T12_GLOBAL_PREGNANCY_DRUG_CONTRAINDICATIONS',
            'GLOBAL',
            'Drug contraindications in pregnancy',
            'Chống chỉ định thuốc trong thai kỳ',
            NULL::jsonb,
            NULL::jsonb,
            NULL::jsonb,
            '{"kind": "OVERRIDE_NOTE", "purpose": "Chống chỉ định thuốc bắt buộc trong thai kỳ, áp dụng cho mọi lựa chọn thuốc hạ áp trong Cây 12.", "details": {"chong_chi_dinh_uc_che_he_RAS": {"label": "Chống chỉ định các thuốc ức chế hệ RAS gồm", "items": ["Ức chế men chuyển (ƯCMC)", "Chẹn thụ thể Angiotensin II (CTTA)", "Ức chế renin trực tiếp", "thuốc kháng thụ thể Mineralocorticoid (MRA)"]}}}'::jsonb,
            NULL::text,
            NULL::text,
            99
        )
)
INSERT INTO public.decision_nodes (
        "id",
        "tree_id",
        "node_key",
        "node_type",
        "text_en",
        "text_vi",
        "condition_definition",
        "context_patch",
        "action_payload",
        "global_config",
        "link_target_tree_key",
        "link_target_node_key",
        "display_order",
        "created_at",
        "updated_at"
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
    SELECT id AS tree_id
    FROM public.decision_trees
    WHERE tree_key = 'hypertension-in-pregnancy'
),
edge_seed (
    from_node_key,
    to_node_key,
    traversal_order
) AS (
    VALUES (
            'T12_START_PREGNANCY_HTN_SEQUENCE',
            'T12_C_HOME_BP_HIGH',
            1
        ),
        (
            'T12_START_PREGNANCY_HTN_SEQUENCE',
            'T12_C_CLINIC_BP_HIGH',
            2
        ),
        (
            'T12_START_PREGNANCY_HTN_SEQUENCE',
            'T12_C_CLINIC_BP_NORMAL',
            3
        ),
        (
            'T12_C_CLINIC_BP_NORMAL',
            'T12_END_FOLLOW_UP_MONITOR',
            1
        ),
        (
            'T12_C_HOME_BP_HIGH',
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            1
        ),
        (
            'T12_C_CLINIC_BP_HIGH',
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            1
        ),
        (
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            'T12_C_CHRONIC_HTN',
            1
        ),
        (
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            'T12_C_GESTATIONAL_HTN',
            2
        ),
        (
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            'T12_C_PREECLAMPSIA_PROTEINURIA',
            3
        ),
        (
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            'T12_C_PREECLAMPSIA_RISK_FACTOR',
            4
        ),
        (
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            'T12_C_SEVERE_SIGNS',
            5
        ),
        (
            'T12_C_CHRONIC_HTN',
            'T12_END_PRE_EXISTING_HTN',
            1
        ),
        (
            'T12_C_GESTATIONAL_HTN',
            'T12_INF_GESTATIONAL_HTN_CLASSIFICATION',
            1
        ),
        (
            'T12_C_PREECLAMPSIA_PROTEINURIA',
            'T12_INF_PREECLAMPSIA_CLASSIFICATION',
            1
        ),
        (
            'T12_C_PREECLAMPSIA_RISK_FACTOR',
            'T12_INF_PREECLAMPSIA_CLASSIFICATION',
            1
        ),
        (
            'T12_C_SEVERE_SIGNS',
            'T12_INF_ECLAMPSIA_CLASSIFICATION',
            1
        ),
        (
            'T12_C_SEVERE_SIGNS',
            'T12_INF_HELLP_SYNDROME_CLASSIFICATION',
            2
        ),
        (
            'T12_INF_GESTATIONAL_HTN_CLASSIFICATION',
            'T12_C_BP_MILD_MODERATE',
            1
        ),
        (
            'T12_INF_GESTATIONAL_HTN_CLASSIFICATION',
            'T12_C_BP_SEVERE',
            2
        ),
        (
            'T12_INF_PREECLAMPSIA_CLASSIFICATION',
            'T12_C_BP_MILD_MODERATE',
            1
        ),
        (
            'T12_INF_PREECLAMPSIA_CLASSIFICATION',
            'T12_C_BP_SEVERE',
            2
        ),
        (
            'T12_C_BP_MILD_MODERATE',
            'T12_INF_MILD_MODERATE_SEVERITY',
            1
        ),
        ('T12_C_BP_SEVERE', 'T12_INF_SEVERE_SEVERITY', 1),
        (
            'T12_INF_MILD_MODERATE_SEVERITY',
            'T12_INF_METHYLDOPA',
            1
        ),
        (
            'T12_INF_MILD_MODERATE_SEVERITY',
            'T12_INF_LABETALOL_ORAL',
            2
        ),
        (
            'T12_INF_MILD_MODERATE_SEVERITY',
            'T12_INF_NIFEDIPINE_OR_NICARDIPINE',
            3
        ),
        (
            'T12_INF_METHYLDOPA',
            'T12_INF_ABSOLUTE_CONTRAINDICATIONS',
            1
        ),
        (
            'T12_INF_LABETALOL_ORAL',
            'T12_INF_ABSOLUTE_CONTRAINDICATIONS',
            1
        ),
        (
            'T12_INF_NIFEDIPINE_OR_NICARDIPINE',
            'T12_INF_ABSOLUTE_CONTRAINDICATIONS',
            1
        ),
        (
            'T12_INF_SEVERE_SEVERITY',
            'T12_INF_SEVERE_DRUG_OPTIONS',
            1
        ),
        (
            'T12_INF_SEVERE_DRUG_OPTIONS',
            'T12_C_HYPERTENSIVE_CRISIS',
            1
        ),
        (
            'T12_INF_SEVERE_DRUG_OPTIONS',
            'T12_C_PULMONARY_EDEMA',
            2
        ),
        (
            'T12_C_HYPERTENSIVE_CRISIS',
            'T12_INF_IV_NITROGLYCERIN',
            1
        ),
        (
            'T12_C_PULMONARY_EDEMA',
            'T12_INF_MAGNESIUM_SUPPLEMENT',
            1
        ),
        (
            'T12_INF_ECLAMPSIA_CLASSIFICATION',
            'T12_INF_LABETALOL_MGSO4',
            1
        ),
        (
            'T12_INF_ECLAMPSIA_CLASSIFICATION',
            'T12_INF_NICARDIPINE_MGSO4',
            2
        ),
        (
            'T12_INF_HELLP_SYNDROME_CLASSIFICATION',
            'T12_INF_LABETALOL_MGSO4',
            1
        ),
        (
            'T12_INF_HELLP_SYNDROME_CLASSIFICATION',
            'T12_INF_NICARDIPINE_MGSO4',
            2
        ),
        (
            'T12_INF_LABETALOL_MGSO4',
            'T12_C_IMMEDIATE_TARGET',
            1
        ),
        (
            'T12_INF_NICARDIPINE_MGSO4',
            'T12_C_IMMEDIATE_TARGET',
            1
        ),
        (
            'T12_INF_IV_NITROGLYCERIN',
            'T12_C_IMMEDIATE_TARGET',
            1
        ),
        (
            'T12_INF_MAGNESIUM_SUPPLEMENT',
            'T12_C_IMMEDIATE_TARGET',
            1
        ),
        (
            'T12_C_IMMEDIATE_TARGET',
            'T12_C_TARGET_NOT_MET',
            1
        ),
        (
            'T12_C_TARGET_NOT_MET',
            'T12_END_EMERGENCY_DELIVERY',
            1
        ),
        (
            'T12_INF_ABSOLUTE_CONTRAINDICATIONS',
            'T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM',
            1
        ),
        (
            'T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM',
            'T12_C_CURRENTLY_PREGNANT',
            1
        ),
        (
            'T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM',
            'T12_C_POSTPARTUM',
            2
        ),
        (
            'T12_C_CURRENTLY_PREGNANT',
            'T12_C_HIGH_PREECLAMPSIA_RISK',
            1
        ),
        (
            'T12_C_CURRENTLY_PREGNANT',
            'T12_C_BP_TARGET_ACHIEVED',
            2
        ),
        (
            'T12_C_CURRENTLY_PREGNANT',
            'T12_C_BP_TARGET_NOT_ACHIEVED',
            3
        ),
        (
            'T12_C_HIGH_PREECLAMPSIA_RISK',
            'T12_END_ASPIRIN_PROPHYLAXIS',
            1
        ),
        (
            'T12_C_BP_TARGET_ACHIEVED',
            'T12_END_MAINTAIN_REGIMEN_PREGNANT',
            1
        ),
        (
            'T12_C_BP_TARGET_NOT_ACHIEVED',
            'T12_END_REFER_OBGYN',
            1
        ),
        ('T12_C_POSTPARTUM', 'T12_C_BREASTFEEDING', 1),
        ('T12_C_POSTPARTUM', 'T12_C_BP_STILL_HIGH', 2),
        ('T12_C_POSTPARTUM', 'T12_C_BP_NOT_HIGH', 3),
        (
            'T12_C_BREASTFEEDING',
            'T12_ACTION_POSTPARTUM_CONTRAINDICATIONS',
            1
        ),
        (
            'T12_C_BP_STILL_HIGH',
            'T12_ACTION_POSTPARTUM_CONTRAINDICATIONS',
            1
        ),
        (
            'T12_C_BP_NOT_HIGH',
            'T12_END_MAINTAIN_REGIMEN_POSTPARTUM',
            1
        ),
        (
            'T12_ACTION_POSTPARTUM_CONTRAINDICATIONS',
            'T12_END_MAINTAIN_REGIMEN_POSTPARTUM',
            1
        )
)
INSERT INTO public.decision_edges (
        "id",
        "from_node_id",
        "to_node_id",
        "traversal_order"
    )
SELECT gen_random_uuid(),
    from_node.id,
    to_node.id,
    edge_seed.traversal_order
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
    SELECT id AS tree_id
    FROM public.decision_trees
    WHERE tree_key = 'hypertension-in-pregnancy'
),
reference_seed (
    node_key,
    source_title,
    section_path,
    locator,
    locator_detail,
    printed_page_numbers,
    pdf_page_numbers,
    reference_note,
    reference_order
) AS (
    VALUES (
            'T12_START_PREGNANCY_HTN_SEQUENCE',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Mục 3.6.6. Tăng huyết áp trong thai kỳ',
            'Entry point of the pregnancy-hypertension sequence.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Điểm vào của trình tự THA trong thai kỳ, theo Mục 3.6.6.',
            1
        ),
        (
            'T12_ACTION_CLASSIFY_HTN_TYPE',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Classifies into the 5 categories of Bảng 15: pre-existing, gestational, preeclampsia, eclampsia, HELLP syndrome.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Phân loại theo 5 nhóm của Bảng 15: THA từ trước, THA thai kỳ, Tiền sản giật, Sản giật, Hội chứng HELLP.',
            1
        ),
        (
            'T12_END_FOLLOW_UP_MONITOR',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'BP below the 140/90 mmHg (clinic) / 135/85 mmHg (home) treatment threshold does not require drug therapy; continue monitoring.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'HA dưới ngưỡng 140/90 mmHg (phòng khám) / 135/85 mmHg (tại nhà) không cần điều trị thuốc; tiếp tục theo dõi.',
            1
        ),
        (
            'T12_C_CHRONIC_HTN',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Pre-existing hypertension: present before pregnancy or before week 20, persisting >6 weeks postpartum with proteinuria.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'THA có trước khi mang thai hoặc trước tuần lễ thứ 20 của thai kỳ và tồn tại > 6 tuần sau sinh với protein niệu.',
            1
        ),
        (
            'T12_END_PRE_EXISTING_HTN',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Terminal classification: pre-existing (chronic) hypertension.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Phân loại kết thúc "THA từ trước" của Bảng 15.',
            1
        ),
        (
            'T12_C_GESTATIONAL_HTN',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Gestational hypertension: onset after week 20, resolving within 6 weeks postpartum.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'THA khởi phát sau tuần thứ 20 của thai kỳ, và kéo dài < 6 tuần sau sinh.',
            1
        ),
        (
            'T12_INF_GESTATIONAL_HTN_CLASSIFICATION',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Classification label: gestational hypertension.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Nhãn phân loại "THA trong thai kỳ" (gestational hypertension) của Bảng 15.',
            1
        ),
        (
            'T12_C_PREECLAMPSIA_PROTEINURIA',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Preeclampsia: gestational hypertension with proteinuria >300mg/24h or ACR >=30 mg/mmol [265 mg/g].',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'THA thai kỳ và có protein niệu (>300 mg/24h hoặc tỷ albumin/creatinine niệu (ACR) >30 mg/mmol [265 mg/g]).',
            1
        ),
        (
            'T12_C_PREECLAMPSIA_RISK_FACTOR',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Preeclampsia risk factors: prior hypertension, prior gestational hypertension, diabetes, kidney disease, nulliparity/multiparity, autoimmune disease (SLE).',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Các yếu tố nguy cơ: THA từ trước, THA trong lần thai kỳ trước, đái tháo đường, bệnh thận, thai lần đầu hay nhiều lần, và bệnh tự miễn (SLE).',
            1
        ),
        (
            'T12_INF_PREECLAMPSIA_CLASSIFICATION',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Classification label: preeclampsia.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Nhãn phân loại "Tiền sản giật" (preeclampsia) của Bảng 15.',
            1
        ),
        (
            'T12_C_SEVERE_SIGNS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Eclampsia: seizure, severe headache, visual disturbance, epigastric pain. HELLP: hemolysis, elevated liver enzymes, low platelets.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Sản giật: co giật, đau đầu dữ dội, rối loạn thị giác, đau bụng, buồn nôn/nôn, thiểu niệu. HELLP: tán huyết, tăng men gan, giảm tiểu cầu.',
            1
        ),
        (
            'T12_INF_ECLAMPSIA_CLASSIFICATION',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Classification label: eclampsia.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Nhãn phân loại "Sản giật" (eclampsia) của Bảng 15.',
            1
        ),
        (
            'T12_INF_HELLP_SYNDROME_CLASSIFICATION',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Classification label: HELLP syndrome (Hemolysis, Elevated Liver enzymes, Low Platelets).',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Nhãn phân loại "Hội chứng HELLP" của Bảng 15.',
            1
        ),
        (
            'T12_C_BP_MILD_MODERATE',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Mục 3.6.6. Tăng huyết áp trong thai kỳ',
            'Mild-to-moderate severity: SBP >=140 (but <160) mmHg and/or DBP >=90 (but <110) mmHg, from the paragraph immediately preceding Bảng 15.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'THA nhẹ đến trung bình: đo HA ít nhất 2 lần cách nhau >=4 giờ, HATT >=140 (nhưng <160) mmHg và/hoặc HATTr >=90 (nhưng <110) mmHg.',
            1
        ),
        (
            'T12_C_BP_SEVERE',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Mục 3.6.6. Tăng huyết áp trong thai kỳ',
            'Severe hypertension: SBP >=160 mmHg and/or DBP >=110 mmHg; SBP >=170 mmHg is a medical emergency.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'THA nặng: HATT >=160 mmHg và/hoặc HATTr >=110 mmHg. HATT >=170 mmHg là cấp cứu nội khoa.',
            1
        ),
        (
            'T12_INF_MILD_MODERATE_SEVERITY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Mục 3.6.6. Tăng huyết áp trong thai kỳ',
            'Severity label: mild-to-moderate.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Phân độ "nhẹ đến trung bình".',
            1
        ),
        (
            'T12_INF_SEVERE_SEVERITY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Mục 3.6.6. Tăng huyết áp trong thai kỳ',
            'Severity label: severe.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Phân độ "nặng".',
            1
        ),
        (
            'T12_C_HOME_BP_HIGH',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Home BP >=135/85 mmHg should be treated.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'HA ổn định >=135/85 mmHg đo tại nhà nên được điều trị.',
            1
        ),
        (
            'T12_C_CLINIC_BP_HIGH',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Clinic BP >=140/90 mmHg should be treated.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'HA ổn định >=140/90 mmHg đo tại phòng khám nên được điều trị.',
            1
        ),
        (
            'T12_C_CLINIC_BP_NORMAL',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Complement of the clinic-BP treatment threshold: below threshold.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'HA dưới ngưỡng điều trị đo tại phòng khám.',
            1
        ),
        (
            'T12_INF_METHYLDOPA',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Mild hypertension, first-choice option: methyldopa.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'THA nhẹ, lựa chọn đầu tiên: methyldopa.',
            1
        ),
        (
            'T12_INF_LABETALOL_ORAL',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Mild hypertension, first-choice option: beta-blocker (labetalol).',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'THA nhẹ, lựa chọn đầu tiên: chẹn beta (Labetalol).',
            1
        ),
        (
            'T12_INF_NIFEDIPINE_OR_NICARDIPINE',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Mild hypertension, first-choice option: dihydropyridine CCB (nifedipine [not capsule form], nicardipine).',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'THA nhẹ, lựa chọn đầu tiên: chẹn kênh canxi dihydropyridine (Nifedipine [trừ dạng viên nang], Nicardipine).',
            1
        ),
        (
            'T12_INF_ABSOLUTE_CONTRAINDICATIONS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'RAS-inhibitor drugs (ACEI, ARB, direct renin inhibitors, MRA) are contraindicated in pregnancy.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'THA trong thai kỳ: chống chỉ định dùng các thuốc ức chế RAS (ƯCMC, CTTA, ức chế renin trực tiếp, lợi tiểu kháng thụ thể Mineralocorticoid).',
            1
        ),
        (
            'T12_INF_SEVERE_DRUG_OPTIONS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Severe hypertension: IV labetalol (or IV nicardipine, esmolol, hydralazine, urapidil), oral methyldopa, or dihydropyridine CCB.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'THA nặng: Labetalol TM (hoặc Nicardipine TM, Esmolol, Hydralazine, Urapidil), Methyldopa uống, hoặc CKCa dihydropyridine.',
            1
        ),
        (
            'T12_C_HYPERTENSIVE_CRISIS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'During a hypertensive crisis: add magnesium to prevent eclampsia.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Trong cơn THA: bổ sung magiê để ngăn ngừa sản giật.',
            1
        ),
        (
            'T12_C_PULMONARY_EDEMA',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'In pulmonary edema: IV nitroglycerin infusion; avoid sodium nitroprusside (fetal cyanide toxicity risk).',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Trong phù phổi: truyền TM Nitroglycerin; tránh Natri nitroprusside do nguy cơ nhiễm độc xyanua thai nhi.',
            1
        ),
        (
            'T12_INF_IV_NITROGLYCERIN',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Pulmonary edema management: IV nitroglycerin infusion.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Trong phù phổi: Truyền TM Nitroglycerin.',
            1
        ),
        (
            'T12_INF_MAGNESIUM_SUPPLEMENT',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Hypertensive crisis management: add magnesium sulfate to prevent eclampsia.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Bổ sung magiê trong cơn THA để ngăn ngừa sản giật.',
            1
        ),
        (
            'T12_INF_LABETALOL_MGSO4',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Eclampsia/severe preeclampsia/HELLP: treat immediately (SBP<160, DBP<105 mmHg), labetalol or nicardipine plus magnesium sulfate.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Sản giật/Tiền sản giật nặng/HELLP: ngay lập tức hạ HA, Labetalol hoặc Nicardipine và Magnesium sulfate.',
            1
        ),
        (
            'T12_INF_NICARDIPINE_MGSO4',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Eclampsia/severe preeclampsia/HELLP: treat immediately (SBP<160, DBP<105 mmHg), labetalol or nicardipine plus magnesium sulfate.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Sản giật/Tiền sản giật nặng/HELLP: ngay lập tức hạ HA, Labetalol hoặc Nicardipine và Magnesium sulfate.',
            1
        ),
        (
            'T12_C_IMMEDIATE_TARGET',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 15. Phân loại tăng huyết áp trong thai kỳ (52)',
            'Immediate treatment target: SBP<160 mmHg and DBP<105 mmHg.',
            ARRAY [29]::smallint [],
            ARRAY [31]::smallint [],
            'Đích điều trị ngay lập tức: HATT <160 mmHg và HATTr <105 mmHg.',
            1
        ),
        (
            'T12_C_TARGET_NOT_MET',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Emergency delivery indicated when visual disturbance or coagulopathy is present.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Lấy thai cấp cứu khi có rối loạn thị giác, rối loạn đông cầm máu.',
            1
        ),
        (
            'T12_END_EMERGENCY_DELIVERY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Delivery for gestational hypertension or preeclampsia is recommended at week 37 if asymptomatic; emergency delivery for visual disturbance/coagulopathy.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Chấm dứt thai kỳ trong THA thai kỳ hoặc Tiền sản giật: khuyến cáo ở tuần 37 nếu không triệu chứng; lấy thai cấp cứu khi có rối loạn thị giác/đông cầm máu.',
            1
        ),
        (
            'T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Ongoing management of hypertension in pregnancy: monitor pregnancy status and postpartum course.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Quản lý THA trong thai kỳ theo dõi tình trạng mang thai và hậu sản.',
            1
        ),
        (
            'T12_C_CURRENTLY_PREGNANT',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Branch: still pregnant.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Nhánh còn đang mang thai.',
            1
        ),
        (
            'T12_C_POSTPARTUM',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Branch: postpartum.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Nhánh sau sinh.',
            1
        ),
        (
            'T12_C_HIGH_PREECLAMPSIA_RISK',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Preeclampsia prophylaxis: 75-162 mg aspirin from week 12-36.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Phòng ngừa tiền sản giật: 75-162 mg Aspirin vào tuần 12-36.',
            1
        ),
        (
            'T12_END_ASPIRIN_PROPHYLAXIS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Preeclampsia prophylaxis: 75-162 mg aspirin from week 12-36; oral calcium 1.5-2 g/day recommended for low-calcium diets (<600 mg/day).',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Phòng ngừa tiền sản giật: 75-162 mg Aspirin vào tuần 12-36. Bổ sung canxi 1,5-2 g/ngày được khuyến khích ở phụ nữ có chế độ ăn ít canxi (<600 mg/ngày).',
            1
        ),
        (
            'T12_C_BP_TARGET_ACHIEVED',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Treatment target: clinic DBP 85 mmHg (and SBP 110-140 mmHg).',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Mục tiêu điều trị: HATTr 85 mmHg tại phòng khám (và HATT từ 110-140 mmHg).',
            1
        ),
        (
            'T12_END_MAINTAIN_REGIMEN_PREGNANT',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Target achieved: maintain current regimen.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Đạt mục tiêu điều trị: duy trì phác đồ hiện tại.',
            1
        ),
        (
            'T12_C_BP_TARGET_NOT_ACHIEVED',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Complement of the treatment-target-achieved condition.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Không đạt mục tiêu điều trị.',
            1
        ),
        (
            'T12_END_REFER_OBGYN',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Target not achieved: refer to OB specialist.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Không đạt mục tiêu điều trị: chuyển chuyên khoa Sản.',
            1
        ),
        (
            'T12_C_BREASTFEEDING',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Breastfeeding period: avoid atenolol, propranolol, nifedipine; prefer long-acting CCB.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Thời kỳ cho con bú: tránh Atenolol, Propranolol, Nifedipine; ưu tiên CKCa tác dụng kéo dài.',
            1
        ),
        (
            'T12_C_BP_STILL_HIGH',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Postpartum BP: if still high, any recommended drug may be used except methyldopa (postpartum depression risk).',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'HA sau sinh: nếu HA cao vẫn tiếp diễn, dùng bất kỳ thuốc nào được khuyến cáo trừ Methyldopa (gây trầm cảm sau sinh).',
            1
        ),
        (
            'T12_C_BP_NOT_HIGH',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Postpartum BP no longer high: maintain regimen.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'HA sau sinh không còn cao: duy trì phác đồ.',
            1
        ),
        (
            'T12_ACTION_POSTPARTUM_CONTRAINDICATIONS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Contraindicated: nicardipine. Avoid: atenolol, propranolol, nifedipine. Prefer: methyldopa/long-acting CCB.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Chống chỉ định Nicardipine; tránh Atenolol, Propranolol, Nifedipine; ưu tiên Methyldopa/CKCa tác dụng kéo dài.',
            1
        ),
        (
            'T12_END_MAINTAIN_REGIMEN_POSTPARTUM',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'Postpartum: maintain regimen.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Duy trì phác đồ sau sinh.',
            1
        ),
        (
            'T12_GLOBAL_ABBREVIATION_GLOSSARY',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52), chú thích',
            'Footnote abbreviation glossary for the drug classes named in Bảng 16.',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'Chú giải viết tắt cho các nhóm thuốc nêu trong Bảng 16 (ƯCMC, CTTA, CKCa, LT, MRA, SGLT2i).',
            1
        ),
        (
            'T12_GLOBAL_PREGNANCY_DRUG_CONTRAINDICATIONS',
            'Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về Chẩn đoán & Điều trị Tăng huyết áp 2022 (Tóm tắt)',
            '[{"number": "3.6.6", "title": "Tăng huyết áp trong thai kỳ"}]'::jsonb,
            'Bảng 16. Khuyến cáo điều trị tăng huyết áp trong thai kỳ (2, 52)',
            'RAS-inhibitor drugs are contraindicated in pregnancy; avoid sodium nitroprusside (fetal cyanide toxicity risk).',
            ARRAY [30]::smallint [],
            ARRAY [32]::smallint [],
            'THA trong thai kỳ: chống chỉ định thuốc ức chế RAS; tránh Natri nitroprusside do nguy cơ nhiễm độc xyanua thai nhi.',
            1
        )
)
INSERT INTO public.node_source_references (
        "id",
        "node_id",
        "source_title",
        "section_path",
        "locator",
        "locator_detail",
        "printed_page_numbers",
        "pdf_page_numbers",
        "reference_note",
        "reference_order"
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

-- ================================================================
-- Tree 13: resistant-hypertension (source: seed_resistant_hypertension.sql)
-- ================================================================
COPY public.decision_trees ("id", "tree_key", "name_en", "name_vi", "created_at", "updated_at") FROM stdin;
8dffe102-09fa-4e81-b2d1-6035da07ad0b	resistant-hypertension	Resistant Hypertension	THA Kháng trị	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
\.

COPY public.decision_nodes ("id", "tree_id", "node_key", "node_type", "text_en", "text_vi", "condition_definition", "context_patch", "action_payload", "global_config", "link_target_tree_key", "link_target_node_key", "display_order", "created_at", "updated_at") FROM stdin;
bb6dadda-b610-4172-8435-88e0111ee741	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_START	START	Essential Treatment Strategy Tree (Tree 4) or Optimal Treatment Strategy Tree (Tree 5)	Cây 4: cây chiến lược điều trị thiết yếu hoặc Cây 5: cây chiến lược điều trị tối ưu	\N	\N	\N	\N	\N	\N	1	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
455fcd4a-e8f2-4b03-b67a-71784b796683	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_C_LIMITED	CONDITION	Essential standard	Tiêu chuẩn thiết yếu	{"op": "eq", "path": "input.facility_capability", "value": "LIMITED_RESOURCES"}	\N	\N	\N	\N	\N	2	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
d98b6c15-9c2b-4b7b-a6cb-f869f625f98a	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_ESSENTIAL_TREATMENT	ACTION	Treat according to essential standard and enhance lifestyle changes	Điều trị theo tiêu chuẩn thiết yếu và Tăng cường biện pháp tđls, đặc biệt là hạn chế muối	\N	\N	{"action_type": "LIFESTYLE_CHANGES", "salt_restriction": true}	\N	\N	\N	3	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
583fb951-4f9f-48ef-b652-85c8d6fe7101	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_CHECK_MRA	ACTION	Check MRA tolerance	Kiểm tra khả năng dung nạp MRA	\N	\N	{"action_type": "CHECK_MRA"}	\N	\N	\N	4	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
379b8afc-b896-410f-bb13-c2e38bef13ad	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_C_MRA_TOLERATED	CONDITION	Tolerates MRA	Có khả năng dung nạp MRA	{"op": "eq", "path": "input.tolerates_mra", "value": true}	\N	\N	\N	\N	\N	5	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
ac540e55-906b-437f-a6af-2eccb619bbb5	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_ADD_MRA	ACTION	Combine A + C + D and MRA	Phối hợp 3 nhóm thuốc A + C + D và MRA	\N	\N	{"action_type": "COMBINE_ACD_MRA"}	\N	\N	\N	6	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
39319a8a-753e-4b85-8611-24d214b78327	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_C_MRA_NOT_TOLERATED	CONDITION	Does not tolerate MRA	Không có khả năng dung nạp MRA	{"op": "eq", "path": "input.tolerates_mra", "value": false}	\N	\N	\N	\N	\N	7	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
da1ba865-b2d4-4677-85ad-15496aad4653	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_ADD_D	ACTION	Add D	Thêm D	\N	\N	{"action_type": "ADD_D"}	\N	\N	\N	8	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
d79e31dd-3e3f-43f9-bc55-29657d900c2f	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_CHECK_SPIRONOLACTONE	ACTION	Check Spironolactone tolerance	Kiểm tra khả năng dung nạp Spironolactone (lợi tiểu giữ kali)	\N	\N	{"action_type": "CHECK_SPIRONOLACTONE"}	\N	\N	\N	9	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
de43bad7-f682-477d-85ab-a0627f596c6a	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_C_SPIRONOLACTONE_TOLERATED	CONDITION	Tolerates Spironolactone	Có khả năng dung nạp Spironolactone	{"op": "eq", "path": "input.tolerates_spironolactone", "value": true}	\N	\N	\N	\N	\N	10	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
8e783a9b-44d4-4246-9ab1-4bf9a9190d3b	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_ADD_SPIRONOLACTONE	ACTION	Add low-dose Spironolactone to current regimen	Thêm Spironolactone liều thấp kết hợp với liều thuốc điều trị hiện có	\N	\N	{"action_type": "ADD_SPIRONOLACTONE"}	\N	\N	\N	11	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
9479b0ab-7060-4663-8246-d2206d4bc5e5	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_C_SPIRONOLACTONE_NOT_TOLERATED	CONDITION	Does not tolerate Spironolactone	Không có khả năng dung nạp Spironolactone	{"op": "eq", "path": "input.tolerates_spironolactone", "value": false}	\N	\N	\N	\N	\N	12	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
29baba0e-818b-41db-a911-96f799a5b584	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_ALTERNATIVES	ACTION	Alternatives: Add K-sparing D, Increase D dose, or Add Bisoprolol/Doxazosin	Thêm nhóm D giữ kali, Tăng liều nhóm D, hoặc Thêm Bisoprolol/Doxazosin	\N	\N	{"action_type": "THERAPEUTIC_ALTERNATIVES"}	\N	\N	\N	13	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
8b2fa240-abcb-47e8-9e3c-9b0a15cb9958	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_C_BP_TARGET_REACHED	CONDITION	BP reaches target	HA đạt đích điều trị	{"op": "eq", "path": "input.bp_target_reached", "value": true}	\N	\N	\N	\N	\N	14	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
3b5b88f1-65e0-4a2d-934b-fb5a965b6df6	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_END_MAINTAIN	END	Maintain regimen	Duy trì phác đồ	\N	\N	{"action_type": "MAINTAIN_REGIMEN"}	\N	\N	\N	15	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
879486a4-d0bf-42f2-a772-dcb944ddbb93	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_C_BP_TARGET_NOT_REACHED	CONDITION	BP does not reach target	HA không đạt đích điều trị	{"op": "eq", "path": "input.bp_target_reached", "value": false}	\N	\N	\N	\N	\N	16	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
e2dcd8e5-7a19-4dc6-a11c-94bc504ba8a4	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_END_REFER	END	Refer to specialized center	Chuyển lên trung tâm chuyên khoa	\N	\N	{"action_type": "REFER_TO_SPECIALIZED_CENTER"}	\N	\N	\N	17	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
b52de82a-7ee3-4efd-b12b-199031f33beb	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_C_FULL	CONDITION	Optimal standard	Tiêu chuẩn tối ưu	{"op": "eq", "path": "input.facility_capability", "value": "FULL_RESOURCES"}	\N	\N	\N	\N	\N	18	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
0b167ff7-f286-4da4-8a3a-0ae20545c7b4	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_OPTIMAL_TREATMENT	ACTION	Treat according to optimal standard and enhance lifestyle changes	Điều trị theo tiêu chuẩn tối ưu và Tăng cường biện pháp tđls, đặc biệt là hạn chế muối	\N	\N	{"action_type": "LIFESTYLE_CHANGES", "salt_restriction": true}	\N	\N	\N	19	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
84342fec-0e0c-4bb5-a676-49c8df14fcc3	8dffe102-09fa-4e81-b2d1-6035da07ad0b	T13_A_CONSIDER_DEVICE	ACTION	Consider device intervention	Xem xét điều trị can thiệp dụng cụ	\N	\N	{"action_type": "CONSIDER_DEVICE_INTERVENTION"}	\N	\N	\N	20	2026-07-04 11:03:11.134834+00	2026-07-04 11:03:11.134834+00
\.

COPY public.decision_edges ("id", "from_node_id", "to_node_id", "traversal_order") FROM stdin;
7153540d-f210-47eb-9bdf-67a5b40e77b4	bb6dadda-b610-4172-8435-88e0111ee741	455fcd4a-e8f2-4b03-b67a-71784b796683	1
7f55db0f-7bde-4030-ad2f-85c335f5f718	bb6dadda-b610-4172-8435-88e0111ee741	b52de82a-7ee3-4efd-b12b-199031f33beb	2
c9aa1f5d-0898-4a9f-896b-9718c2af80f7	455fcd4a-e8f2-4b03-b67a-71784b796683	d98b6c15-9c2b-4b7b-a6cb-f869f625f98a	1
377d0452-46aa-44c4-883d-f159386271c9	d98b6c15-9c2b-4b7b-a6cb-f869f625f98a	583fb951-4f9f-48ef-b652-85c8d6fe7101	1
6254c403-b820-4100-8c42-c040ad5f5c29	583fb951-4f9f-48ef-b652-85c8d6fe7101	379b8afc-b896-410f-bb13-c2e38bef13ad	1
c41e0028-4b25-489f-a3c8-204bdeaf1cf4	583fb951-4f9f-48ef-b652-85c8d6fe7101	39319a8a-753e-4b85-8611-24d214b78327	2
1d339393-b1aa-407c-84f6-80d5dcae8b97	379b8afc-b896-410f-bb13-c2e38bef13ad	ac540e55-906b-437f-a6af-2eccb619bbb5	1
03795239-89ba-4f82-b221-15e359143cea	39319a8a-753e-4b85-8611-24d214b78327	da1ba865-b2d4-4677-85ad-15496aad4653	1
c1ae4e3d-3fa0-4320-b53f-9ab4db9734d9	da1ba865-b2d4-4677-85ad-15496aad4653	d79e31dd-3e3f-43f9-bc55-29657d900c2f	1
d0a185d4-7004-4fde-b18d-27dded426a45	d79e31dd-3e3f-43f9-bc55-29657d900c2f	de43bad7-f682-477d-85ab-a0627f596c6a	1
04b2b928-a131-46d6-b105-990b66d94507	d79e31dd-3e3f-43f9-bc55-29657d900c2f	9479b0ab-7060-4663-8246-d2206d4bc5e5	2
17e6f351-1c1a-4d71-8e7b-021e432a9656	de43bad7-f682-477d-85ab-a0627f596c6a	8e783a9b-44d4-4246-9ab1-4bf9a9190d3b	1
c2923555-8fb0-47cb-9da3-25df8dfd371b	9479b0ab-7060-4663-8246-d2206d4bc5e5	29baba0e-818b-41db-a911-96f799a5b584	1
5511259a-0c86-44f2-a854-ec31bede5549	ac540e55-906b-437f-a6af-2eccb619bbb5	8b2fa240-abcb-47e8-9e3c-9b0a15cb9958	1
e1fb81f7-2959-43ac-b173-4bc037e6ece9	ac540e55-906b-437f-a6af-2eccb619bbb5	879486a4-d0bf-42f2-a772-dcb944ddbb93	2
85365365-f132-4d0f-833b-088a184b5995	8e783a9b-44d4-4246-9ab1-4bf9a9190d3b	8b2fa240-abcb-47e8-9e3c-9b0a15cb9958	1
021e76c8-aeb2-4b15-8958-d6b354f62c0f	8e783a9b-44d4-4246-9ab1-4bf9a9190d3b	879486a4-d0bf-42f2-a772-dcb944ddbb93	2
87ccff51-f99b-447b-a21b-644f6bd9c7af	29baba0e-818b-41db-a911-96f799a5b584	8b2fa240-abcb-47e8-9e3c-9b0a15cb9958	1
f9d2dce5-181f-4c69-822d-ab5038c1e402	29baba0e-818b-41db-a911-96f799a5b584	879486a4-d0bf-42f2-a772-dcb944ddbb93	2
87ff4a86-6c52-4900-903f-6b4a900871ce	8b2fa240-abcb-47e8-9e3c-9b0a15cb9958	3b5b88f1-65e0-4a2d-934b-fb5a965b6df6	1
3218e055-323b-4ca7-b5eb-7061dc4b5fe7	879486a4-d0bf-42f2-a772-dcb944ddbb93	e2dcd8e5-7a19-4dc6-a11c-94bc504ba8a4	1
50957160-9860-4313-b829-5b000d97517e	b52de82a-7ee3-4efd-b12b-199031f33beb	0b167ff7-f286-4da4-8a3a-0ae20545c7b4	1
51a363d2-fa3d-4c1f-8dd3-d9221eb21eaf	0b167ff7-f286-4da4-8a3a-0ae20545c7b4	84342fec-0e0c-4bb5-a676-49c8df14fcc3	1
845e061f-a7cf-4265-91cf-702bb5567d3d	84342fec-0e0c-4bb5-a676-49c8df14fcc3	e2dcd8e5-7a19-4dc6-a11c-94bc504ba8a4	1
\.

COPY public.node_source_references ("id", "node_id", "source_title", "section_path", "locator", "locator_detail", "printed_page_numbers", "pdf_page_numbers", "reference_note", "reference_order") FROM stdin;
86c5c2a7-643c-4c8f-bbab-34d4850a6752	bb6dadda-b610-4172-8435-88e0111ee741	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
725ccd08-03a2-4dcd-8e86-bb7764e384a2	455fcd4a-e8f2-4b03-b67a-71784b796683	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
b142117e-2912-4fea-9813-45d068679eef	d98b6c15-9c2b-4b7b-a6cb-f869f625f98a	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
018cecc8-3b1e-4731-84c6-8add024330c5	583fb951-4f9f-48ef-b652-85c8d6fe7101	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
d3ad703f-1ea7-4963-8d7b-5f3f9656dbde	379b8afc-b896-410f-bb13-c2e38bef13ad	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
ef962ce0-b85c-4eec-82a6-d8da0bf0b28a	ac540e55-906b-437f-a6af-2eccb619bbb5	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
b45bb617-f0c7-4ffb-9cf4-eb26d5733ab9	39319a8a-753e-4b85-8611-24d214b78327	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
f936b545-1c13-4e4c-9c17-e33f3737c350	da1ba865-b2d4-4677-85ad-15496aad4653	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
d92f358f-8148-4208-8c67-a1a2f3d55b3e	d79e31dd-3e3f-43f9-bc55-29657d900c2f	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
3a8c0f64-05b4-429f-93dd-5f03b0179853	de43bad7-f682-477d-85ab-a0627f596c6a	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
8a24a4ef-d019-4867-8624-8ecfcccb9e3c	8e783a9b-44d4-4246-9ab1-4bf9a9190d3b	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
973168e6-c680-4f40-b7b1-94f7bb82ba66	9479b0ab-7060-4663-8246-d2206d4bc5e5	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
0d2f7343-660f-4274-8886-609bbf7be1b7	29baba0e-818b-41db-a911-96f799a5b584	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
f944a5b1-aa37-48a3-aa38-002121321bd5	8b2fa240-abcb-47e8-9e3c-9b0a15cb9958	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
3cad015d-1bc3-49bd-8b08-6542c885d88d	3b5b88f1-65e0-4a2d-934b-fb5a965b6df6	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
6ada36e1-2931-40ed-b7a5-02d7256e543e	879486a4-d0bf-42f2-a772-dcb944ddbb93	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
dee53cf8-de3b-4d29-b440-ae8c80b19929	e2dcd8e5-7a19-4dc6-a11c-94bc504ba8a4	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
a4008906-1c08-4712-aa09-af2beeb5263a	b52de82a-7ee3-4efd-b12b-199031f33beb	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
5e035df0-0390-4e3e-88bd-1f68ace7488b	0b167ff7-f286-4da4-8a3a-0ae20545c7b4	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
872f274f-44fc-4645-8df5-47343d61a67d	84342fec-0e0c-4bb5-a676-49c8df14fcc3	Khuyến cáo của Phân hội Tăng huyết áp - Hội Tim mạch Quốc gia Việt Nam (VSH/VNHA) về chẩn đoán & điều trị tăng huyết áp 2022 (Tóm Tắt)	["3.6. C\u00e1c tr\u01b0\u1eddng h\u1ee3p t\u0103ng huy\u1ebft \u00e1p \u0111\u1eb7c bi\u1ec7t", "3.6.1. T\u0103ng huy\u1ebft \u00e1p kh\u00e1ng tr\u1ecb"]	3.6.1. Tăng huyết áp kháng trị	\N	{24}	{26}	\N	1
\.


-- ================================================================
-- Tree 14: hypertensive-emergency (source: tree14.sql)
-- ================================================================
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

COPY public.development_runtime_logs ("id", "request_id", "environment", "input_payload", "inference_context", "journey", "output_payload", "error_payload", "created_at") FROM stdin;
\.

COPY public.alembic_version ("version_num") FROM stdin;
5c43058f54be
\.


COMMIT;
