from typing import Annotated, List, Optional, Dict

from semantic_kernel.functions import kernel_function

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext


class CourseRecommendationPlugin:
    def __init__(self, state: ConversationContext):
        self.state = state

    @kernel_function(
        name="add_courses",
        description="Add course codes to student's selection when you recommend courses or when the user asks to add specific classes. Format courses as DEPT NUM (e.g., COMP 110, MATH 231). Call this function whenever discussing specific classes that the student should take."
    )
    def add_courses(
            self,
            courses: Annotated[str, "Course codes (e.g., COMP 110, MATH 231)"] = None,
            reason: Annotated[str, "Reason for adding these courses"] = None,
    ) -> str:
        """Add courses to student's selection when recommended or requested."""

        def parse_courses(value):
            if not value:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                # Try to parse as JSON list or split by commas
                try:
                    import json
                    return json.loads(value)
                except:
                    # Split by commas or spaces and clean up course codes
                    import re
                    courses = []
                    for item in re.split(r'[,;\s]+', value):
                        item = item.strip()
                        if item:
                            # Format course codes consistently (e.g., "COMP110" → "COMP 110")
                            match = re.match(r'([A-Z]+)[\s]*(\d+.*)', item, re.IGNORECASE)
                            if match:
                                dept, num = match.groups()
                                courses.append(f"{dept.upper()} {num}")
                            else:
                                courses.append(item.upper())
                    return courses
            return [str(value)]

        courses_list = parse_courses(courses)
        if not courses_list:
            return "No courses provided to add."

        updates = []
        artifact = self.state.artifact

        # Add each course if it's not already in the list
        for course in courses_list:
            if course not in artifact.courses_selected:
                artifact.courses_selected.append(course)
                updates.append(course)

        if updates:
            reason_text = f" for {reason}" if reason else ""
            print(f"Added courses: {', '.join(updates)}")
            return f"Added courses{reason_text}: {', '.join(updates)}"
        return "All courses were already in your selection."

    @kernel_function(
        name="clear_all_courses",
        description="Clear all recommended or selected courses."
    )
    async def clear_all_courses(self) -> str:
        self.state.artifact.courses_selected.clear()
        return "All recommended courses cleared"