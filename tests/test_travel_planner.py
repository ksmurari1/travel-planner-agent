import pytest
from pydantic import ValidationError

from travel_planner import CityInput, PlaceRecommendation, TravelPlan, TravelRecommendations


def sample_places():
    return [
        {"name": "Hawa Mahal", "description": "Historic palace."},
        {"name": "Amber Fort", "description": "Historic fort."},
        {"name": "City Palace", "description": "Royal residence."},
    ]


def test_city_name_is_trimmed():
    assert CityInput(city=" Jaipur ").city == "Jaipur"


def test_blank_city_is_rejected():
    with pytest.raises(ValidationError):
        CityInput(city="   ")


def test_three_recommendations_are_accepted():
    result = TravelRecommendations.model_validate({"recommendations": sample_places()})
    assert len(result.recommendations) == 3


def test_two_recommendations_are_rejected():
    with pytest.raises(ValidationError):
        TravelRecommendations.model_validate({"recommendations": sample_places()[:2]})


def test_four_recommendations_are_rejected():
    places = sample_places() + [{"name": "Jantar Mantar", "description": "Historic observatory."}]
    with pytest.raises(ValidationError):
        TravelRecommendations.model_validate({"recommendations": places})


def test_empty_place_name_is_rejected():
    with pytest.raises(ValidationError):
        PlaceRecommendation(name="", description="A description.")


def test_empty_description_is_rejected():
    with pytest.raises(ValidationError):
        PlaceRecommendation(name="Hawa Mahal", description="")


def test_duplicate_places_are_rejected():
    places = sample_places()
    places[1] = {"name": "hawa mahal", "description": "Duplicate."}
    with pytest.raises(ValidationError):
        TravelRecommendations.model_validate({"recommendations": places})


def test_travel_plan_has_exactly_three_places():
    plan = TravelPlan(city="Chennai", places=sample_places())
    assert plan.city == "Chennai"
    assert len(plan.places) == 3


def test_travel_plan_rejects_blank_city():
    with pytest.raises(ValidationError):
        TravelPlan(city="  ", places=sample_places())
