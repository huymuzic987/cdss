BEGIN;
COPY public.decision_trees ("id", "tree_key", "name_en", "name_vi", "created_at", "updated_at") FROM stdin;
29fdf73f-e05d-4169-8e03-2345298d9a40	resistant-hypertension	Resistant Hypertension	THA Kháng trị	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
\.

COPY public.decision_nodes ("id", "tree_id", "node_key", "node_type", "text_en", "text_vi", "condition_definition", "context_patch", "action_payload", "global_config", "link_target_tree_key", "link_target_node_key", "display_order", "created_at", "updated_at") FROM stdin;
06cea1f6-0a85-49a2-94c8-220d063c93e7	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_START	START	Essential Treatment Strategy Tree (Tree 4) or Optimal Treatment Strategy Tree (Tree 5)	Cây 4: cây chiến lược điều trị thiết yếu hoặc Cây 5: cây chiến lược điều trị tối ưu	\N	\N	\N	\N	\N	\N	1	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
05265e46-631a-4c97-95c5-d1bf708010dd	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_C_LIMITED	CONDITION	Essential standard	Tiêu chuẩn thiết yếu	{"op": "eq", "path": "input.facility_capability", "value": "LIMITED_RESOURCES"}	\N	\N	\N	\N	\N	2	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
40fa0236-4b64-4703-a5bb-dcaf057e764b	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_ESSENTIAL_TREATMENT	ACTION	Treat according to essential standard and enhance lifestyle changes	Điều trị theo tiêu chuẩn thiết yếu và Tăng cường biện pháp tđls, đặc biệt là hạn chế muối	\N	\N	{"action_type": "LIFESTYLE_CHANGES", "salt_restriction": true}	\N	\N	\N	3	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
104875ba-0e23-4f34-8459-8d6e358ac8ed	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_CHECK_MRA	ACTION	Check MRA tolerance	Kiểm tra khả năng dung nạp MRA	\N	\N	{"action_type": "CHECK_MRA"}	\N	\N	\N	4	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
6142eb40-d033-4c21-80e7-bdcf1f7345c1	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_C_MRA_TOLERATED	CONDITION	Tolerates MRA	Có khả năng dung nạp MRA	{"op": "eq", "path": "input.tolerates_mra", "value": true}	\N	\N	\N	\N	\N	5	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
2662655b-5ab6-45fd-9e3b-3189a355159f	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_ADD_MRA	ACTION	Combine A + C + D and MRA	Phối hợp 3 nhóm thuốc A + C + D và MRA	\N	\N	{"action_type": "COMBINE_ACD_MRA"}	\N	\N	\N	6	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
8e0afc9d-f184-4acf-af88-a32095ee2011	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_C_MRA_NOT_TOLERATED	CONDITION	Does not tolerate MRA	Không có khả năng dung nạp MRA	{"op": "eq", "path": "input.tolerates_mra", "value": false}	\N	\N	\N	\N	\N	7	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
8ece95f0-fbe6-4357-a5ec-1d03b072f233	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_ADD_D	ACTION	Add D	Thêm D	\N	\N	{"action_type": "ADD_D"}	\N	\N	\N	8	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
18afbaf4-68d2-4faf-a3e9-88aeaa331210	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_CHECK_SPIRONOLACTONE	ACTION	Check Spironolactone tolerance	Kiểm tra khả năng dung nạp Spironolactone (lợi tiểu giữ kali)	\N	\N	{"action_type": "CHECK_SPIRONOLACTONE"}	\N	\N	\N	9	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
07085f60-469e-4017-9575-7fc0ae166344	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_C_SPIRONOLACTONE_TOLERATED	CONDITION	Tolerates Spironolactone	Có khả năng dung nạp Spironolactone	{"op": "eq", "path": "input.tolerates_spironolactone", "value": true}	\N	\N	\N	\N	\N	10	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
6414da5a-ff21-4186-97c2-1f7e80a1aee9	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_ADD_SPIRONOLACTONE	ACTION	Add low-dose Spironolactone to current regimen	Thêm Spironolactone liều thấp kết hợp với liều thuốc điều trị hiện có	\N	\N	{"action_type": "ADD_SPIRONOLACTONE"}	\N	\N	\N	11	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
788cf095-da5d-4484-ae11-ff17d678b280	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_C_SPIRONOLACTONE_NOT_TOLERATED	CONDITION	Does not tolerate Spironolactone	Không có khả năng dung nạp Spironolactone	{"op": "eq", "path": "input.tolerates_spironolactone", "value": false}	\N	\N	\N	\N	\N	12	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
b946d492-ef93-4ffa-993c-f236e71e2435	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_ALTERNATIVES	ACTION	Alternatives: Add K-sparing D, Increase D dose, or Add Bisoprolol/Doxazosin	Thêm nhóm D giữ kali, Tăng liều nhóm D, hoặc Thêm Bisoprolol/Doxazosin	\N	\N	{"action_type": "THERAPEUTIC_ALTERNATIVES"}	\N	\N	\N	13	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
7b6597c3-43f3-4fe0-a28f-1d5d016ad874	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_C_BP_TARGET_REACHED	CONDITION	BP reaches target	HA đạt đích điều trị	{"op": "eq", "path": "input.bp_target_reached", "value": true}	\N	\N	\N	\N	\N	14	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
0f3b8386-1fdd-4902-986e-18131ebfdbe1	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_END_MAINTAIN	END	Maintain regimen	Duy trì phác đồ	\N	\N	{"action_type": "MAINTAIN_REGIMEN"}	\N	\N	\N	15	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
268aa20d-efe0-4447-86e2-a9caed2f71d5	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_C_BP_TARGET_NOT_REACHED	CONDITION	BP does not reach target	HA không đạt đích điều trị	{"op": "eq", "path": "input.bp_target_reached", "value": false}	\N	\N	\N	\N	\N	16	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
b7276f90-254d-418a-91f7-46bdd3c6150a	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_END_REFER	END	Refer to specialized center	Chuyển lên trung tâm chuyên khoa	\N	\N	{"action_type": "REFER_TO_SPECIALIZED_CENTER"}	\N	\N	\N	17	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
b3151b48-378a-467c-925b-124936a21a53	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_C_FULL	CONDITION	Optimal standard	Tiêu chuẩn tối ưu	{"op": "eq", "path": "input.facility_capability", "value": "FULL_RESOURCES"}	\N	\N	\N	\N	\N	18	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
24c26607-3628-4f3c-bcc6-db869ad881c3	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_OPTIMAL_TREATMENT	ACTION	Treat according to optimal standard and enhance lifestyle changes	Điều trị theo tiêu chuẩn tối ưu và Tăng cường biện pháp tđls, đặc biệt là hạn chế muối	\N	\N	{"action_type": "LIFESTYLE_CHANGES", "salt_restriction": true}	\N	\N	\N	19	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
ba927375-f61f-4be6-b165-fc78c40ee73a	29fdf73f-e05d-4169-8e03-2345298d9a40	T13_A_CONSIDER_DEVICE	ACTION	Consider device intervention	Xem xét điều trị can thiệp dụng cụ	\N	\N	{"action_type": "CONSIDER_DEVICE_INTERVENTION"}	\N	\N	\N	20	2026-07-04 09:34:49.785184+00	2026-07-04 09:34:49.785184+00
\.

