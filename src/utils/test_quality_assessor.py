#!/usr/bin/env python3
"""
Test Quality Assessor - Evaluate test case quality based on QA SOP

Evaluates test quality for Jira tickets and PRs according to ENG-02 QA Guidelines.

Reference: .claude/procedures/test-quality-sop.md
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class TestQualityResult:
    """Result of test quality assessment"""
    score: float  # 0-10
    grade: str  # PASS, NEEDS_WORK, FAIL
    findings: Dict[str, List[str]] = field(default_factory=dict)
    missing_items: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    recommendation: str = ""  # APPROVE, NEEDS_WORK, BLOCKED
    details: Dict = field(default_factory=dict)


class TestQualityAssessor:
    """
    Assess test quality based on QA SOP criteria

    Scoring Rubric (from .claude/procedures/test-quality-sop.md):
    - 8-10: PASS (fully compliant with SOP)
    - 5-7:  NEEDS WORK (partial compliance)
    - 0-4:  FAIL (non-compliant)
    """

    # SOP Section 3.4: Mandatory QA test case comment format indicators
    QA_COMMENT_INDICATORS = [
        r"QA Test Cases",
        r"Test Cases.*\[.*\]",  # "Test Cases – [Name, Date]"
        r"Environment:.*QA",
        r"Browser\(s\):",
        r"Steps:",
        r"Expected:",
        r"Result:.*PASS|FAIL"
    ]

    # SOP Section 4.3: Standard test case template elements
    TEST_CASE_ELEMENTS = {
        "steps": r"Steps?:\s*\n\s*\d+\.",  # Numbered steps
        "expected": r"Expected( Result)?:",
        "actual": r"(Actual )?Result:",
        "environment": r"Environment:",
        "preconditions": r"Preconditions?:",
    }

    # Common test case coverage patterns
    COVERAGE_PATTERNS = {
        "happy_path": r"happy path|positive case|valid",
        "negative": r"negative|invalid|missing|error|fails?",
        "edge_case": r"edge case|boundary|limit|minimum|maximum",
        "regression": r"regression|existing.*unaffected|backward compat",
        "cross_browser": r"chrome|safari|firefox|edge|browser",
        "permissions": r"permission|role|access|unauthorized|auth",
    }

    def assess_pr_test_quality(
        self,
        pr_data: Dict,
        ticket_data: Dict,
        pr_comments: List[Dict],
        qase_cases: Optional[List[Dict]] = None
    ) -> TestQualityResult:
        """
        Assess test quality for a PR based on SOP criteria

        Args:
            pr_data: Bitbucket PR data (title, description, state)
            ticket_data: Jira ticket data (summary, ACs, status)
            pr_comments: List of PR comments (for QA test case documentation)
            qase_cases: Optional list of Qase test cases found for this ticket

        Returns:
            TestQualityResult with score, grade, and detailed findings
        """
        score = 0.0
        max_score = 10.0
        findings = {
            "compliant": [],
            "missing": [],
            "warnings": []
        }
        strengths = []
        missing_items = []

        # 1. Check for QA test case comment on PR (MANDATORY - Section 3.4)
        qa_comment = self._find_qa_test_case_comment(pr_comments)

        if qa_comment:
            score += 3.0  # 30% weight - mandatory requirement
            findings["compliant"].append("✅ QA test case comment found on PR (SOP 3.4)")
            strengths.append("Proper test case documentation in PR")

            # Analyze comment quality
            comment_score, comment_findings = self._assess_qa_comment_quality(qa_comment)
            score += comment_score
            findings["compliant"].extend(comment_findings["good"])
            findings["warnings"].extend(comment_findings["warnings"])
            missing_items.extend(comment_findings["missing"])
        else:
            findings["missing"].append("❌ No QA test case comment on PR (MANDATORY - SOP 3.4)")
            missing_items.append("QA test case documentation comment")

        # 2. Check acceptance criteria coverage (Section 4.2)
        acs = ticket_data.get("acceptance_criteria", [])
        if qa_comment:
            coverage_score, coverage_findings = self._assess_ac_coverage(qa_comment, acs)
            score += coverage_score
            findings["compliant"].extend(coverage_findings["covered"])
            findings["missing"].extend(coverage_findings["not_covered"])
        else:
            findings["missing"].append("Cannot assess AC coverage without QA comment")

        # 3. Check for negative/edge case testing (Section 4.2)
        if qa_comment:
            negative_found = self._check_pattern(qa_comment, self.COVERAGE_PATTERNS["negative"])
            edge_found = self._check_pattern(qa_comment, self.COVERAGE_PATTERNS["edge_case"])

            if negative_found:
                score += 1.0
                findings["compliant"].append("✅ Negative test cases documented")
                strengths.append("Good negative case coverage")
            else:
                findings["missing"].append("⚠️ No negative test cases found")
                missing_items.append("Negative test cases")

            if edge_found:
                score += 0.5
                findings["compliant"].append("✅ Edge cases tested")
            else:
                findings["warnings"].append("⚠️ Edge cases not explicitly mentioned")

        # 4. Check for regression testing (Section 3.3)
        if qa_comment:
            regression_found = self._check_pattern(qa_comment, self.COVERAGE_PATTERNS["regression"])
            if regression_found:
                score += 1.0
                findings["compliant"].append("✅ Regression testing performed")
                strengths.append("Regression checks documented")
            else:
                findings["warnings"].append("⚠️ No explicit regression testing mentioned")

        # 5. Check for cross-browser testing (Section 3.3)
        if qa_comment:
            browser_found = self._check_pattern(qa_comment, self.COVERAGE_PATTERNS["cross_browser"])
            if browser_found:
                score += 1.0
                findings["compliant"].append("✅ Cross-browser testing documented")
            else:
                findings["missing"].append("❌ No cross-browser testing evidence (SOP 3.3 - Chrome + Safari minimum)")
                missing_items.append("Cross-browser testing (Chrome + Safari)")

        # 6. Check Qase test case links (if provided)
        if qase_cases:
            score += 0.5
            findings["compliant"].append(f"✅ Found {len(qase_cases)} Qase test case(s)")
            strengths.append(f"Qase integration: {len(qase_cases)} cases linked")

        # Cap score at max
        score = min(score, max_score)

        # Determine grade and recommendation
        grade, recommendation = self._determine_grade_and_recommendation(
            score,
            missing_items,
            ticket_data.get("status")
        )

        return TestQualityResult(
            score=round(score, 2),
            grade=grade,
            findings=findings,
            missing_items=missing_items,
            strengths=strengths,
            recommendation=recommendation,
            details={
                "qa_comment_found": qa_comment is not None,
                "qase_cases_count": len(qase_cases) if qase_cases else 0,
                "acceptance_criteria_count": len(acs),
                "pr_title": pr_data.get("title"),
                "ticket_key": ticket_data.get("key"),
                "ticket_status": ticket_data.get("status")
            }
        )

    def _find_qa_test_case_comment(self, pr_comments: List[Dict]) -> Optional[str]:
        """Find QA test case comment in PR comments (Section 3.4)"""
        for comment in pr_comments:
            content = comment.get("content", "")
            # Check for QA comment indicators
            for pattern in self.QA_COMMENT_INDICATORS:
                if re.search(pattern, content, re.IGNORECASE):
                    return content
        return None

    def _assess_qa_comment_quality(self, comment: str) -> Tuple[float, Dict[str, List[str]]]:
        """
        Assess quality of QA comment based on template compliance (Section 4.3)

        Returns: (score_out_of_3, findings_dict)
        """
        score = 0.0
        findings = {"good": [], "warnings": [], "missing": []}

        # Check for template elements
        elements_found = 0
        for element_name, pattern in self.TEST_CASE_ELEMENTS.items():
            if re.search(pattern, comment, re.IGNORECASE):
                elements_found += 1

        # Score based on template compliance
        if elements_found >= 4:
            score += 1.5
            findings["good"].append("✅ Test case format follows SOP template (4+ elements)")
        elif elements_found >= 2:
            score += 0.75
            findings["warnings"].append("⚠️ Partial template compliance (only some elements present)")
        else:
            findings["missing"].append("Test case template elements (steps, expected, environment)")

        # Check for test results (PASS/FAIL)
        if re.search(r"Result:.*PASS", comment, re.IGNORECASE):
            score += 0.75
            findings["good"].append("✅ Test results documented (PASS)")
        elif re.search(r"Result:.*FAIL", comment, re.IGNORECASE):
            score += 0.5
            findings["warnings"].append("⚠️ Test failures documented (needs resolution)")
        else:
            findings["missing"].append("Test execution results (PASS/FAIL)")

        # Check for environment/browser info
        if re.search(r"Environment:.*\w+", comment, re.IGNORECASE):
            score += 0.75
            findings["good"].append("✅ Test environment documented")
        else:
            findings["missing"].append("Test environment details")

        return (score, findings)

    def _assess_ac_coverage(self, qa_comment: str, acceptance_criteria: List[str]) -> Tuple[float, Dict[str, List[str]]]:
        """
        Check if acceptance criteria are covered in testing (Section 4.2)

        Returns: (score_out_of_2, coverage_findings)
        """
        if not acceptance_criteria:
            # No ACs defined - can't assess coverage
            return (1.0, {"covered": ["ℹ️ No ACs defined in ticket"], "not_covered": []})

        score = 0.0
        findings = {"covered": [], "not_covered": []}

        covered_count = 0
        for ac in acceptance_criteria:
            # Simple keyword matching (could be improved with NLP)
            ac_keywords = re.findall(r'\b\w{4,}\b', ac.lower())  # Extract 4+ char words
            matches = sum(1 for kw in ac_keywords if kw in qa_comment.lower())

            if matches >= len(ac_keywords) * 0.5:  # 50% keyword match threshold
                covered_count += 1

        coverage_ratio = covered_count / len(acceptance_criteria)

        if coverage_ratio >= 0.8:
            score = 2.0
            findings["covered"].append(f"✅ Excellent AC coverage ({covered_count}/{len(acceptance_criteria)} ACs tested)")
        elif coverage_ratio >= 0.5:
            score = 1.0
            findings["covered"].append(f"⚠️ Partial AC coverage ({covered_count}/{len(acceptance_criteria)} ACs)")
            findings["not_covered"].append(f"Some ACs may not be fully tested ({len(acceptance_criteria) - covered_count} unclear)")
        else:
            score = 0.5
            findings["not_covered"].append(f"❌ Poor AC coverage ({covered_count}/{len(acceptance_criteria)} ACs)")

        return (score, findings)

    def _check_pattern(self, text: str, pattern: str) -> bool:
        """Check if pattern exists in text"""
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _determine_grade_and_recommendation(
        self,
        score: float,
        missing_items: List[str],
        ticket_status: Optional[str]
    ) -> Tuple[str, str]:
        """
        Determine grade and recommendation based on score and context

        Returns: (grade, recommendation)
        """
        # Grade based on score
        if score >= 8.0:
            grade = "PASS"
        elif score >= 5.0:
            grade = "NEEDS_WORK"
        else:
            grade = "FAIL"

        # Recommendation based on grade and critical missing items
        critical_missing = any("MANDATORY" in item or "❌" in item for item in missing_items)

        if grade == "PASS":
            recommendation = "APPROVE"
        elif grade == "NEEDS_WORK":
            if critical_missing:
                recommendation = "BLOCKED"
            else:
                recommendation = "NEEDS_WORK"
        else:  # FAIL
            recommendation = "BLOCKED"

        # Special case: If ticket is in Pending Approval but failing, definitely block
        if ticket_status == "Pending Approval" and grade == "FAIL":
            recommendation = "BLOCKED"

        return (grade, recommendation)


def format_assessment_report(result: TestQualityResult) -> str:
    """Format test quality assessment as a readable report"""
    report = f"""
