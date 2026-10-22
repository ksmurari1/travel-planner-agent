"""CrewAI Travel Planner with Pydantic validation and CLI support.

CLI: python travel_planner.py
The Streamlit interface imports plan_trip() from this module.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load a local .env file when present; environment variables still take precedence.
load_dotenv()

# Avoid interactive trace-sharing prompts and disable optional tracing by default.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", os.getenv("MODEL", "gpt-4o-mini"))


class CityInput(BaseModel):
    """Validated user-supplied city name."""

    city: str = Field(min_length=1, max_length=100, description="City to plan a visit to")

    @field_validator("city")
    @classmethod
    def clean_city(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("City name cannot be empty.")
        return cleaned


class PlaceRecommendation(BaseModel):
    """One recommended destination."""

    name: str = Field(min_length=1, description="Name of the place")
    description: str = Field(min_length=1, description="Short description of the place")
    # Defaults keep compatibility with the original seven validation tests.
    why_visit: str = Field(
        default="A worthwhile stop for visitors.",
        min_length=1,
        description="Why a traveller should visit this place",
    )
    best_time: str = Field(
        default="Check local opening hours and seasonal conditions before visiting.",
        min_length=1,
        description="Best time to visit, with a brief reason",
    )

    @field_validator("name", "description", "why_visit", "best_time")
    @classmethod
    def clean_text_fields(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be empty or contain only spaces.")
        return cleaned


class TravelRecommendations(BaseModel):
    """Exactly three recommendations; retained for existing tests/API compatibility."""

    recommendations: list[PlaceRecommendation] = Field(
        min_length=3,
        max_length=3,
        description="Exactly three distinct places to visit",
    )

    @field_validator("recommendations")
    @classmethod
    def ensure_distinct_places(cls, places: list[PlaceRecommendation]) -> list[PlaceRecommendation]:
        names = [place.name.casefold() for place in places]
        if len(set(names)) != len(names):
            raise ValueError("Recommendations must contain three distinct places.")
        return places


class TravelPlan(BaseModel):
    """Complete plan used by the UI and JSON download."""

    city: str = Field(min_length=1)
    places: list[PlaceRecommendation] = Field(min_length=3, max_length=3)

    @field_validator("city")
    @classmethod
    def clean_city(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("City name cannot be empty.")
        return cleaned

    @field_validator("places")
    @classmethod
    def ensure_distinct_places(cls, places: list[PlaceRecommendation]) -> list[PlaceRecommendation]:
        names = [place.name.casefold() for place in places]
        if len(set(names)) != len(names):
            raise ValueError("Recommendations must contain three distinct places.")
        return places


# Compatibility alias for code written against the Emergent ZIP.
Place = PlaceRecommendation


def _get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "OPENAI_API_KEY is missing. Add it to the project's .env file, "
            "then restart the application. See .env.example."
        )
    return key


def plan_trip(city: str, **callbacks: Any) -> TravelPlan:
    """Run the CrewAI agent and return a Pydantic-validated plan."""
    validated_city = CityInput(city=city).city
    api_key = _get_api_key()

    # Import CrewAI only when a real plan is requested. This keeps model tests
    # independent from network/API execution and produces a clear setup error.
    try:
        from crewai import Agent, Crew, LLM, Process, Task
    except ImportError as exc:  # pragma: no cover - installation-specific
        raise RuntimeError(
            "CrewAI is not installed in this Python environment. Install requirements.txt."
        ) from exc

    model_name = os.getenv("OPENAI_MODEL_NAME", os.getenv("MODEL", DEFAULT_MODEL)).strip()
    llm = LLM(model=model_name, api_key=api_key, temperature=0.3)

    agent = Agent(
        role="Senior Travel Planner",
        goal=(
            "Recommend exactly three distinct, worthwhile places in the traveller's city, "
            "with concise descriptions, reasons to visit, and practical timing advice."
        ),
        backstory=(
            "You are an experienced travel planner who balances iconic sights, cultural "
            "places, and local favourites. Be useful and cautious: do not invent opening "
            "hours or claim that current conditions have been verified."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description=(
            f"Prepare a travel recommendation for {validated_city}. Recommend exactly "
            "three distinct real places located in that city (not nearby cities). For each "
            "place, provide its name, a concise description, why it is worth visiting, "
            "and the best time or season to visit. If a detail is uncertain, phrase it "
            "cautiously rather than inventing specifics. The city must be exactly the "
            f"traveller's requested city: {validated_city}."
        ),
        expected_output=(
            "A structured plan containing exactly three distinct places. Every place must "
            "include non-empty name, description, why_visit, and best_time fields."
        ),
        agent=agent,
        output_pydantic=TravelPlan,
    )

    crew_options: dict[str, Any] = {
        "agents": [agent],
        "tasks": [task],
        "process": Process.sequential,
        "verbose": False,
    }
    # Pass only callbacks explicitly supported by the installed CrewAI version.
    for callback_name in ("step_callback", "task_callback"):
        if callback_name in callbacks and callbacks[callback_name] is not None:
            crew_options[callback_name] = callbacks[callback_name]

    try:
        result = Crew(**crew_options).kickoff()
    except Exception as exc:
        # Keep the underlying exception chained for terminal debugging, but let
        # the UI show a safe message without secrets or a giant traceback.
        message = str(exc).lower()
        if any(term in message for term in ("401", "unauthorized", "invalid api key", "authentication")):
            raise RuntimeError("OpenAI authentication failed. Check OPENAI_API_KEY in .env.") from exc
        if any(term in message for term in ("429", "rate limit", "quota", "insufficient_quota")):
            raise RuntimeError("The OpenAI API rate limit or quota was reached. Check your API account and retry later.") from exc
        if any(term in message for term in ("connection", "timeout", "network", "name resolution")):
            raise RuntimeError("Could not connect to the model service. Check your internet connection and retry.") from exc
        raise RuntimeError("CrewAI could not complete the travel plan. Check the terminal for diagnostic details.") from exc

    structured = getattr(result, "pydantic", None)
    if structured is None:
        raise RuntimeError("The agent did not return structured output. Please retry the request.")

    # Validate once more at our application boundary, then normalize city to the input.
    if isinstance(structured, TravelPlan):
        raw_plan = structured.model_dump()
    elif isinstance(structured, BaseModel):
        raw_plan = structured.model_dump()
    elif isinstance(structured, dict):
        raw_plan = structured
    else:
        raise RuntimeError("The agent returned an unexpected output format. Please retry.")

    raw_plan["city"] = validated_city
    try:
        return TravelPlan.model_validate(raw_plan)
    except Exception as exc:
        raise RuntimeError("The agent's recommendations did not pass output validation. Please retry.") from exc


def generate_recommendations(city: str) -> TravelRecommendations:
    """Compatibility helper used by the earlier Streamlit app and tests."""
    plan = plan_trip(city)
    return TravelRecommendations(recommendations=plan.places)


def format_plan(plan: TravelPlan) -> str:
    lines = [f"\nTOP 3 PLACES TO VISIT IN {plan.city.upper()}", "=" * 44]
    for number, place in enumerate(plan.places, start=1):
        lines.extend([
            f"\n{number}. {place.name}",
            f"   Description : {place.description}",
            f"   Why visit   : {place.why_visit}",
            f"   Best time   : {place.best_time}",
        ])
    return "\n".join(lines)


def main() -> int:
    """Command-line entry point retained for the assignment."""
    try:
        city = input("Which city would you like to explore? ")
        plan = plan_trip(city)
        print(format_plan(plan))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"\nTravel Planner: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nTravel planning cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
