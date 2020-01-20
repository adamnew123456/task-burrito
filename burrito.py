#!/usr/bin/env python3
"""
Usage: burrito INPUT-FILE EXPORTER [PROPERTY=VALUE]...

Arguments:

- INPUT-FILE: The path to a Markdown file with Task Burrito anntoations. May
  also be - for stdin.

- EXPORTER: The name of an exporter (one of: "plain", "simple", "calendar", "full")

- PROPERTY=VALUE: Exporter-specific configuration options. Properties with the
  BOOLEAN tag should be assigned to either 1 or 0.

Plain Exporter Properties:

None.

Simple Exporter Properties:

- summary=BOOLEAN: Whether to include the full task list with notes. True by default.

Calendar Exporter Properties:

- summary=BOOLEAN: Whether to include the full task list with notes. True by default.

Full Exporter Properties:

- summary=BOOLEAN: Whether to include the full task list with notes. True by default.
"""

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
import datetime
from enum import Enum
import html
import sys
from typing import Any, IO, List, Mapping, Optional, Tuple, Set

import markdown


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


class FilePosition:
    """
    A position within the file which can be updated as characters are read.
    """

    def __init__(self):
        self.line = 0

    def next_line(self, n: int = 1):
        """
        Advances to the next line and resets the column to the start of the
        line.
        """
        self.line += n

    def __str__(self):
        return "Line {}:".format(self.line)


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


def task_id_link(task_id: Tuple[int]) -> str:
    """
    Converts a task identifier into an HTML link to that task.
    """
    return "<a href='#{}'> {} </a>".format(task_id_str(task_id), task_id_str(task_id))


def task_status_color(status: TaskStatus) -> str:
    """
    Converts a task status into a color-coded form of the status.
    """
    if status == TaskStatus.TODO:
        name = "TODO"
        color = "red"
    elif status == TaskStatus.IN_PROGRESS:
        name = "IN-PROGRESS"
        color = "orange"
    elif status == TaskStatus.BLOCKED:
        name = "BLOCKED"
        color = "darkgoldenrod"
    else:
        name = "DONE"
        color = "green"

    return "<span style='font-weight: bold; color: {}'> {} </span>".format(color, name)


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


def resolve_default_values(tasks: Mapping[Tuple[int], Task]):
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


def sort_tasks(tasks: List[Task]) -> List[Task]:
    """
    Orders tasks hierarchically by their IDs.
    """
    return sorted(tasks, key=lambda entry: entry.task_id)


def warn(position: FilePosition, fmt: str, *args: Any, **kwargs: Any):
    """
    Displays a warning on stderr which refers to the given file position. Does
    not terminate the file processing.
    """
    print(str(position), fmt.format(*args, **kwargs), file=sys.stderr)


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


def parse_task_property(prop: str, value: str, position: FilePosition) -> Optional[Any]:
    """
    Parses and validates a value for the given task property, and returns its
    parsed form if it is valid.
    """
    if prop == "task":
        try:
            return parse_task_id(value)
        except ValueError as err:
            warn(position, "{}", err.args[0])
            return None

    elif prop == "label":
        if not value:
            warn(position, "Task label cannot be empty")
            return None

        return value

    elif prop == "status":
        if value not in ("DONE", "IN-PROGRESS", "BLOCKED", "TODO"):
            warn(position, "Invalid status value '{}'", value)
            return None

        return TaskStatus[value.replace("-", "_")]

    elif prop == "priority":
        try:
            priority = int(value)
            if priority not in range(1, 6):
                warn(position, "Priority value '{}' not in range 1..5", priority)
                return None

            return priority
        except ValueError:
            warn(position, "Priority value '{}' must be an integer", value)
            return None

    elif prop == "deadline":
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            warn(position, "Deadline value '{}' not in format YYYY-MM-DD", value)
            return None

    elif prop == "depends":
        tasks = value.split()
        if not tasks:
            warn(
                position,
                "Depends list should be left out if there are no dependent tasks",
            )
            return None

        task_ids = []
        for task in tasks:
            try:
                task_ids.append(parse_task_id(task))
            except ValueError as err:
                warn(position, "Issue with task ID {}: {}", task, err.args[0])
                return None

        return set(task_ids)

    else:
        warn(position, "Invalid task property {}", prop)
        return None


def parse_task(fobj: IO, position: FilePosition) -> Task:
    """
    Parses a task definition from the given file stream.

    This function assumes that the first line of hypens has already been
    processed and will return with the stream having read the last line of
    hyphens.
    """
    property_words = {"task", "label", "status", "priority", "deadline", "depends"}
    properties = {}

    found_end = False
    for line in fobj:
        line = line.strip()
        position.next_line()

        if not line:
            warn(position, "Blank lines are not recommended within task blocks")
            continue

        if line == "---":
            found_end = True
            break

        try:
            prop_end = line.index(" ")
            prop = line[:prop_end]

            if prop not in property_words:
                warn(position, "Unexpected property type '{}' in task block", prop)
                continue

            if prop in properties:
                warn(
                    position, "Duplicate property '{}' not allowed in task block", prop
                )
                continue

            raw_value = line[prop_end + 1 :].strip()
            value = parse_task_property(prop, raw_value, position)
            if value is not None:
                properties[prop] = value

        except ValueError:
            warn(position, "Ignoring non-property line within task block")

    if not found_end:
        warn(position, "Unexpected task block at end of file")
        return None

    for prop in {"task", "label", "status"}:
        if prop not in properties:
            # Unlike most other problems, there's not a way to recover from
            # this. There's no way to synthesize these values or usefully
            # ignore them.
            raise SyntaxError(
                "{} Task properties must have a '{}' property value".format(
                    str(position), prop
                )
            )

    return Task(
        properties["task"],
        properties["label"],
        properties["status"],
        properties.get("priority"),
        properties.get("deadline"),
        properties.get("depends", set()),
    )


