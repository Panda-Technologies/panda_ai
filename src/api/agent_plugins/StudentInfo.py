from enum import Enum
from typing import Annotated, List, Optional

from semantic_kernel.functions import kernel_function

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext, AcademicTerm
from src.api.api_fetch.models import UserModel
from src.api.api_fetch.services import UserService, PandaService
from src.api.main import SESSION_COOKIE

class Season(str, Enum):
    FALL = "Fall"
    SPRING = "Spring"
    SUMMER = "Summer"

class TimePreference(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NO_PREFERENCE = "no preference"


class StudentInfoPlugin:
    def __init__(self, state: ConversationContext):
        self.state = state
        self.user_service = UserService(PandaService(SESSION_COOKIE))

    @kernel_function(
        name="major_info",
        description="Update major, degree type, concentration."
    )
    def update_major_info(
            self,
            major: Annotated[str, "Major name"] = None,
            degree_type: Annotated[str, "BA, BS, etc."] = None,
            concentration: Annotated[str, "Specialization"] = None,
    ) -> str:
        """Update major information."""
        updates = []
        artifact = self.state.artifact

        if degree_type and artifact.degree_type != degree_type:
            artifact.degree_type = degree_type
            updates.append(f"Degree type: {degree_type}")

        if major and artifact.major != major:
            artifact.major = major
            updates.append(f"Major: {major}")

        if concentration and artifact.concentration != concentration:
            artifact.concentration = concentration
            updates.append(f"Concentration: {concentration}")

        if updates:
            print("Major info updated")
            return f"Updated: {', '.join(updates)}"
        return "No updates made."

    @kernel_function(
        name="minor_info"
    )
    def update_minor_info(
            self,
            minor: Annotated[str, "Minor(s)"] = None,
    ) -> str:
        """Update minor information."""

        def safe_list(value):
            if not value:
                return None
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    import json
                    return json.loads(value)
                except:
                    return [item.strip() for item in value.split(",")]
            return [str(value)]

        updates = []
        artifact = self.state.artifact
        minor = safe_list(minor)

        if minor:
            new_minors = [m for m in minor if m not in artifact.minor]
            if new_minors:
                artifact.minor.extend(new_minors)
                updates.append(f"Minor(s): {', '.join(new_minors)}")

        if updates:
            print("Minor info updated")
            return f"Updated: {', '.join(updates)}"
        return "No updates made."

    @kernel_function(
        name="term_info"
    )
    def update_term_info(
            self,
            start_season: Annotated[Season, "Starting term"] = None,
            start_year: Annotated[int, "Start year"] = None,
            current_season: Annotated[Season, "Current term"] = None,
            current_year: Annotated[int, "Current year"] = None,
    ) -> str:
        """Update term information."""
        updates = []
        artifact = self.state.artifact

        if start_season and start_year:
            if not artifact.start_term:
                artifact.start_term = AcademicTerm(term=start_season, year=start_year)
                updates.append(f"Start term: {start_season} {start_year}")
            elif artifact.start_term.term != start_season or artifact.start_term.year != start_year:
                artifact.start_term.term = start_season
                artifact.start_term.year = start_year
                updates.append(f"Start term: {start_season} {start_year}")

        if current_season and current_year:
            if not artifact.current_term:
                artifact.current_term = AcademicTerm(term=current_season, year=current_year)
                updates.append(f"Current term: {current_season} {current_year}")
            elif artifact.current_term.term != current_season or artifact.current_term.year != current_year:
                artifact.current_term.term = current_season
                artifact.current_term.year = current_year
                updates.append(f"Current term: {current_season} {current_year}")

        if updates:
            print("Term info updated")
            return f"Updated: {', '.join(updates)}"
        return "No updates made."

    @kernel_function(
        name="course_load"
    )
    def update_course_load(
            self,
            preferred: Annotated[int, "Preferred courses per semester"] = None,
            minimum: Annotated[int, "Minimum courses per semester"] = None,
            maximum: Annotated[int, "Maximum courses per semester"] = None,
    ) -> str:
        """Update course load preferences."""
        updates = []
        artifact = self.state.artifact

        if preferred is not None and artifact.preferred_courses_per_semester != preferred:
            artifact.preferred_courses_per_semester = preferred
            updates.append(f"Preferred: {preferred}")

        if minimum is not None and artifact.min_courses_per_semester != minimum:
            artifact.min_courses_per_semester = minimum
            updates.append(f"Minimum: {minimum}")

        if maximum is not None and artifact.max_courses_per_semester != maximum:
            artifact.max_courses_per_semester = maximum
            updates.append(f"Maximum: {maximum}")

        if updates:
            print("Course load updated")
            return f"Updated: {', '.join(updates)}"
        return "No updates made."

    @kernel_function(
        name="time_preference",
        description="Update class time preference based on your question to the user.",
    )
    def update_time_preference(
            self,
            time: Annotated[TimePreference, "Class time preference"] = None,
    ) -> str:
        """Update class time preference."""
        if not time:
            return "No time preference provided."

        artifact = self.state.artifact
        if artifact.time_preference != time:
            artifact.time_preference = time
            print("Time preference updated")
            return f"Updated time preference: {time}"
        return "No update needed."

    @kernel_function(
        name="summer_availability"
    )
    def update_summer_availability(
            self,
            available: Annotated[bool, "Available for summer courses"] = None,
    ) -> str:
        """Update summer course availability."""
        if available is None:
            return "No summer availability provided."

        artifact = self.state.artifact
        if artifact.summer_available != available:
            artifact.summer_available = available
            print("Summer availability updated")
            return f"Updated summer availability: {'Yes' if available else 'No'}"
        return "No update needed."

    @kernel_function(
        name="career_goals"
    )
    def update_career_goals(
            self,
            goals: Annotated[str, "Career goals"] = None,
    ) -> str:
        """Update career goals."""

        def safe_list(value):
            if not value:
                return None
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    import json
                    return json.loads(value)
                except:
                    return [item.strip() for item in value.split(",")]
            return [str(value)]

        goals = safe_list(goals)
        if not goals:
            return "No career goals provided."

        updates = []
        artifact = self.state.artifact
        new_goals = [g for g in goals if g not in artifact.career_goals]

        if new_goals:
            artifact.career_goals.extend(new_goals)
            updates.append(f"Goals: {', '.join(new_goals)}")
            print("Career goals updated")
            return f"Updated: {', '.join(updates)}"
        return "No new goals to add."

    @kernel_function(
        name="credits_needed"
    )
    def update_credits_needed(
            self,
            total: Annotated[int, "Total credits for graduation"] = None,
    ) -> str | None:
        """Update total credits needed."""
        if total is None:
            return "No credit information provided."

        artifact = self.state.artifact
        if artifact.total_credits_needed != total:
            artifact.total_credits_needed = total
            print("Credits needed updated")
            return f"Updated total credits: {total}"
        return None


    @kernel_function(name="clear_student_major_info",
                     description="""Clear student major information. 
                     This is used when the user has indicated they want 
                     a different major from the one they initially selected""")
    def clear_student_major_info(self) -> str:
        """Clear student major information."""
        artifact = self.state.artifact
        (artifact.major, artifact.courses_selected,
         artifact.concentration, artifact.minor, artifact.career_goals,
         artifact.degree_type, artifact.total_credits_needed) = None, [], None, [], [], None, None
        return "Student major information cleared successfully."

    @kernel_function(name="get_user_info",
                     description="""Get information about the user from the Panda API. 
                     (tasks/assignments, courses taken, class schedules, degree planners,
                     graduation semester, or their degree program). Tasks have stageId 1-3, for not started,
                     in progress, completed respectively.""")

    def get_user_info(self) -> UserModel:
        return self.user_service.get_user()