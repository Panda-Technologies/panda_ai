from pydantic import BaseModel
from typing import List, Optional

class ClassSectionModel(BaseModel):
    id: int
    section: str
    classId: int
    dayOfWeek: str
    startTime: str
    endTime: str
    professor: str
    rateMyProfessorRating: Optional[float] = None


class ClassModel(BaseModel):
    id: int
    classCode: str
    courseType: str
    title: str
    description: str
    sections: Optional[List[ClassSectionModel]] = None


class ClassScheduleEntryModel(BaseModel):
    id: int
    classId: int
    sectionId: int
    course: ClassModel


class ClassScheduleModel(BaseModel):
    id: int
    title: str
    isCurrent: Optional[bool] = None
    semesterId: str
    entries: Optional[List[ClassScheduleEntryModel]] = None


class TaskModel(BaseModel):
    id: int
    title: str
    dueDate: str
    stageId: int
    classCode: str
    description: str
    source: str


class DegreeModel(BaseModel):
    id: int
    name: str
    type: str
    coreCategories: List[str]
    electiveCategories: List[str]
    gatewayCategories: List[str]  # Changed from gatewayCourses to match API
    numberOfCores: float
    numberOfElectives: Optional[float] = None  # Added optional field


class SemesterEntryModel(BaseModel):
    id: int
    semesterId: int
    classId: int


class SemesterModel(BaseModel):
    id: int
    degreeId: int
    name: str
    credits: int
    entries: Optional[List[SemesterEntryModel]] = None


class DegreePlannerModel(BaseModel):
    id: int
    title: str
    degreeId: int
    degree: Optional[DegreeModel] = None
    semester: Optional[List[SemesterModel]] = None


class RequirementModel(BaseModel):
    id: int
    category: str
    reqType: str
    classIds: List[int]
    degreeId: int


class UserModel(BaseModel):
    email: str
    university: Optional[str] = None
    isPremium: Optional[bool] = None
    yearInUniversity: Optional[str] = None
    graduationSemesterName: Optional[str] = None
    gpa: Optional[float] = None
    tasks: List[TaskModel]
    classSchedules: List[ClassScheduleModel]
    degreePlanners: List[DegreePlannerModel]
    attendancePercentage: Optional[float] = None
    assignmentCompletionPercentage: Optional[float] = None
    takenClassIds: List[int] = []
    degrees: List[DegreeModel]