def parse_file(fobj: IO) -> List[Task]:
    """
    Parses the contents of a task file and returns each task along with the
    notes associated with it.
    """
    position = FilePosition()
    current_task = None
    current_content = []
    tasks = []

    for line in fobj:
        position.next_line()
        if line.strip() == "---":
            if current_task is not None:
                current_task.content = "".join(current_content)
                tasks.append(current_task)
                current_content.clear()

            current_task = parse_task(fobj, position)
        elif current_task is None:
            warn(position, "Ignoring content that does not belong to a task")
        else:
            current_content.append(line)

    if current_task is not None:
        current_task.content = "".join(current_content)
        tasks.append(current_task)
        current_content.clear()

    return tasks


def plain_exporter(tasks: List[Task], configs: Mapping[str, str]):
    """
    Exports a task list back into the default format, sorting the tasks and
    dropping anything that was ignored.
    """
    tasks = sort_tasks(tasks)
    for task in tasks:
        print("---")
        print("task", task_id_str(task.task_id))
        print("label", task.label)
        print("status", str(task.status))
        if task.priority:
            print("priority", task.priority)
        if task.deadline:
            print("deadline", task.deadline.isoformat())
        if task.depends:
            print("depends", " ".join(task_id_str(dep) for dep in sorted(task.depends)))
        print("---")
        print(task.content, end="")


HTML_HEADER = """
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title> Project List </title>
        <style>
        table, th, td { border: 1px solid black; border-collapse: collapse; vertical-align: top; }
        .toc { list-style: none; }
        </style>
    </head>
    <body>
"""

HTML_FOOTER = """
    </body>
</html>
"""

def export_task_list(tasks: List[Task]):
    """
    Exports information about tasks only without any front matter. Meant for
    use with other exporters.
    """
    for task in tasks:
        print(
            "<h1 id='{}'>".format(task_id_str(task.task_id)),
            task_id_str(task.task_id),
            html.escape(task.label),
            "</h1>",
        )
        print("<div><table>")
        print("<tr>")
        print("<th>ID</th>")
        print("<th>Status</th>")
        print("<th>Priority</th>")
        print("<th>Deadline</th>")
        print("<th>Dependencies</th>")
        print("</tr>")
        print("<td>", task_id_str(task.task_id), "</td>")
        print("<td>", task_status_color(task.status), "</td>")
        print("<td>", task.priority or "Unassigned", "</td>")
        print("<td>", task.deadline.isoformat() or "Unassigned", "</td>")
        print(
            "<td>",
            ", ".join(task_id_link(dep) for dep in sorted(task.depends)),
            "</td>",
        )
        print("</tr>")
        print("</table></div>")
        if task.content:
            print("<h2>Notes</h2>")
            print(markdown.markdown(task.content))


def export_table_of_contents(task_map: Mapping[Tuple[int], Task]):
    """
    Exports a task list into HTML without doing any restructuring, similar to
    the plain_exporter.
    """
    tasks = sort_tasks(task_map.values())

    print("<h1> Table of Contents </h1>")
    depth = 0
    for task in tasks:
        while depth < len(task.task_id):
            print("<ol class='toc'>")
            depth += 1

        while depth > len(task.task_id):
            print("</ol>")
            depth -= 1

        if task.status == TaskStatus.BLOCKED:
            blockers = (
                task_map[dep]
                for dep in sorted(task.depends)
                if task_map[dep].status != TaskStatus.DONE
            )
            short_line = "{} on {}".format(
                task_status_color(task.status),
                ", ".join(task_id_link(dep.task_id) for dep in blockers)
            )
        elif task.status == TaskStatus.TODO:
            if task.deadline is None:
                short_line = task_status_color(task.status)
            else:
                short_line = "{} by {}".format(task_status_color(task.status), task.deadline.isoformat())
        elif task.status == TaskStatus.DONE:
            short_line = task_status_color(task.status)
        elif task.status == TaskStatus.IN_PROGRESS:
            if task.deadline is None:
                short_line = task_status_color(task.status)
            else:
                short_line = "{} due by {}".format(task_status_color(task.status), task.deadline.isoformat())
        else:
            short_line = "Unknown status {}".format(task.status)

        print(
            "<li><strong style='font-size: 1.5em'>",
            task_id_link(task.task_id),
            html.escape(task.label),
            "</strong>",
            short_line,
            "</li>",
        )

    while depth > 0:
        print("</ol>")
        depth -= 1


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


