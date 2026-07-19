-- Medicine lookup table for the CDSS decision-tree system.
--
-- Source of truth for drug names, dosing, source citation, and prescribing
-- availability. Transcribed from backups/medicine.csv (DRUG0001-DRUG0065),
-- with drug_class assigned per the A/B/C/D class-letter convention used by
-- combination_options in backups/cdss_merged.sql (A = ACEI/ARB, B =
-- beta-blocker, C = calcium-channel blocker, D = diuretic). Drugs outside
-- that scheme (SGLT2i, alpha-blockers, vasodilators, central agonists,
-- direct renin inhibitor, aspirin) have drug_class = NULL.
--
-- The `medicines` table schema is owned by the Alembic migration
-- 8cd7e7adc1fb_create_medicines_table.py -- this file is seed data only (run
-- it against a database that already has that migration applied). To change
-- a dose, name, or availability: edit the matching row below and re-apply.

INSERT INTO medicines
    (drug_id, name, drug_class, subgroup, route, dose_low, dose_usual, dose_max, source, link, available)
VALUES
    ('DRUG0001', 'Diltiazem', 'C', 'CKCa Non-DHP', 'Thuốc Uống', '120 mg', '180 - 240 mg', '240 mg', 'Bảng 10', NULL, true),
    ('DRUG0002', 'Verapamil', 'C', 'CKCa Non-DHP', 'Thuốc Uống', '120 mg', '240 - 360 mg', '360 mg', 'Bảng 10', NULL, true),
    ('DRUG0003', 'Amlodipine', 'C', 'CKCa DHP', 'Thuốc Uống', '2.5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0004', 'Felodipine', 'C', 'CKCa DHP', 'Thuốc Uống', '2.5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0005', 'Isradipine', 'C', 'CKCa DHP', 'Thuốc Uống', '2.5 mg BID', '5 - 10 mg BID', '20 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0006', 'Nifedipine', 'C', 'CKCa DHP', 'Thuốc Uống', '30 mg', '30 - 90 mg', '90 mg', 'Bảng 10', NULL, true),
    ('DRUG0007', 'Nitrendipine', 'C', 'CKCa DHP', 'Thuốc Uống', '10 mg', '20 mg', '20 mg', 'Bảng 10', NULL, true),
    ('DRUG0008', 'Lercanidipine', 'C', 'CKCa DHP', 'Thuốc Uống', '10 mg', '20 mg', '20 mg', 'Bảng 10', NULL, true),
    ('DRUG0009', 'Benazepril', 'A', 'ƯCMC', 'Thuốc Uống', '5 mg', '10 - 40 mg', '40 mg', 'Bảng 10', NULL, true),
    ('DRUG0010', 'Captopril', 'A', 'ƯCMC', 'Thuốc Uống', '12.5 mg BID', '50 - 100 mg BID', '200 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0011', 'Enalapril', 'A', 'ƯCMC', 'Thuốc Uống', '5 mg', '10 - 40 mg', '40 mg', 'Bảng 10', NULL, true),
    ('DRUG0012', 'Fosinopril', 'A', 'ƯCMC', 'Thuốc Uống', '10 mg', '10 - 40 mg', '40 mg', 'Bảng 10', NULL, true),
    ('DRUG0013', 'Lisinopril', 'A', 'ƯCMC', 'Thuốc Uống', '5 mg', '10 - 40 mg', '40 mg', 'Bảng 10', NULL, true),
    ('DRUG0014', 'Perindopril', 'A', 'ƯCMC', 'Thuốc Uống', '3.5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0015', 'Quinapril', 'A', 'ƯCMC', 'Thuốc Uống', '5 mg', '10 - 40 mg', '40 mg', 'Bảng 10', NULL, true),
    ('DRUG0016', 'Ramipril', 'A', 'ƯCMC', 'Thuốc Uống', '2.5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0017', 'Trandolapril', 'A', 'ƯCMC', 'Thuốc Uống', '1 - 2 mg', '2 - 8 mg', '8 mg', 'Bảng 10', NULL, true),
    ('DRUG0018', 'Imidapril', 'A', 'ƯCMC', 'Thuốc Uống', '2.5 - 5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0019', 'Azilsartan', 'A', 'CTTA', 'Thuốc Uống', '40 mg', '80 mg', '80 mg', 'Bảng 10', NULL, true),
    ('DRUG0020', 'Candesartan', 'A', 'CTTA', 'Thuốc Uống', '4 mg', '8 - 32 mg', '32 mg', 'Bảng 10', NULL, true),
    ('DRUG0021', 'Eprosartan', 'A', 'CTTA', 'Thuốc Uống', '400 mg', '600 - 800 mg', '800 mg', 'Bảng 10', NULL, true),
    ('DRUG0022', 'Irbesartan', 'A', 'CTTA', 'Thuốc Uống', '150 mg', '150 - 300 mg', '300 mg', 'Bảng 10', NULL, true),
    ('DRUG0023', 'Losartan', 'A', 'CTTA', 'Thuốc Uống', '50 mg', '50 - 100 mg', '100 mg', 'Bảng 10', NULL, true),
    ('DRUG0024', 'Olmesartan', 'A', 'CTTA', 'Thuốc Uống', '10 mg', '20 - 40 mg', '40 mg', 'Bảng 10', NULL, true),
    ('DRUG0025', 'Telmisartan', 'A', 'CTTA', 'Thuốc Uống', '40 mg', '40 - 80 mg', '80 mg', 'Bảng 10', NULL, true),
    ('DRUG0026', 'Valsartan', 'A', 'CTTA', 'Thuốc Uống', '80 mg', '80 - 320 mg', '320 mg', 'Bảng 10', NULL, true),
    ('DRUG0027', 'Bendroflumethiazide', 'D', 'LT Thiazide', 'Thuốc Uống', '5 mg', '10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0028', 'Chlorthalidone', 'D', 'LT Thiazide-like', 'Thuốc Uống', '12.5 mg', '12.5 - 25 mg', '25 mg', 'Bảng 10', NULL, true),
    ('DRUG0029', 'Hydrochlorothiazide', 'D', 'LT Thiazide', 'Thuốc Uống', '12.5 mg', '12.5 - 50 mg', '50 mg', 'Bảng 10', NULL, true),
    ('DRUG0030', 'Indapamide', 'D', 'LT Thiazide-like', 'Thuốc Uống', '1.25 mg', '2.5 mg', '2.5 mg', 'Bảng 10', NULL, true),
    ('DRUG0031', 'Bumetanide', 'D', 'LT quai', 'Thuốc Uống', '0.5 mg', '1 mg', '1 mg', 'Bảng 10', NULL, true),
    ('DRUG0032', 'Furosemide', 'D', 'LT quai', 'Thuốc Uống/Thuốc Truyền Tĩnh Mạch', '20 mg BID', '40 mg BID', 'Variable', 'Bảng 10', NULL, true),
    ('DRUG0033', 'Torsemide', 'D', 'LT quai', 'Thuốc Uống', '5 mg', '10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0034', 'Amiloride', 'D', 'LT giữ Kali', 'Thuốc Uống', '5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0035', 'Eplerenone', 'D', 'LT giữ Kali (MRA)', 'Thuốc Uống', '25 mg', '50 - 100 mg', '100 mg', 'Bảng 10', NULL, true),
    ('DRUG0036', 'Spironolactone', 'D', 'LT giữ Kali (MRA)', 'Thuốc Uống', '12.5 mg', '25 - 50 mg', '50 mg', 'Bảng 10', NULL, true),
    ('DRUG0037', 'Triamterene', 'D', 'LT giữ Kali', 'Thuốc Uống', '100 mg', '100 mg', '100 mg', 'Bảng 10', NULL, true),
    ('DRUG0038', 'Acebutolol', 'B', 'CB', 'Thuốc Uống', '200 mg', '200 - 400 mg', '400 mg', 'Bảng 10', NULL, true),
    ('DRUG0039', 'Atenolol', 'B', 'CB', 'Thuốc Uống', '25 mg', '100 mg', '100 mg', 'Bảng 10', NULL, true),
    ('DRUG0040', 'Bisoprolol', 'B', 'CB', 'Thuốc Uống', '5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0041', 'Carvedilol', 'B', 'CB', 'Thuốc Uống', '3.125 mg BID', '6.25 - 25 mg BID', '50 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0042', 'Labetalol', 'B', 'CB', 'Thuốc Uống/Thuốc Truyền Tĩnh Mạch', '100 mg BID', '100 - 300 mg BID', '600 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0043', 'Metoprolol Succinate', 'B', 'CB', 'Thuốc Uống', '25 mg', '50 - 100 mg', '100 mg', 'Bảng 10', NULL, true),
    ('DRUG0044', 'Metoprolol Tartrate', 'B', 'CB', 'Thuốc Uống', '25 mg BID', '50 - 100 mg BID', '200 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0045', 'Nadolol', 'B', 'CB', 'Thuốc Uống', '20 mg', '40 - 80 mg', '80 mg', 'Bảng 10', NULL, true),
    ('DRUG0046', 'Nebivolol', 'B', 'CB', 'Thuốc Uống', '2.5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0047', 'Propranolol', 'B', 'CB', 'Thuốc Uống', '40 mg BID', '40 - 160 mg BID', '320 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0048', 'Aliskiren', NULL, 'Ức chế Renin trực tiếp', 'Thuốc Uống', '75 mg', '150 - 300 mg', '300 mg', 'Bảng 10', NULL, true),
    ('DRUG0049', 'Doxazosin', NULL, 'Ức chế thụ thể Alpha giao cảm', 'Thuốc Uống', '1 mg', '1 - 2 mg', '2 mg', 'Bảng 10', NULL, true),
    ('DRUG0050', 'Prazosin', NULL, 'Ức chế thụ thể Alpha giao cảm', 'Thuốc Uống', '1 mg BID', '1 - 5 mg BID', '10 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0051', 'Terazosin', NULL, 'Ức chế thụ thể Alpha giao cảm', 'Thuốc Uống', '1 mg', '1 - 2 mg', '2 mg', 'Bảng 10', NULL, true),
    ('DRUG0052', 'Hydralazine', NULL, 'Giãn mạch', 'Thuốc Uống/Thuốc Truyền Tĩnh Mạch', '10 mg BID', '25 - 100 mg BID', '200 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0053', 'Minoxidil', NULL, 'Giãn mạch', 'Thuốc Uống', '2.5 mg', '5 - 10 mg', '10 mg', 'Bảng 10', NULL, true),
    ('DRUG0054', 'Clonidine', NULL, 'Chủ vận chọn lọc alpha-2 giao cảm', 'Thuốc Uống', '0.1 mg BID', '0.1 - 0.2 mg BID', '0.4 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0055', 'Methyldopa', NULL, 'Chủ vận chọn lọc alpha-2 giao cảm', 'Thuốc Uống', '125 mg BID', '250 - 500 mg BID', '1000 mg/ngày', 'Bảng 10', NULL, true),
    ('DRUG0056', 'Reserpine', NULL, 'Giảm Adrenergic', 'Thuốc Uống', '0.1 mg', '0.1 - 0.25 mg', '0.25 mg', 'Bảng 10', NULL, true),
    ('DRUG0057', 'Nicardipine', 'C', 'CKCa DHP', 'Thuốc Truyền Tĩnh Mạch', '3 mg/giờ', '5 mg/giờ', '15 mg/giờ', 'Mục 3.7.5', 'https://drugs.com/dosage/nicardipine.html', true),
    ('DRUG0058', 'Clevidipine', 'C', 'CKCa DHP', 'Thuốc Truyền Tĩnh Mạch', '1 - 2 mg/giờ', '4 - 6 mg/giờ', '16-32 mg/giờ', 'Mục 3.7.5', 'https://drugs.com/dosage/clevidipine.html', true),
    ('DRUG0059', 'Esmolol', 'B', 'CB', 'Thuốc Truyền Tĩnh Mạch', '50 mcg/kg/phút', '50-250 mcg/kg/phút', '300 mcg/kg/phút', 'Mục 3.7.5', 'https://drugs.com/dosage/esmolol.html', true),
    ('DRUG0060', 'Nitroprusside', NULL, 'Giãn mạch', 'Thuốc Truyền Tĩnh Mạch', '0.3 mcg/kg/phút', '0.3-10 mcg/kg/phút', '10 mcg/kg/phút', 'Mục 3.7.5', 'https://drugs.com/dosage/nitroprusside.html', true),
    ('DRUG0061', 'Nitroglycerin', NULL, 'Giãn mạch', 'Thuốc Truyền Tĩnh Mạch', '5 mcg/phút', '10 mcg/phút', '20 mcg/phút', 'Mục 3.7.5', 'https://drugs.com/dosage/nitroglycerin.html', true),
    ('DRUG0062', 'Dapagliflozin', 'SGLT2i', 'SGLT2i', 'Thuốc Uống', '5-10 mg', '10 mg', '10 mg', 'Mục 3.7.1', NULL, true),
    ('DRUG0063', 'Empagliflozin', 'SGLT2i', 'SGLT2i', 'Thuốc Uống', '10 mg', '10 mg', '25 mg', 'Mục 3.7.1', NULL, true),
    ('DRUG0064', 'Urapidil', NULL, 'Ức chế thụ thể Alpha giao cảm', 'Thuốc Uống/Thuốc Truyền Tĩnh Mạch', NULL, NULL, NULL, NULL, NULL, true),
    ('DRUG0065', 'Aspirin', NULL, NULL, NULL, '75 - 81 mg/ngày', NULL, '150 - 162 mg/ngày', NULL, 'https://www.drugs.com/pregnancy/aspirin.html ; https://www.drugs.com/dosage/aspirin.html', true);
