"""Candidate selectors for medication-producing tree actions."""

ACTION_SELECTORS: dict[str, list[list[str]]] = {
    "COMBINE_D_SGLT2I_ALDO": [["D", "SGLT2i"]],
    "COMBINE_ABD_ALDO_SGLT2I": [["A", "B", "D", "SGLT2i"]],
    "ADD_A_ARNI_CTTA_UCMC": [["A"]],
    "ADD_A_ARNI_CTTA": [["A"]],
    "COMBINE_ACD_MRA": [["A", "C", "D", "MRA"]],
    "ADD_SPIRONOLACTONE": [["MRA"]],
    "ADD_DIHYDROPYRIDINE_CCB": [["C"]],
    "SELECT_AC_OR_AD": [["A", "C"], ["A", "D"]],
    "FIXED_DOSE_TWO_DRUG_COMBINATION": [["A", "C"], ["A", "D"]],
    "FIXED_DOSE_THREE_DRUG_COMBINATION": [["A", "C", "D"]],
    "PRESCRIBE_D_C_THIAZIDE_PRIORITY": [["D"]],
    "BETA_BLOCKER_3_YEARS": [["B"]],
    "EARLY_BETA_BLOCKER": [["B"]],
    "BETA_BLOCKER_OR_CCB": [["B"], ["C"]],
    "THERAPEUTIC_ALTERNATIVES": [["MRA"], ["D"], ["B"], ["Doxazosin"]],
    "ACUTE_CORONARY_SYNDROME_THERAPY": [["Nitroprusside"], ["Nitroglycerin"], ["Urapidil"]],
    "ACUTE_AORTIC_SYNDROME_THERAPY": [["Esmolol"], ["Labetalol"]],
    "ORAL_ANTIHYPERTENSIVE_THERAPY": [["A"], ["C"], ["D"]],
    "HYPERTENSIVE_ENCEPHALOPATHY_ACUTE_THERAPY": [
        ["Labetalol"],
        ["Nicardipine"],
        ["Nitroprusside"],
    ],
    "ACUTE_ISCHEMIC_STROKE_THROMBOLYSIS_CANDIDATE_THERAPY": [
        ["Labetalol"],
        ["Nicardipine"],
        ["Urapidil"],
    ],
    "ACUTE_ISCHEMIC_STROKE_THERAPY": [["Labetalol"], ["Nicardipine"], ["Nitroprusside"]],
    "ACUTE_INTRACEREBRAL_HEMORRHAGE_THERAPY": [["Nitroglycerin"], ["Labetalol"], ["Urapidil"]],
    "ACUTE_CARDIOGENIC_PULMONARY_EDEMA_THERAPY": [
        ["Labetalol"],
        ["Metoprolol Succinate"],
        ["Metoprolol Tartrate"],
    ],
    "ECLAMPSIA_SEVERE_PREECLAMPSIA_HELLP_THERAPY": [["Labetalol"], ["Nicardipine"]],
    "MALIGNANT_HYPERTENSION_TMA_AKI_THERAPY": [
        ["Labetalol"],
        ["Nicardipine"],
        ["Nitroprusside"],
        ["Urapidil"],
    ],
}
ACTION_SELECTOR_ACTION_TYPES = frozenset(ACTION_SELECTORS)
