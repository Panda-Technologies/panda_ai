from typing import List

from semantic_kernel.functions import kernel_function

from src.api.api_fetch.models import RequirementModel
from src.api.api_fetch.services import DegreeService, PandaService
from src.api.main import SESSION_COOKIE


class DegreeInfoPlugin:
    def __init__(self):
        self.degree_service = DegreeService(PandaService(SESSION_COOKIE))

    @kernel_function(name="get_degree_requirements", description="Gets all requirements for a degree, use this when a user wants info about a degree requirements. Input should not contain degree type (eg. BA, BS)")
    def get_degree_requirements(self, degree_name: str) -> List[RequirementModel]:
        """Get degree requirements for a given degree name."""
        return self.degree_service.get_degree_req(degree_name)
