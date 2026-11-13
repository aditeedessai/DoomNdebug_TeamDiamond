"""M3-08 Priority Calculation Test Suite (24 Test Scenarios).

Tests:
1. Severity 1, report_count 1, overdue 0 -> Low (score 10)
2. Severity 3, report_count 1 -> Low (score 30)
3. Severity 3, report_count 2 -> Medium (score 35)
4. Severity 5, report_count 1 -> Medium (score 50)
5. Severity 5, report_count 3, overdue 10 -> High (score 70)
6. Severity 7, report_count 1 -> High (score 70)
7. Severity 7, report_count 3 -> Critical (score 80)
8. Severity 7, report_count 1, overdue 10 -> Critical (score 80)
9. Severity 8, report_count 1 -> Critical (score 80)
10. Score boundary 34 -> Low
11. Score boundary 35 -> Medium
12. Score boundary 59 -> Medium
13. Score boundary 60 -> High
14. Score boundary 79 -> High
15. Score boundary 80 -> Critical
16. Multiple community reports without an arbitrary bonus cap
17. Overdue bonus defaults to zero
18. Negative and zero severity rejected (ValueError)
19. Severity above 10 rejected (ValueError)
20. Report count below 1 rejected (ValueError)
21. Negative overdue bonus rejected (ValueError)
22. Booleans rejected for every parameter (ValueError)
23. Floats and numeric strings rejected (ValueError)
24. None and non-finite values rejected (ValueError)
"""
import sys
import os

# Add backend directory to sys.path
backend_path = r"c:\Users\Nishtaa\Desktop\DoomNdebug_TeamDiamond\backend"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if 'backend' not in sys.path:
    sys.path.insert(0, 'backend')

from app.services.priority_service import PriorityService, priority_service


def test_01_sev1_rep1_ovd0():
    """Test 1: Severity 1, report_count 1, overdue 0 -> Low."""
    res = priority_service.calculate_priority(severity=1, report_count=1, overdue_bonus=0)
    score = priority_service.calculate_priority_score(severity=1, report_count=1, overdue_bonus=0)
    assert score == 10, f"Expected score 10, got {score}"
    assert res == "Low", f"Expected 'Low', got {res}"
    print("PASS: Test 01 - Severity 1, report_count 1, overdue 0 -> Low (score 10)")


def test_02_sev3_rep1():
    """Test 2: Severity 3, report_count 1 -> Low."""
    res = priority_service.calculate_priority(severity=3, report_count=1)
    score = priority_service.calculate_priority_score(severity=3, report_count=1)
    assert score == 30, f"Expected score 30, got {score}"
    assert res == "Low", f"Expected 'Low', got {res}"
    print("PASS: Test 02 - Severity 3, report_count 1 -> Low (score 30)")


def test_03_sev3_rep2():
    """Test 3: Severity 3, report_count 2 -> Medium (escalation from Low)."""
    res = priority_service.calculate_priority(severity=3, report_count=2)
    score = priority_service.calculate_priority_score(severity=3, report_count=2)
    assert score == 35, f"Expected score 35, got {score}"
    assert res == "Medium", f"Expected 'Medium', got {res}"
    print("PASS: Test 03 - Severity 3, report_count 2 -> Medium (score 35)")


def test_04_sev5_rep1():
    """Test 4: Severity 5, report_count 1 -> Medium."""
    res = priority_service.calculate_priority(severity=5, report_count=1)
    score = priority_service.calculate_priority_score(severity=5, report_count=1)
    assert score == 50, f"Expected score 50, got {score}"
    assert res == "Medium", f"Expected 'Medium', got {res}"
    print("PASS: Test 04 - Severity 5, report_count 1 -> Medium (score 50)")


def test_05_sev5_rep3_ovd10():
    """Test 5: Severity 5, report_count 3, overdue 10 -> High."""
    # (5 * 10) + (3 - 1) * 5 + 10 = 50 + 10 + 10 = 70
    res = priority_service.calculate_priority(severity=5, report_count=3, overdue_bonus=10)
    score = priority_service.calculate_priority_score(severity=5, report_count=3, overdue_bonus=10)
    assert score == 70, f"Expected score 70, got {score}"
    assert res == "High", f"Expected 'High', got {res}"
    print("PASS: Test 05 - Severity 5, report_count 3, overdue 10 -> High (score 70)")


