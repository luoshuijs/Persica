from enum import IntEnum


class Phase(IntEnum):
    DEPENDENCY = 10
    REPOSITORY = 20
    SERVICE = 30
    COMMAND = 40
    JOB = 50
