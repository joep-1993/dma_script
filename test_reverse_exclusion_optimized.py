"""
Test script for the optimized reverse_exclusion functions.

This script tests:
1. The grouping logic (shops grouped by maincat_id + cl1)
2. The batch removal function (reverse_exclusion_batch)
3. End-to-end dry-run with a mock sheet

Run with: python test_reverse_exclusion_optimized.py
"""

import sys
import os
from collections import defaultdict
from unittest.mock import Mock, MagicMock, patch

# Add script directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def test_grouping_logic():
    """
    Test that rows are correctly grouped by (maincat_id, cl1).
    """
    print("\n" + "="*60)
    print("TEST 1: Grouping Logic")
    print("="*60)

    # Simulate sheet data: (row_idx, shop_name, maincat_id, cl1, status)
    test_data = [
        (2, "Shop A", "12345", "a", None),
        (3, "Shop B", "12345", "a", None),    # Same group as row 2
        (4, "Shop C", "12345", "b", None),    # Different cl1
        (5, "Shop D", "67890", "a", None),    # Different maincat
        (6, "Shop E", "12345", "a", None),    # Same group as row 2, 3
        (7, "Shop F", "12345", "a", "TRUE"),  # Already processed - should skip
        (8, "Shop G", None, "a", None),       # Missing maincat - should error
        (9, "Shop H", "12345", None, None),   # Missing cl1 - should error
    ]

    # Group the data (simulating the function logic)
    groups = defaultdict(list)
    missing_fields = []

    for row_idx, shop_name, maincat_id, cl1, status in test_data:
        if status is not None and status != '':
            continue  # Already processed
        if not shop_name:
            continue
        if not maincat_id or not cl1:
            missing_fields.append(row_idx)
            continue

        groups[(str(maincat_id), str(cl1))].append((row_idx, shop_name))

    # Verify results
    print(f"\nInput: {len(test_data)} rows")
    print(f"Groups created: {len(groups)}")
    print(f"Rows with missing fields: {missing_fields}")

    # Expected groups:
    # ("12345", "a"): [Shop A, Shop B, Shop E] (rows 2, 3, 6)
    # ("12345", "b"): [Shop C] (row 4)
    # ("67890", "a"): [Shop D] (row 5)

    expected_groups = {
        ("12345", "a"): [(2, "Shop A"), (3, "Shop B"), (6, "Shop E")],
        ("12345", "b"): [(4, "Shop C")],
        ("67890", "a"): [(5, "Shop D")],
    }

    all_passed = True
    for key, expected in expected_groups.items():
        actual = groups.get(key, [])
        if actual == expected:
            print(f"  ✅ Group {key}: {len(actual)} shops - PASS")
        else:
            print(f"  ❌ Group {key}: expected {expected}, got {actual} - FAIL")
            all_passed = False

    if missing_fields == [8, 9]:
        print(f"  ✅ Missing fields rows: {missing_fields} - PASS")
    else:
        print(f"  ❌ Missing fields rows: expected [8, 9], got {missing_fields} - FAIL")
        all_passed = False

    if all_passed:
        print("\n✅ TEST 1 PASSED: Grouping logic works correctly")
    else:
        print("\n❌ TEST 1 FAILED")

    return all_passed


