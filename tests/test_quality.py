from sleep_agent.signal.quality import assess_quality


def test_quality_explains_rejection():
    result = assess_quality(coverage=.8, contact_fraction=.7, motion_fraction=.2,
                            abnormal_rr_fraction=.3)
    assert not result.usable
    assert set(result.reasons) == {"coverage_below_threshold", "contact_below_threshold",
                                   "excessive_motion", "too_many_abnormal_rr"}