COPY public.decision_edges ("id", "from_node_id", "to_node_id", "traversal_order") FROM stdin;
b34a483a-ce46-4daf-99a1-2311229e81f3	06cea1f6-0a85-49a2-94c8-220d063c93e7	05265e46-631a-4c97-95c5-d1bf708010dd	1
0fe25dd5-2637-48de-805b-46a7c29bdf75	06cea1f6-0a85-49a2-94c8-220d063c93e7	b3151b48-378a-467c-925b-124936a21a53	2
a5b52ec2-7da1-4ff5-a83c-a3771a973884	05265e46-631a-4c97-95c5-d1bf708010dd	40fa0236-4b64-4703-a5bb-dcaf057e764b	1
99ed586f-3568-4b87-9dd3-b24bed15f5b3	40fa0236-4b64-4703-a5bb-dcaf057e764b	104875ba-0e23-4f34-8459-8d6e358ac8ed	1
84fbbd91-a150-4efd-97fc-dc13e617e97e	104875ba-0e23-4f34-8459-8d6e358ac8ed	6142eb40-d033-4c21-80e7-bdcf1f7345c1	1
8e70df0c-0df7-4f9d-8d15-f5258c4cc97c	104875ba-0e23-4f34-8459-8d6e358ac8ed	8e0afc9d-f184-4acf-af88-a32095ee2011	2
203048d1-9bde-4a2d-85d7-caa9baab2b9b	6142eb40-d033-4c21-80e7-bdcf1f7345c1	2662655b-5ab6-45fd-9e3b-3189a355159f	1
7184293a-643d-452a-b2b7-bbdabe35074b	8e0afc9d-f184-4acf-af88-a32095ee2011	8ece95f0-fbe6-4357-a5ec-1d03b072f233	1
0506f19c-76a8-412b-ae26-d2add4190394	8ece95f0-fbe6-4357-a5ec-1d03b072f233	18afbaf4-68d2-4faf-a3e9-88aeaa331210	1
815e83f0-f661-4d99-ad70-f626e0077935	18afbaf4-68d2-4faf-a3e9-88aeaa331210	07085f60-469e-4017-9575-7fc0ae166344	1
c8314897-7ae5-4c02-b098-adac0b70e42e	18afbaf4-68d2-4faf-a3e9-88aeaa331210	788cf095-da5d-4484-ae11-ff17d678b280	2
04f4c437-3f59-4253-9405-371d0216bef4	07085f60-469e-4017-9575-7fc0ae166344	6414da5a-ff21-4186-97c2-1f7e80a1aee9	1
a7390161-bf70-423d-82d2-610b25459e15	788cf095-da5d-4484-ae11-ff17d678b280	b946d492-ef93-4ffa-993c-f236e71e2435	1
664f00d0-5a7c-41d3-9b95-bea7b8d12940	2662655b-5ab6-45fd-9e3b-3189a355159f	7b6597c3-43f3-4fe0-a28f-1d5d016ad874	1
4f2c58a3-f34e-4339-b813-4962b9cbd308	2662655b-5ab6-45fd-9e3b-3189a355159f	268aa20d-efe0-4447-86e2-a9caed2f71d5	2
3e6f6c6b-5d8b-4821-b739-3d04b2308154	6414da5a-ff21-4186-97c2-1f7e80a1aee9	7b6597c3-43f3-4fe0-a28f-1d5d016ad874	1
bc04ff1d-5c23-47c3-8c3a-98726a025000	6414da5a-ff21-4186-97c2-1f7e80a1aee9	268aa20d-efe0-4447-86e2-a9caed2f71d5	2
f64a8ff2-a260-4ae2-a0ce-7d43c97131ca	b946d492-ef93-4ffa-993c-f236e71e2435	7b6597c3-43f3-4fe0-a28f-1d5d016ad874	1
f91e9e92-ea48-4e47-a1d5-1334f055bfe0	b946d492-ef93-4ffa-993c-f236e71e2435	268aa20d-efe0-4447-86e2-a9caed2f71d5	2
b6937d7e-deec-4f89-b88f-f9fd867b5bde	7b6597c3-43f3-4fe0-a28f-1d5d016ad874	0f3b8386-1fdd-4902-986e-18131ebfdbe1	1
0d32f601-1d54-4a6e-9f46-44d7179e922f	268aa20d-efe0-4447-86e2-a9caed2f71d5	b7276f90-254d-418a-91f7-46bdd3c6150a	1
8399282c-1af3-40a0-8b39-d3184897ccad	b3151b48-378a-467c-925b-124936a21a53	24c26607-3628-4f3c-bcc6-db869ad881c3	1
d823e933-31cc-4298-beaf-4d6e6e3d0fdd	24c26607-3628-4f3c-bcc6-db869ad881c3	ba927375-f61f-4be6-b165-fc78c40ee73a	1
2fcd251d-1c06-4daf-b5fa-1d675b12d7ac	ba927375-f61f-4be6-b165-fc78c40ee73a	b7276f90-254d-418a-91f7-46bdd3c6150a	1
\.

COMMIT;
