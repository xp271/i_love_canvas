"""
网页抓取模块
"""
from .course_url_extractor import CourseURLExtractor
from .course_assignments_capture import CourseAssignmentsCapture
from .assignment_detail_capture import AssignmentDetailCapture

__all__ = ['CourseURLExtractor', 'CourseAssignmentsCapture', 'AssignmentDetailCapture']