def test_06_sev7_rep1():
    """Test 6: Severity 7, report_count 1 -> High."""
    res = priority_service.calculate_priority(severity=7, report_count=1)
    score = priority_service.calculate_priority_score(severity=7, report_count=1)
    assert score == 70, f"Expected score 70, got {score}"
    assert res == "High", f"Expected 'High', got {res}"
    print("PASS: Test 06 - Severity 7, report_count 1 -> High (score 70)")


def test_07_sev7_rep3():
    """Test 7: Severity 7, report_count 3 -> Critical (escalation from High)."""
    # (7 * 10) + (3 - 1) * 5 + 0 = 70 + 10 = 80
    res = priority_service.calculate_priority(severity=7, report_count=3)
    score = priority_service.calculate_priority_score(severity=7, report_count=3)
    assert score == 80, f"Expected score 80, got {score}"
    assert res == "Critical", f"Expected 'Critical', got {res}"
    print("PASS: Test 07 - Severity 7, report_count 3 -> Critical (score 80)")


def test_08_sev7_rep1_ovd10():
    """Test 8: Severity 7, report_count 1, overdue 10 -> Critical (escalation via overdue)."""
    # (7 * 10) + 0 + 10 = 80
    res = priority_service.calculate_priority(severity=7, report_count=1, overdue_bonus=10)
    score = priority_service.calculate_priority_score(severity=7, report_count=1, overdue_bonus=10)
    assert score == 80, f"Expected score 80, got {score}"
    assert res == "Critical", f"Expected 'Critical', got {res}"
    print("PASS: Test 08 - Severity 7, report_count 1, overdue 10 -> Critical (score 80)")


def test_09_sev8_rep1():
    """Test 9: Severity 8, report_count 1 -> Critical."""
    # (8 * 10) + 0 + 0 = 80
    res = priority_service.calculate_priority(severity=8, report_count=1)
    score = priority_service.calculate_priority_score(severity=8, report_count=1)
    assert score == 80, f"Expected score 80, got {score}"
    assert res == "Critical", f"Expected 'Critical', got {res}"
    print("PASS: Test 09 - Severity 8, report_count 1 -> Critical (score 80)")


def test_10_boundary_34_low():
    """Test 10: Score boundary 34 -> Low."""
    # sev=3 (30) + rep=1 (0) + ovd=4 (4) = 34
    res = priority_service.calculate_priority(severity=3, report_count=1, overdue_bonus=4)
    score = priority_service.calculate_priority_score(severity=3, report_count=1, overdue_bonus=4)
    assert score == 34
    assert res == "Low"
    print("PASS: Test 10 - Boundary score 34 -> Low")


def test_11_boundary_35_medium():
    """Test 11: Score boundary 35 -> Medium."""
    # sev=3 (30) + rep=2 (5) + ovd=0 = 35
    res = priority_service.calculate_priority(severity=3, report_count=2, overdue_bonus=0)
    score = priority_service.calculate_priority_score(severity=3, report_count=2, overdue_bonus=0)
    assert score == 35
    assert res == "Medium"
    print("PASS: Test 11 - Boundary score 35 -> Medium")


def test_12_boundary_59_medium():
    """Test 12: Score boundary 59 -> Medium."""
    # sev=5 (50) + rep=1 (0) + ovd=9 (9) = 59
    res = priority_service.calculate_priority(severity=5, report_count=1, overdue_bonus=9)
    score = priority_service.calculate_priority_score(severity=5, report_count=1, overdue_bonus=9)
    assert score == 59
    assert res == "Medium"
    print("PASS: Test 12 - Boundary score 59 -> Medium")


def test_13_boundary_60_high():
    """Test 13: Score boundary 60 -> High."""
    # sev=6 (60) + rep=1 (0) + ovd=0 = 60
    res = priority_service.calculate_priority(severity=6, report_count=1, overdue_bonus=0)
    score = priority_service.calculate_priority_score(severity=6, report_count=1, overdue_bonus=0)
    assert score == 60
    assert res == "High"
    print("PASS: Test 13 - Boundary score 60 -> High")


