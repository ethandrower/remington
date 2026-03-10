"""
Unit Tests for Standup Parser

TDD-style tests using real Slack standup messages as fixtures.
Tests validate that the LLM-based parser correctly extracts:
- Standup dates
- Completed work (ticket_id, hours, description)
- Planned work (ticket_ids)
- Blockers
- Additional notes
"""
import json
import pytest
from pathlib import Path
from typing import Dict, List


# Import will work once we implement the parser
try:
    from src.processors.standup_parser import StandupParser, StandupParsed
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False


# Load test fixtures
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "standup_test_cases.json"


def load_test_fixtures() -> List[Dict]:
    """Load test cases from JSON fixture file"""
    with open(FIXTURES_PATH, 'r') as f:
        data = json.load(f)
    return data['test_cases']


@pytest.fixture
def parser():
    """Create parser instance for testing"""
    if not PARSER_AVAILABLE:
        pytest.skip("StandupParser not yet implemented")
    return StandupParser()


@pytest.fixture
def test_cases():
    """Load all test cases from fixtures"""
    return load_test_fixtures()


class TestStandupParserStructure:
    """Test that parser returns correct data structure"""

    def test_parser_returns_standup_parsed_object(self, parser):
        """Parser should return StandupParsed instance"""
        result = parser.parse("ECD-123: 2H\nFixed bugs")
        assert isinstance(result, StandupParsed)

    def test_parsed_object_has_required_fields(self, parser):
        """StandupParsed should have all required fields"""
        result = parser.parse("ECD-123: 2H")
        assert hasattr(result, 'standup_date')
        assert hasattr(result, 'completed_work')
        assert hasattr(result, 'planned_work')
        assert hasattr(result, 'blockers')
        assert hasattr(result, 'notes')

    def test_completed_work_items_have_required_fields(self, parser):
        """Each completed work item should have ticket_id, hours, description"""
        result = parser.parse("ECD-123: 2H\nFixed authentication bug")
        if result.completed_work:
            work_item = result.completed_work[0]
            assert hasattr(work_item, 'ticket_id')
            assert hasattr(work_item, 'hours')
            assert hasattr(work_item, 'description')


class TestStandupParserBasicCases:
    """Test basic parsing scenarios"""

    def test_empty_message_returns_empty_result(self, parser):
        """Empty message should return empty StandupParsed"""
        result = parser.parse("")
        assert result.completed_work == []
        assert result.planned_work == []

    def test_single_ticket_with_hours(self, parser):
        """Should parse single ticket with hours"""
        result = parser.parse("ECD-123: 2H\nFixed bug")
        assert len(result.completed_work) >= 1
        # Find the ECD-123 entry
        ecd_123 = next((w for w in result.completed_work if w.ticket_id == "ECD-123"), None)
        assert ecd_123 is not None
        assert ecd_123.hours == 2.0

    def test_multiple_tickets(self, parser):
        """Should parse multiple tickets"""
        message = """
        ECD-123: 2H
        Fixed auth bug

        ECD-456: 3H
        Refactored API
        """
        result = parser.parse(message)
        assert len(result.completed_work) >= 2
        ticket_ids = [w.ticket_id for w in result.completed_work]
        assert "ECD-123" in ticket_ids
        assert "ECD-456" in ticket_ids

    def test_fractional_hours(self, parser):
        """Should parse fractional hours correctly"""
        result = parser.parse("ECD-123: 0.5H\nQuick fix")
        ecd_123 = next((w for w in result.completed_work if w.ticket_id == "ECD-123"), None)
        assert ecd_123 is not None
        assert ecd_123.hours == 0.5

    def test_planned_work_without_hours(self, parser):
        """Tickets without hours should go to planned_work"""
        message = """
        Worked on:
        ECD-123: 2H

        Plan to work:
        ECD-456
        """
        result = parser.parse(message)
        assert "ECD-456" in result.planned_work


