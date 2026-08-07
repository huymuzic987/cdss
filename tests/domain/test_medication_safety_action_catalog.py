from cdss.domain.medication_safety.medication_safety_action_catalog import ACTION_SELECTORS


def test_acute_cardiogenic_pulmonary_edema_lists_both_metoprolol_salts() -> None:
    assert ACTION_SELECTORS["ACUTE_CARDIOGENIC_PULMONARY_EDEMA_THERAPY"] == [
        ["Labetalol"],
        ["Metoprolol Succinate"],
        ["Metoprolol Tartrate"],
    ]