def test_14_boundary_79_high():
    """Test 14: Score boundary 79 -> High."""
    # sev=7 (70) + rep=2 (5) + ovd=4 (4) = 79
    res = priority_service.calculate_priority(severity=7, report_count=2, overdue_bonus=4)
    score = priority_service.calculate_priority_score(severity=7, report_count=2, overdue_bonus=4)
    assert score == 79
    assert res == "High"
    print("PASS: Test 14 - Boundary score 79 -> High")


def test_15_boundary_80_critical():
    """Test 15: Score boundary 80 -> Critical."""
    # sev=8 (80) + rep=1 (0) + ovd=0 = 80
    res = priority_service.calculate_priority(severity=8, report_count=1, overdue_bonus=0)
    score = priority_service.calculate_priority_score(severity=8, report_count=1, overdue_bonus=0)
    assert score == 80
    assert res == "Critical"
    print("PASS: Test 15 - Boundary score 80 -> Critical")


def test_16_multiple_community_reports_uncapped():
    """Test 16: Multiple community reports without arbitrary bonus cap."""
    # sev=2 (20), rep=15 -> bonus = (15 - 1) * 5 = 70. score = 20 + 70 = 90
    res = priority_service.calculate_priority(severity=2, report_count=15)
    score = priority_service.calculate_priority_score(severity=2, report_count=15)
    assert score == 90, f"Expected 90 without cap, got {score}"
    assert res == "Critical"

    # sev=1 (10), rep=25 -> bonus = 24 * 5 = 120. score = 130
    res_large = priority_service.calculate_priority(severity=1, report_count=25)
    score_large = priority_service.calculate_priority_score(severity=1, report_count=25)
    assert score_large == 130
    assert res_large == "Critical"
    print("PASS: Test 16 - Multiple community reports follow exact formula without arbitrary cap")


def test_17_overdue_bonus_defaults_to_zero():
    """Test 17: Overdue bonus defaults to zero when omitted."""
    # Calling with only severity
    res_default = priority_service.calculate_priority(severity=5)
    score_default = priority_service.calculate_priority_score(severity=5)
    assert score_default == 50
    assert res_default == "Medium"

    # Explicit overdue_bonus=0 matches default
    res_explicit = priority_service.calculate_priority(severity=5, report_count=1, overdue_bonus=0)
    score_explicit = priority_service.calculate_priority_score(severity=5, report_count=1, overdue_bonus=0)
    assert res_default == res_explicit
    assert score_default == score_explicit
    print("PASS: Test 17 - Overdue bonus defaults cleanly to zero")


def test_18_negative_and_zero_severity_rejected():
    """Test 18: Negative and zero severity rejected with ValueError."""
    for invalid_sev in [0, -1, -5, -99]:
        try:
            priority_service.calculate_priority(severity=invalid_sev)
            assert False, f"Expected ValueError for severity={invalid_sev}"
        except ValueError as e:
            assert "severity" in str(e).lower()

    print("PASS: Test 18 - Negative and zero severity rejected")


def test_19_severity_above_10_rejected():
    """Test 19: Severity above 10 rejected with ValueError."""
    for invalid_sev in [11, 12, 100]:
        try:
            priority_service.calculate_priority(severity=invalid_sev)
            assert False, f"Expected ValueError for severity={invalid_sev}"
        except ValueError as e:
            assert "severity" in str(e).lower()

    print("PASS: Test 19 - Severity above 10 rejected")


def test_20_report_count_below_1_rejected():
    """Test 20: Report count below 1 rejected with ValueError."""
    for invalid_rc in [0, -1, -10]:
        try:
            priority_service.calculate_priority(severity=5, report_count=invalid_rc)
            assert False, f"Expected ValueError for report_count={invalid_rc}"
        except ValueError as e:
            assert "report_count" in str(e).lower()

    print("PASS: Test 20 - Report count below 1 rejected")


def test_21_negative_overdue_bonus_rejected():
    """Test 21: Negative overdue bonus rejected with ValueError."""
    for invalid_ovd in [-1, -5, -100]:
        try:
            priority_service.calculate_priority(severity=5, report_count=1, overdue_bonus=invalid_ovd)
            assert False, f"Expected ValueError for overdue_bonus={invalid_ovd}"
        except ValueError as e:
            assert "overdue_bonus" in str(e).lower()

    print("PASS: Test 21 - Negative overdue bonus rejected")