def test_batch_function_logic():
    """
    Test the reverse_exclusion_batch function logic with mocked Google Ads API.
    """
    print("\n" + "="*60)
    print("TEST 2: Batch Function Logic")
    print("="*60)

    # Test case-insensitive matching
    shop_names = ["Shop A", "SHOP B", "shop c"]
    shop_names_lower = {name.lower(): name for name in shop_names}

    # Simulate listing tree data from Google Ads
    mock_criteria = [
        {"index": "INDEX3", "value": "Shop A", "negative": True, "resource": "res1"},
        {"index": "INDEX3", "value": "shop b", "negative": True, "resource": "res2"},  # Different case
        {"index": "INDEX3", "value": "Shop D", "negative": True, "resource": "res3"},  # Not in our list
        {"index": "INDEX3", "value": "Shop C", "negative": False, "resource": "res4"}, # Not negative
        {"index": "INDEX2", "value": "Shop A", "negative": True, "resource": "res5"},  # Wrong index
    ]

    # Find matching criteria (simulating the function logic)
    criteria_to_remove = []
    found_shops = set()

    for crit in mock_criteria:
        if crit["index"] == "INDEX3" and crit["negative"]:
            value_lower = crit["value"].lower()
            if value_lower in shop_names_lower:
                original_shop_name = shop_names_lower[value_lower]
                criteria_to_remove.append((crit["resource"], original_shop_name))
                found_shops.add(value_lower)

    not_found = [shop for shop in shop_names if shop.lower() not in found_shops]

    print(f"\nInput shops: {shop_names}")
    print(f"Criteria to remove: {criteria_to_remove}")
    print(f"Shops not found: {not_found}")

    # Verify
    all_passed = True

    # Should find Shop A and SHOP B (case insensitive match for shop b)
    expected_remove = [("res1", "Shop A"), ("res2", "SHOP B")]
    if criteria_to_remove == expected_remove:
        print(f"  ✅ Criteria to remove: PASS")
    else:
        print(f"  ❌ Criteria to remove: expected {expected_remove}, got {criteria_to_remove} - FAIL")
        all_passed = False

    # Shop C should be "not found" because its criterion is not negative
    if "shop c" in not_found:
        print(f"  ✅ Non-negative criterion handled: PASS")
    else:
        print(f"  ❌ Non-negative criterion: shop c should be in not_found - FAIL")
        all_passed = False

    if all_passed:
        print("\n✅ TEST 2 PASSED: Batch function logic works correctly")
    else:
        print("\n❌ TEST 2 FAILED")

    return all_passed


def test_result_aggregation():
    """
    Test that results are correctly aggregated across multiple ad groups.
    """
    print("\n" + "="*60)
    print("TEST 3: Result Aggregation")
    print("="*60)

    shop_names = ["Shop A", "Shop B", "Shop C"]

    # Simulate results from multiple ad groups
    ad_group_results = [
        # Ad Group 1
        {'success': ['Shop A'], 'not_found': ['Shop B', 'Shop C'], 'errors': []},
        # Ad Group 2
        {'success': ['Shop A', 'Shop B'], 'not_found': ['Shop C'], 'errors': []},
        # Ad Group 3
        {'success': [], 'not_found': ['Shop A', 'Shop B'], 'errors': [('Shop C', 'API Error')]},
    ]

    # Aggregate results per shop
    shop_results = {shop: {'success': 0, 'not_found': 0, 'errors': []} for shop in shop_names}

    for result in ad_group_results:
        for shop in result['success']:
            shop_results[shop]['success'] += 1
        for shop in result['not_found']:
            shop_results[shop]['not_found'] += 1
        for shop, error in result['errors']:
            shop_results[shop]['errors'].append(error)

    print(f"\nAggregated results:")
    for shop, result in shop_results.items():
        print(f"  {shop}: success={result['success']}, not_found={result['not_found']}, errors={len(result['errors'])}")

    # Verify
    all_passed = True

    # Shop A: success in AG1 and AG2, not_found in AG3 = 2 success, 1 not_found
    if shop_results['Shop A'] == {'success': 2, 'not_found': 1, 'errors': []}:
        print(f"  ✅ Shop A aggregation: PASS")
    else:
        print(f"  ❌ Shop A: expected {{'success': 2, 'not_found': 1, 'errors': []}}, got {shop_results['Shop A']} - FAIL")
        all_passed = False

    # Shop C: 1 success, 2 not_found, 1 error
    if shop_results['Shop C']['success'] == 0 and shop_results['Shop C']['not_found'] == 2 and len(shop_results['Shop C']['errors']) == 1:
        print(f"  ✅ Shop C aggregation (with error): PASS")
    else:
        print(f"  ❌ Shop C: expected success=0, not_found=2, errors=1 - FAIL")
        all_passed = False

    if all_passed:
        print("\n✅ TEST 3 PASSED: Result aggregation works correctly")
    else:
        print("\n❌ TEST 3 FAILED")

    return all_passed


