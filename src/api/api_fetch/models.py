from pydantic import BaseModel, Field
from typing import List, Annotated

class ClassSection(BaseModel):
    id: Annotated[int, Field(alias="section_id")]
    section: Annotated[str, Field(alias="section_number")]
    classId: Annotated[int, Field(alias="class_id")]
    dayOfWeek: Annotated[str, Field(alias="day_of_week")]
    startTime: Annotated[str, Field(alias="start_time")]
    endTime: Annotated[str, Field(alias="end_time")]
    professor: Annotated[str, Field(alias="professor_name")]
    rateMyProfessorRating: Annotated[float | None, Field(alias="rate_my_professor_rating")]


class Class(BaseModel):
    id: Annotated[int, Field(alias="class_id")]
    classCode: Annotated[str, Field(alias="class_code")]
    courseType: Annotated[str, Field(alias="class_type")]
    title: Annotated[str, Field(alias="class_title")]
    description: Annotated[str, Field(alias="class_description")]
    sections: Annotated[List[ClassSection], Field(alias="class_sections")]


class ClassScheduleEntry(BaseModel):
    id: Annotated[int, Field(alias="class_schedule_entry_id")]
    classId: Annotated[int, Field(alias="class_id")]
    sectionId: Annotated[int, Field(alias="section_id")]
    course: Annotated[Class, Field(alias="class_object")]


class ClassSchedule(BaseModel):
    id: Annotated[int, Field(alias="class_schedule_id")]
    title: Annotated[str, Field(alias="class_title")]
    isCurrent: Annotated[bool, Field(alias="is_current")]
    semesterId: Annotated[str, Field(alias="semester_id")]
    entries: Annotated[List[ClassScheduleEntry], Field(alias="class_schedule_entries")]


class Task(BaseModel):
    id: Annotated[int, Field(alias="task_id")]
    title: Annotated[str, Field(alias="task_title")]
    dueDate: Annotated[str, Field(alias="due_date")]
    stageId: Annotated[int, Field(alias="stage_id")]
    classCode: Annotated[str, Field(alias="class_code")]
    description: Annotated[str, Field(alias="description")]
    source: Annotated[str, Field(alias="source")]

class Degree(BaseModel):
    id: Annotated[int, Field(alias="degree_id")]
    name: Annotated[str, Field(alias="degree_name")]
    type: Annotated[str, Field(alias="degree_type")]
    coreCategories: Annotated[List[str], Field(alias="core_categories")]
    electiveCategories: Annotated[List[str], Field(alias="elective_categories")]
    gatewayCourses: Annotated[List[str], Field(alias="gateway_courses")]
    numberOfCores: Annotated[float, Field(alias="number_of_cores")]

class SemesterEntry(BaseModel):
    id: Annotated[int, Field(alias="semester_entry_id")]
    semesterId: Annotated[int, Field(alias="semester_id")]
    classId: Annotated[int, Field(alias="class_id")]

class Semester(BaseModel):
    id: Annotated[int, Field(alias="semester_id")]
    degreeId: Annotated[int, Field(alias="degree_id")]
    name: Annotated[str, Field(alias="semester_name")]
    credits: Annotated[int, Field(alias="credits")]
    entries: Annotated[List[SemesterEntry], Field(alias="semester_entries")]

class DegreePlanner(BaseModel):
    id: Annotated[int, Field(alias="degree_planner_id")]
    title: Annotated[str, Field(alias="degree_planner_title")]
    degreeId: Annotated[int, Field(alias="degree_id")]
    degree: Annotated[Degree, Field(alias="degree")]
    semester: Annotated[list[Semester], Field(alias="semesters")]

class Requirement(BaseModel):
    id: Annotated[int, Field(alias="requirement_id")]
    category: Annotated[str, Field(alias="requirement_category")]
    reqType: Annotated[str, Field(alias="requirement_type")]
    classIds: Annotated[List[int], Field(alias="class_ids")]
    degreeId: Annotated[int, Field(alias="degree_id")]

class User(BaseModel):
    id: Annotated[int, Field(alias="user_id")]
    email: Annotated[str, Field(alias="email")]
    degrees: Annotated[list[Degree], Field(alias="degrees")]
    tasks: Annotated[list[Task], Field(alias="tasks")]
    classSchedules: Annotated[list[ClassSchedule], Field(alias="class_schedules")]
    degreePlanners: Annotated[list[DegreePlanner], Field(alias="degree_planners")]