═══════════════════════════════════════════════════════════
TEST QUALITY ASSESSMENT REPORT
═══════════════════════════════════════════════════════════

Ticket: {result.details.get('ticket_key')}
PR: {result.details.get('pr_title', 'N/A')[:60]}...
Status: {result.details.get('ticket_status')}

OVERALL SCORE: {result.score}/10.0
GRADE: {result.grade}
RECOMMENDATION: {result.recommendation}

───────────────────────────────────────────────────────────
✅ COMPLIANT ITEMS:
"""
    for item in result.findings.get("compliant", []):
        report += f"  {item}\n"

    if result.strengths:
        report += "\n💪 STRENGTHS:\n"
        for strength in result.strengths:
            report += f"  • {strength}\n"

    if result.findings.get("warnings"):
        report += "\n⚠️  WARNINGS:\n"
        for warning in result.findings["warnings"]:
            report += f"  {warning}\n"

    if result.missing_items:
        report += "\n❌ MISSING / NON-COMPLIANT:\n"
        for missing in result.missing_items:
            report += f"  • {missing}\n"

    report += f"""
───────────────────────────────────────────────────────────
📋 SUMMARY:
  • QA Comment Found: {'Yes' if result.details.get('qa_comment_found') else 'No'}
  • Qase Cases Linked: {result.details.get('qase_cases_count', 0)}
  • Acceptance Criteria: {result.details.get('acceptance_criteria_count', 0)}

═══════════════════════════════════════════════════════════
"""
    return report
