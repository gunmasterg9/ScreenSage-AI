"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError
from backend.app.schemas import BoundingBox, UIElement, ScreenExplanation


def test_bounding_box_valid():
    box = BoundingBox(ymin=10.0, xmin=15.0, ymax=40.0, xmax=60.0, label="Search Bar")
    assert box.ymin == 10.0
    assert box.xmax == 60.0
    assert box.label == "Search Bar"


def test_bounding_box_order_correction():
    # If inverted (ymin > ymax), validator handles order
    box = BoundingBox(ymin=50.0, xmin=20.0, ymax=10.0, xmax=80.0)
    assert box.ymax >= box.ymin


def test_bounding_box_out_of_bounds():
    with pytest.raises(ValidationError):
        BoundingBox(ymin=-5.0, xmin=10.0, ymax=50.0, xmax=60.0)

    with pytest.raises(ValidationError):
        BoundingBox(ymin=0.0, xmin=0.0, ymax=150.0, xmax=50.0)


def test_ui_element_schema():
    elem = UIElement(
        id="elem_1",
        element_name="Submit Button",
        element_type="button",
        likely_purpose="Submits the active form",
        visible_text="Send Query",
        bounding_box=BoundingBox(ymin=80.0, xmin=40.0, ymax=90.0, xmax=60.0),
    )
    assert elem.element_type == "button"
    assert elem.bounding_box is not None


def test_screen_explanation_schema():
    explanation = ScreenExplanation(
        screen_summary="A browser settings page showing cookie preferences.",
        visible_ui_elements=[
            UIElement(
                element_name="Allow All Cookies Toggle",
                element_type="toggle",
                likely_purpose="Permits first and third party cookies",
                visible_text="Allow cookies",
            )
        ],
        likely_purpose_of_important_elements=["Toggles modify privacy state"],
        relevant_visible_text=["Privacy and Security", "Cookies"],
        answer_to_user_question="The cookie toggle is in the center of the screen.",
        suggested_next_steps=["Click the toggle to change state"],
        uncertainties_and_missing_visual_information=["Advanced security sub-tab is scrolled off screen"],
        coordinate_support_verified=False,
    )
    assert "cookie" in explanation.screen_summary.lower()
    assert len(explanation.visible_ui_elements) == 1
    assert explanation.coordinate_support_verified is False
