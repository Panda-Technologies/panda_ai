from enum import Enum
from typing import Annotated, List, Optional

from semantic_kernel.functions import kernel_function

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext, AcademicTerm
from src.api.api_fetch.models import UserModel
from src.api.api_fetch.services import UserService, PandaService
from src.api.main import SESSION_COOKIE

class StudentInfoPlugin:
    def __init__(self, state: ConversationContext):
        self.state = state
        self.user_service = UserService(PandaService(SESSION_COOKIE))

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