def export_calendar(task_map: Mapping[Tuple[int], Task]):
    """
    Exports a task list into a basic calendar view.
    """
    header = """
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title> Project Calendar </title>
        <style>
        table, th, td { border: 1px solid black; border-collapse: collapse; }
        td { vertical-align: top }
        </style>
    </head>
    <body>
"""
    footer = """
    </body>
</html>
"""

    tasks = sort_tasks(task_map.values())
    tasks_with_deadline = (
        task
        for task in tasks
        if task.deadline is not None and task.status != TaskStatus.DONE
    )
    tasks_by_deadline = sorted(tasks_with_deadline, key=lambda task: task.deadline)

    if not tasks_by_deadline:
        print("<h1> No Active Tasks Have A Deadline</h1>")
    else:
        today = datetime.date.today()
        current_date = first_day_of_month(today)
        current_weekday = calendar.weekday(
            current_date.year, current_date.month, current_date.day
        )
        first_day = True
        new_month = True
        new_week = True

        while tasks_by_deadline:
            next_task = tasks_by_deadline.pop(0)

            while current_date <= next_task.deadline:
                if not first_day:
                    print("</td>")

                if new_month:
                    if not first_day:
                        print("</tr>")
                        print("</table>")

                    first_day = False
                    print(
                        "<h1> {} {} </h1>".format(
                            calendar.month_name[current_date.month], current_date.year
                        )
                    )
                    print("<table>")
                    print("<tr>")
                    print("<th> Monday </th>")
                    print("<th> Tuesday </th>")
                    print("<th> Wednesday </th>")
                    print("<th> Thursday </th>")
                    print("<th> Friday </th>")
                    print("<th> Saturday </th>")
                    print("<th> Sunday </th>")
                    print("</tr>")

                    new_week = False
                    new_month = False
                    print("<tr>")
                    for _ in range(current_weekday):
                        print("<td></td>")

                if new_week:
                    print("</tr>")
                    print("<tr>")
                    new_week = False

                print("<td><b>", current_date.day, "</b>")

                current_weekday += 1
                if current_weekday == 7:
                    current_weekday = 0
                    new_week = True

                current_date += datetime.timedelta(days=1)
                if current_date.day == 1:
                    new_month = True

            print("<div>")
            print(
                "{} {}".format(
                    task_id_link(next_task.task_id), html.escape(next_task.label)
                )
            )
            print("</div>")

    print("</td>")
    end_of_month = first_day_of_next_month(current_date) - datetime.timedelta(days=1)
    while current_date <= end_of_month:
        if new_week:
            print("</tr>")
            print("<tr>")
            new_week = False

        print("<td><b>", current_date.day, "</b></td>")

        current_weekday += 1
        if current_weekday == 7:
            current_weekday = 0
            new_week = True

        current_date += datetime.timedelta(days=1)

    print("</tr></table>")

def export_html_report(task_map: Mapping[Tuple[int], Task], include_toc: bool, include_calendar: bool, include_summary: bool):
    """
    Exports a task list into an HTML view, with different components.
    """
    print(HTML_HEADER)

    if include_toc:
        export_table_of_contents(task_map)
        print('<hr>')

    if include_calendar:
        export_calendar(task_map)
        print('<hr>')

    if include_summary:
        export_task_list(sort_tasks(task_map.values()))

    print(HTML_FOOTER)

def build_config_map(configs: List[str]) -> Mapping[str, str]:
    """
    Parses a configuration list into a mapping of configuration values.
    """
    config_map = {}
    for config in configs:
        if '=' not in config:
            print("Invalid option '{}', not in KEY=VALUE format".format(config), file=sys.stderr)
            sys.exit(1)

        (key, value) = config.split('=', 2)
        config_map[key] = value

    return config_map

def main():
    """
    Parses the input file and dispatches to the chosen exporter.
    """
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__)
        sys.exit(1)

    try:
        input_file = sys.argv[1]
        exporter = sys.argv[2]
        configs = build_config_map(sys.argv[3:])

        if input_file == "-":
            in_fobj = sys.stdin
        else:
            in_fobj = open(input_file)

        tasks = parse_file(in_fobj)
        if not tasks:
            print("Tasks file cannot be empty", file=sys.stderr)
            sys.exit(1)

        task_map = verify_task_tree(tasks)
        resolve_default_values(task_map)

        is_html_export = exporter in {"simple", "calendar", "full"}
        if is_html_export:
            try:
                include_summary = int(configs.get("summary", "1")) == 1
            except ValueError:
                print("Invalid value for summary config, must be 1 or 0")
                sys.exit(1)

            include_toc = exporter in {"simple", "full"}
            include_calendar = exporter in {"calendar", "full"}
            export_html_report(task_map, include_toc, include_calendar, include_summary)
        elif exporter == "plain":
            plain_exporter(tasks, configs)
        else:
            print("Unknown exporter:", exporter, file=sys.stderr)
            sys.exit(1)

    except IndexError:
        print("Usage: burrito INPUT-FILE EXPORTER [property=value]...", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