def test_22_booleans_rejected():
    """Test 22: Booleans rejected explicitly for every parameter."""
    # Python treats bool as subclass of int: isinstance(True, int) is True
    # Verify True and False are rejected for all parameters

    # severity
    for b in [True, False]:
        try:
            priority_service.calculate_priority(severity=b)
            assert False, f"Expected ValueError for severity={b}"
        except ValueError as e:
            assert "severity" in str(e).lower()

    # report_count
    for b in [True, False]:
        try:
            priority_service.calculate_priority(severity=5, report_count=b)
            assert False, f"Expected ValueError for report_count={b}"
        except ValueError as e:
            assert "report_count" in str(e).lower()

    # overdue_bonus
    for b in [True, False]:
        try:
            priority_service.calculate_priority(severity=5, report_count=1, overdue_bonus=b)
            assert False, f"Expected ValueError for overdue_bonus={b}"
        except ValueError as e:
            assert "overdue_bonus" in str(e).lower()

    print("PASS: Test 22 - Booleans rejected for every parameter")


def test_23_floats_and_strings_rejected():
    """Test 23: Floats and numeric strings rejected with ValueError."""
    # severity
    for invalid in [5.0, 7.5, "5", "seven"]:
        try:
            priority_service.calculate_priority(severity=invalid)
            assert False, f"Expected ValueError for severity={invalid}"
        except ValueError as e:
            assert "severity" in str(e).lower()

    # report_count
    for invalid in [2.0, 3.5, "2", "many"]:
        try:
            priority_service.calculate_priority(severity=5, report_count=invalid)
            assert False, f"Expected ValueError for report_count={invalid}"
        except ValueError as e:
            assert "report_count" in str(e).lower()

    # overdue_bonus
    for invalid in [10.0, 5.5, "10", "overdue"]:
        try:
            priority_service.calculate_priority(severity=5, report_count=1, overdue_bonus=invalid)
            assert False, f"Expected ValueError for overdue_bonus={invalid}"
        except ValueError as e:
            assert "overdue_bonus" in str(e).lower()

    print("PASS: Test 23 - Floats and numeric strings rejected")


def test_24_none_and_non_finite_rejected():
    """Test 24: None and non-finite values rejected with ValueError."""
    for invalid in [None, float("nan"), float("inf"), float("-inf"), [], {}]:
        try:
            priority_service.calculate_priority(severity=invalid)
            assert False, f"Expected ValueError for severity={invalid}"
        except ValueError:
            pass

        try:
            priority_service.calculate_priority(severity=5, report_count=invalid)
            assert False, f"Expected ValueError for report_count={invalid}"
        except ValueError:
            pass

        try:
            priority_service.calculate_priority(severity=5, report_count=1, overdue_bonus=invalid)
            assert False, f"Expected ValueError for overdue_bonus={invalid}"
        except ValueError:
            pass

    print("PASS: Test 24 - None and non-finite values rejected")


if __name__ == "__main__":
    print("=" * 70)
    print("Running Member 3 Task M3-08 - Deterministic Priority Calculation Test Suite")
    print("=" * 70)

    test_01_sev1_rep1_ovd0()
    test_02_sev3_rep1()
    test_03_sev3_rep2()
    test_04_sev5_rep1()
    test_05_sev5_rep3_ovd10()
    test_06_sev7_rep1()
    test_07_sev7_rep3()
    test_08_sev7_rep1_ovd10()
    test_09_sev8_rep1()
    test_10_boundary_34_low()
    test_11_boundary_35_medium()
    test_12_boundary_59_medium()
    test_13_boundary_60_high()
    test_14_boundary_79_high()
    test_15_boundary_80_critical()
    test_16_multiple_community_reports_uncapped()
    test_17_overdue_bonus_defaults_to_zero()
    test_18_negative_and_zero_severity_rejected()
    test_19_severity_above_10_rejected()
    test_20_report_count_below_1_rejected()
    test_21_negative_overdue_bonus_rejected()
    test_22_booleans_rejected()
    test_23_floats_and_strings_rejected()
    test_24_none_and_non_finite_rejected()

    print("=" * 70)
    print("ALL 24 M3-08 TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
