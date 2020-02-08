"""
Various utilities used by the rest of the package.
"""
from collections import Counter, defaultdict
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Mapping, Optional, Set, Tuple


class FilePosition:
    """
    A position within the file which can be updated as characters are read.
    """

    def __init__(self, name):
        self.name = name
        self.line = 0

    def next_line(self, n: int = 1):
        """
        Advances to the next line and resets the column to the start of the
        line.
        """
        self.line += n

    def __str__(self):
        return "{}:{}:".format(self.name, self.line)


class Logger:
    """
    A basic logger which includes reporting the positions of errors and
    warnings.
    """

    def __init__(self, warn_output, error_output):
        self.warn_output = warn_output
        self.error_output = error_output

    def warn(self, position: FilePosition, fmt: str, *args: Any, **kwargs: Any):
        """
        Writes a warning about a specific location in the input file.
        """
        print(str(position), fmt.format(*args, **kwargs), file=self.warn_output)

    def error(self, position: FilePosition, fmt: str, *args: Any, **kwargs: Any):
        """
        Writes an error about a specific location in the input file.
        """
        print(str(position), fmt.format(*args, **kwargs), file=self.error_output)


class TaskStatus(Enum):
    """
    The status values allowed for a task.
    """

    DONE = 1
    IN_PROGRESS = 2
    BLOCKED = 3
    TODO = 4

    def __str__(self):
        if self.name == "IN_PROGRESS":
            return "IN-PROGRESS"

        return self.name


# Used to indicate that a property explicitly should not be inherited from the
# parent
NOT_PROVIDED = object()


@dataclass
class Task:
    """
    The metadata and notes stored about a task.
    """

    task_id: Tuple[int]
    label: str
    status: TaskStatus
    priority: Optional[int]
    deadline: Optional[datetime.date]
    depends: Set[Tuple[int]]
    content: str = field(default="", init=False)


def task_id_parent(task_id: Tuple[int]) -> Tuple[int]:
    """
    Gets the parent ID of a task ID.
    """
    if len(task_id) == 1:
        return None

    return task_id[:-1]


def task_id_ancestors(task_id: Tuple[int]) -> List[Tuple[int]]:
    """
    Gets the full list of tasks above the given task.
    """
    parents = []
    parent = task_id_parent(task_id)
    while parent is not None:
        parents.append(parent)
        parent = task_id_parent(parent)

    return parents


def task_id_str(task_id: Tuple[int]) -> str:
    """
    Converts a task identifier into a key for the task map.
    """
    return ".".join(str(part) for part in task_id)


def verify_task_tree(tasks: List[Task]) -> Mapping[Tuple[int], Task]:
    """
    Converts a task list into a task map, while verifying that all parts of the
    task hierarchy exist.
    """
    task_map = {task.task_id: task for task in tasks}
    for task in tasks:
        for ancestor in task_id_ancestors(task.task_id):
            if ancestor not in task_map:
                raise ValueError(
                    "There is no task {}, which should be an ancestor of task {}".format(
                        ancestor, task_id_str(ancestor)
                    )
                )

    return task_map


def task_child_map(tasks: List[Task]) -> Mapping[Tuple[int], Set[Tuple[int]]]:
    """
    Builds a mapping from each task into the immediate children of that task.
    """
    task_children = defaultdict(set)
    for task in tasks:
        parent = task_id_parent(task.task_id)
        if parent is not None:
            task_children[parent].add(task.task_id)

    return task_children


def resolve_task_defaults(tasks: Mapping[Tuple[int], Task]):
    """
    Updates all tasks so that they inherit the provided values from their
    parent tasks.
    """
    child_map = task_child_map(tasks.values())

    for task in sort_tasks(tasks.values()):
        parent_id = task_id_parent(task.task_id)
        if parent_id is not None:
            parent = tasks[parent_id]
            if task.deadline is None:
                task.deadline = parent.deadline

            if task.priority is None:
                task.priority = parent.priority

        task.depends |= child_map[task.task_id]


def find_foldable_tasks(tasks: List[Task]) -> Set[Tuple[int]]:
    """
    Finds tasks whose children are all marked as DONE. These can be omitted
    from a table of contents view if folding is enabled.
    """
    all_children = Counter()
    completed_children = Counter()
    for task in tasks:
        parent = task_id_parent(task.task_id)
        if parent is not None:
            all_children[parent] += 1
            if task.status == TaskStatus.DONE:
                completed_children[parent] += 1

    return {
        task.task_id
        for task in tasks
        if all_children[task.task_id] == completed_children[task.task_id]
        and all_children[task.task_id] > 0
    }


def sort_tasks(tasks: List[Task], reverse: bool = False) -> List[Task]:
    """
    Orders tasks hierarchically by their IDs.
    """
    return sorted(tasks, key=lambda entry: entry.task_id, reverse=reverse)


def parse_task_id(task_id: str) -> Tuple[int]:
    """
    Checks that a task ID is valid and returns its parsed form, throwing a
    ValueError if it is invalid.
    """
    task_id_parts = task_id.split(".")
    if not task_id_parts:
        raise ValueError("Task ID cannot be empty")

    task_id_values = []
    for part in task_id_parts:
        error = None
        try:
            part_value = int(part)
            if part_value <= 0:
                error = "Task ID part '{}' must be positive".format(part_value)

            task_id_values.append(part_value)
        except ValueError:
            error = "Task ID part '{}' must be an integer".format(part)

        if error is not None:
            raise ValueError(error)

    return tuple(task_id_values)


def first_day_of_month(date: datetime.date) -> datetime.date:
    """
    Computes the first day of the given month
    """
    return date - datetime.timedelta(days=date.day - 1)


def first_day_of_next_month(date: datetime.date) -> datetime.date:
    """
    Computes the first day of the month after the given one.
    """
    this_month = first_day_of_month(date)
    end_of_year = this_month.month == 12
    return datetime.date(
        this_month.year if not end_of_year else this_month.year + 1,
        this_month.month + 1 if not end_of_year else 1,
        1,
    )


def is_valued(value: Any):
    """
    Checks that a value is either None or NOT_PROVIDED.
    """
    return not (value is None or value is NOT_PROVIDED)
