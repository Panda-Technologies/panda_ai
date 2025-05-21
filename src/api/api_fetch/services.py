from typing import Any, List

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

from src.api.api_fetch.models import UserModel, RequirementModel


class PandaService:
    def __init__(self, session_cookie: str):
        self.session_cookie = session_cookie
        transport = RequestsHTTPTransport(
            url="http://localhost:5001/graphql",
            headers={"Cookie": self.session_cookie}
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def fetch_panda(self, query: str, variables: dict[str, any] | None) -> dict[str, Any]:
        query_obj = gql(query)
        return self.client.execute(query_obj, variable_values=variables)

class UserService:
    def __init__(self, panda_service: PandaService):
        self.panda = panda_service

    def get_user(self):
        query = """
          query GetUser {
            getUser {
              email
              university
              isPremium
              yearInUniversity
              graduationSemesterName
              gpa
              tasks {
                id
                title
                description
                dueDate
                stageId
                classCode
                source
              }
              classSchedules {
                id
                title
                isCurrent
                semesterId
              }
              degreePlanners {
                id
                title
                degreeId
              }
              attendancePercentage
              assignmentCompletionPercentage
              takenClassIds
              degrees {
                id
                name
                type
                coreCategories
                gatewayCategories
                electiveCategories
                numberOfCores
                numberOfElectives
              }
            }
          }
        """

        output = self.panda.fetch_panda(query, None)
        user_model = UserModel.model_validate(output["getUser"])
        return user_model

class DegreeService:
    def __init__(self, panda_service: PandaService):
        self.panda = panda_service

    def get_degree_req(self, degree_name: str) -> List[RequirementModel]:
        query = """
        query GetRequirements($degreeName: String) {
          getRequirements(degreeName: $degreeName) {
            id
            category
            reqType
            classIds
            degreeId
            classNames
          }
        }
        """
        output = self.panda.fetch_panda(query, {"degreeName": degree_name})
        requirement_model: List[RequirementModel] = [RequirementModel.model_validate(requirement) for requirement in output["getRequirements"]]
        return requirement_model