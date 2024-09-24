from dataclasses import dataclass
from typing import List, Optional

from camel.typing import TestType


@dataclass
class TestUtilityMethod():
    name: str
    class_name: str
    signature: str
    code: str
    comment: str
    type: TestType = TestType.TEST_UTILITY_METHOD

@dataclass
class TestMethod():
    name: str
    class_name: str
    signature: str
    code: str
    comment: str
    type: TestType = TestType.TEST_METHOD

@dataclass
class TestCase():
    name: str
    test_method: Optional[TestMethod] = None
    test_utility_methods: Optional[List[TestUtilityMethod]] = None
    test_output: Optional[List[str]] = None
    stack_trace: Optional[List[str]] = None
    
    def __str__(self) -> str:
        return self.name

@dataclass
class TestSuite():
    name: str
    test_cases: List[TestCase]
    
    def __str__(self) -> str:
        return f"{self.name}: {str(self.test_cases)}"


@dataclass
class TestFailure():
    project: str
    bug_ID: int
    test_suites: List[TestSuite]
    buggy_methods: Optional[List[str]] = None