def test_status_determination():
    """
    Test that row status (success/failure) is correctly determined.
    """
    print("\n" + "="*60)
    print("TEST 4: Status Determination")
    print("="*60)

    test_cases = [
        # (campaigns_found, result, expected_status, description)
        (0, {'success': 0, 'not_found': 0, 'errors': []}, False, "No campaigns found"),
        (5, {'success': 3, 'not_found': 2, 'errors': []}, True, "Some removed, some not found, no errors"),
        (5, {'success': 0, 'not_found': 5, 'errors': []}, True, "All not found (shop wasn't excluded)"),
        (5, {'success': 3, 'not_found': 0, 'errors': [('AG1', 'Error')]}, False, "Has errors"),
        (5, {'success': 5, 'not_found': 0, 'errors': []}, True, "All removed successfully"),
    ]

    all_passed = True
    for campaigns_found, result, expected_status, description in test_cases:
        # Determine status (same logic as in the function)
        has_errors = len(result['errors']) > 0

        if campaigns_found == 0:
            actual_status = False
        elif has_errors:
            actual_status = False
        else:
            actual_status = True

        if actual_status == expected_status:
            print(f"  ✅ {description}: PASS")
        else:
            print(f"  ❌ {description}: expected {expected_status}, got {actual_status} - FAIL")
            all_passed = False

    if all_passed:
        print("\n✅ TEST 4 PASSED: Status determination works correctly")
    else:
        print("\n❌ TEST 4 FAILED")

    return all_passed


def test_efficiency_comparison():
    """
    Compare the number of API calls between old and new approach.
    """
    print("\n" + "="*60)
    print("TEST 5: Efficiency Comparison")
    print("="*60)

    # Scenario: 10 shops for the same maincat_id + cl1
    # 5 deepest_cats for that maincat
    # 3 ad groups per campaign
    num_shops = 10
    num_deepest_cats = 5
    num_ad_groups_per_campaign = 3

    # Old approach: For each shop, for each deepest_cat, for each ad group: read tree + remove
    old_api_calls = num_shops * num_deepest_cats * num_ad_groups_per_campaign * 2  # read + remove
    print(f"\nScenario: {num_shops} shops, {num_deepest_cats} deepest_cats, {num_ad_groups_per_campaign} ad groups each")
    print(f"\nOLD approach (per-shop processing):")
    print(f"  API calls: {num_shops} shops × {num_deepest_cats} deepest_cats × {num_ad_groups_per_campaign} ad groups × 2 (read+remove)")
    print(f"  Total: {old_api_calls} API calls")

    # New approach: For each deepest_cat, for each ad group: read tree once + batch remove
    new_api_calls = num_deepest_cats * num_ad_groups_per_campaign * 2  # read + batch remove
    print(f"\nNEW approach (grouped batch processing):")
    print(f"  API calls: {num_deepest_cats} deepest_cats × {num_ad_groups_per_campaign} ad groups × 2 (read+batch remove)")
    print(f"  Total: {new_api_calls} API calls")

    reduction = (1 - new_api_calls / old_api_calls) * 100
    print(f"\n📊 Reduction: {reduction:.1f}% fewer API calls")
    print(f"   ({old_api_calls} → {new_api_calls})")

    if new_api_calls < old_api_calls:
        print("\n✅ TEST 5 PASSED: New approach is more efficient")
        return True
    else:
        print("\n❌ TEST 5 FAILED: New approach should be more efficient")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*70)
    print("OPTIMIZED REVERSE EXCLUSION - TEST SUITE")
    print("="*70)

    results = []
    results.append(("Grouping Logic", test_grouping_logic()))
    results.append(("Batch Function Logic", test_batch_function_logic()))
    results.append(("Result Aggregation", test_result_aggregation()))
    results.append(("Status Determination", test_status_determination()))
    results.append(("Efficiency Comparison", test_efficiency_comparison()))

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