class TestStandupParserRealMessages:
    """Test parser against real Slack standup messages"""

    @pytest.mark.parametrize("test_case_id", [
        "standup_1", "standup_2", "standup_3", "standup_4", "standup_5",
        "standup_6", "standup_7", "standup_8", "standup_9", "standup_10"
    ])
    def test_real_standup_message(self, parser, test_cases, test_case_id):
        """Test parser against real standup message"""
        # Find the test case
        test_case = next((tc for tc in test_cases if tc['id'] == test_case_id), None)
        assert test_case is not None, f"Test case {test_case_id} not found"

        # Parse the message
        input_data = test_case['input']
        expected = test_case['expected_output']

        result = parser.parse(input_data['message_text'])

        # Validate standup_date
        if expected.get('standup_date'):
            assert result.standup_date == expected['standup_date'], \
                f"Date mismatch in {test_case_id}"

        # Validate completed_work
        expected_work = expected.get('completed_work', [])
        if expected_work:
            assert len(result.completed_work) == len(expected_work), \
                f"Wrong number of work items in {test_case_id}. Expected {len(expected_work)}, got {len(result.completed_work)}"

            for exp_item in expected_work:
                # Find matching ticket in results
                actual_item = next(
                    (w for w in result.completed_work if w.ticket_id == exp_item['ticket_id']),
                    None
                )
                assert actual_item is not None, \
                    f"Missing ticket {exp_item['ticket_id']} in {test_case_id}"
                assert actual_item.hours == exp_item['hours'], \
                    f"Hours mismatch for {exp_item['ticket_id']} in {test_case_id}"
                # Description matching can be fuzzy - just check it's not empty
                assert actual_item.description, \
                    f"Empty description for {exp_item['ticket_id']} in {test_case_id}"

        # Validate planned_work
        expected_planned = expected.get('planned_work', [])
        if expected_planned:
            for ticket in expected_planned:
                assert ticket in result.planned_work, \
                    f"Missing planned ticket {ticket} in {test_case_id}"

        # Validate blockers
        if expected.get('blockers'):
            assert result.blockers is not None, \
                f"Expected blockers in {test_case_id}"
            # Check if blocker content is present (fuzzy match)
            assert len(result.blockers) > 0, \
                f"Blocker content empty in {test_case_id}"


class TestStandupParserEdgeCases:
    """Test edge cases and error handling"""

    def test_message_with_no_tickets(self, parser):
        """Message with no ticket IDs should return empty"""
        result = parser.parse("Worked on bug fixes today")
        # Might have notes, but no work items
        assert result.completed_work == []

    def test_message_with_urls(self, parser):
        """Should handle messages with URLs"""
        message = "ECD-123: 2H\nPR: https://bitbucket.org/company/repo/pull-requests/123"
        result = parser.parse(message)
        assert len(result.completed_work) >= 1

    def test_message_with_special_characters(self, parser):
        """Should handle special characters (bullets, unicode, etc)"""
        message = "• ECD-123: 2H\n    ◦ Fixed bug with special chars: &amp; < >"
        result = parser.parse(message)
        assert len(result.completed_work) >= 1

    def test_multiple_tickets_on_one_line(self, parser):
        """Should handle multiple ticket references in one work item"""
        message = "ECD-123, ECD-456, ECD-789: 5H\nRefactored shared components"
        result = parser.parse(message)
        # LLM should intelligently split or group these
        assert len(result.completed_work) >= 1

    def test_time_in_different_formats(self, parser):
        """Should handle various time formats"""
        messages = [
            "ECD-123: 2H",
            "ECD-123: 2h",
            "ECD-123 ~ 2H",
            "ECD-123 2.5 hours",
        ]
        for msg in messages:
            result = parser.parse(msg)
            # Should extract time in some form
            if result.completed_work:
                assert result.completed_work[0].hours > 0


class TestStandupParserOutput:
    """Test output format and serialization"""

    def test_parse_to_dict(self, parser):
        """Should convert to dictionary"""
        result_dict = parser.parse_to_dict("ECD-123: 2H\nFixed bug")
        assert isinstance(result_dict, dict)
        assert 'completed_work' in result_dict
        assert 'planned_work' in result_dict

    def test_dict_is_json_serializable(self, parser):
        """Output dict should be JSON serializable"""
        result_dict = parser.parse_to_dict("ECD-123: 2H")
        try:
            json.dumps(result_dict)
        except Exception as e:
            pytest.fail(f"Result dict is not JSON serializable: {e}")


# Mark all tests to skip if parser not implemented yet
pytestmark = pytest.mark.skipif(
    not PARSER_AVAILABLE,
    reason="StandupParser not yet implemented"
)