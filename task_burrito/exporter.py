"""
Takes tasks from the parser and processes them into different formats.
"""
import calendar
from dataclasses import dataclass, field
import datetime
import html
from typing import IO, List, Mapping, Tuple

import markdown
from task_burrito import utils

HTML_HEADER = """
<html lang="en">
    <head>
        %HEAD%
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title> Project List </title>
        <style>
        table, th, td { border: 1px solid black; border-collapse: collapse; vertical-align: top; }
        .toc { list-style: none; }
        body { background-color: darkgray; }
        td.calendar { min-width: 80px; height: 50px; }
        </style>
    </head>
    <body>
"""

HTML_FOOTER = """
      %TAIL%
    </body>
</html>
"""


@dataclass
class ExportConfig:
    """
    Configuration options for the exporter
    """

    include_toc: bool = field(default=False, init=False)
    include_calendar: bool = field(default=False, init=False)
    include_summary: bool = field(default=True, init=False)
    fold_toc: bool = field(default=True, init=False)
    body_suffix: str = field(default=None, init=False)
    head_prefix: str = field(default=None, init=False)


def task_id_link(task_id: Tuple[int]) -> str:
    """
    Converts a task identifier into an HTML link to that task.
    """
    return "<a href='#{}'> {} </a>".format(
        utils.task_id_str(task_id), utils.task_id_str(task_id)
    )


def task_status_color(status: utils.TaskStatus) -> str:
    """
    Converts a task status into a color-coded form of the status.
    """
    if status == utils.TaskStatus.TODO:
        name = "TODO"
        color = "red"
    elif status == utils.TaskStatus.IN_PROGRESS:
        name = "IN-PROGRESS"
        color = "orange"
    elif status == utils.TaskStatus.BLOCKED:
        name = "BLOCKED"
        color = "yellow"
    else:
        name = "DONE"
        color = "green"

    return "<span style='font-weight: bold; color: {}'> {} </span>".format(color, name)


def plain_exporter(tasks: List[utils.Task], output: IO):
    """
    Exports a task list back into the default format, sorting the tasks and
    dropping anything that was ignored.
    """
    tasks = utils.sort_tasks(tasks)
    for task in tasks:
        print("---", file=output)
        print("task", utils.task_id_str(task.task_id), file=output)
        print("label", task.label, file=output)
        print("status", str(task.status), file=output)
        if task.priority is not None:
            print("priority", task.priority if utils.is_valued(task.priority) else "none", file=output)
        if task.deadline is not None:
            print("deadline", task.deadline.isoformat() if utils.is_valued(task.deadline) else "none", file=output)
        if task.depends:
            print(
                "depends",
                " ".join(utils.task_id_str(dep) for dep in sorted(task.depends)),
                file=output,
            )
        print("---", file=output)
        print(task.content, end="", file=output)


def export_task_list(tasks: List[utils.Task], output: IO):
    """
    Exports information about tasks only without any front matter. Meant for
    use with other exporters.
    """
    for task in tasks:
        print(
            "<h1 id='{}'>".format(utils.task_id_str(task.task_id)),
            utils.task_id_str(task.task_id),
            html.escape(task.label),
            "</h1>",
            file=output,
        )
        print("<div><table>", file=output)
        print("<tr>", file=output)
        print("<th>ID</th>", file=output)
        print("<th>Status</th>", file=output)
        print("<th>Priority</th>", file=output)
        print("<th>Deadline</th>", file=output)
        print("<th>Dependencies</th>", file=output)
        print("</tr>", file=output)
        print("<td>", utils.task_id_str(task.task_id), "</td>", file=output)
        print("<td>", task_status_color(task.status), "</td>", file=output)
        print("<td>", task.priority if utils.is_valued(task.priority) else "Unassigned", "</td>", file=output)
        print(
            "<td>",
            task.deadline.isoformat() if utils.is_valued(task.deadline) else "Unassigned",
            "</td>",
            file=output,
        )
        print(
            "<td>",
            ", ".join(task_id_link(dep) for dep in sorted(task.depends)),
            "</td>",
            file=output,
        )
        print("</tr>", file=output)
        print("</table></div>", file=output)
        if task.content:
            print("<h2>Notes</h2>", file=output)
            print(markdown.markdown(task.content, file=output), file=output)


def export_table_of_contents(
    task_map: Mapping[Tuple[int], utils.Task], output: IO, fold: bool
):
    """
    Exports a task list into HTML without doing any restructuring, similar to
    the plain_exporter.
    """
    tasks = utils.sort_tasks(task_map.values())
    if fold:
        foldable = utils.find_foldable_tasks(tasks)
    else:
        foldable = set()

    print("<h1> Table of Contents </h1>", file=output)
    depth = 0
    fold_depth = -1
    for task in tasks:
        if fold_depth != -1 and len(task.task_id) > fold_depth:
            continue

        fold_depth = -1
        while depth < len(task.task_id):
            print("<ol class='toc'>", file=output)
            depth += 1

        while depth > len(task.task_id):
            print("</ol>", file=output)
            depth -= 1

        if task.status == utils.TaskStatus.BLOCKED:
            blockers = [
                task_map[dep]
                for dep in sorted(task.depends)
                if task_map[dep].status != utils.TaskStatus.DONE
            ]
            if blockers:
                short_line = "{} on {}".format(
                    task_status_color(task.status),
                    ", ".join(task_id_link(dep.task_id) for dep in blockers),
                )
            else:
                short_line = task_status_color(task.status)
        elif task.status == utils.TaskStatus.TODO:
            if not utils.is_valued(task.deadline):
                short_line = task_status_color(task.status)
            else:
                short_line = "{} by {}".format(
                    task_status_color(task.status), task.deadline.isoformat()
                )
        elif task.status == utils.TaskStatus.DONE:
            short_line = task_status_color(task.status)
        elif task.status == utils.TaskStatus.IN_PROGRESS:
            if not utils.is_valued(task.deadline):
                short_line = task_status_color(task.status)
            else:
                short_line = "{} due by {}".format(
                    task_status_color(task.status), task.deadline.isoformat()
                )
        else:
            short_line = "Unknown status {}".format(task.status)

        print(
            "<li><strong style='font-size: 1.5em'>",
            task_id_link(task.task_id),
            html.escape(task.label),
            "</strong>",
            short_line,
            "</li>",
            file=output,
        )

        if task.task_id in foldable:
            fold_depth = depth

    while depth > 0:
        print("</ol>", file=output)
        depth -= 1


def export_calendar(task_map: Mapping[Tuple[int], utils.Task], output: IO):
    """
    Exports a task list into a basic calendar view.
    """
    tasks = utils.sort_tasks(task_map.values())
    tasks_with_deadline = (
        task
        for task in tasks
        if utils.is_valued(task.deadline) and task.status != utils.TaskStatus.DONE
    )
    tasks_by_deadline = sorted(tasks_with_deadline, key=lambda task: task.deadline)

    if not tasks_by_deadline:
        print("<h1> No Active Tasks Have A Deadline</h1>", file=output)
    else:
        current_date = utils.first_day_of_month(tasks_by_deadline[0].deadline)
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
                    print("</td>", file=output)

                if new_month:
                    if not first_day:
                        filler_weekday = current_weekday
                        while filler_weekday < 7:
                            print("<td></td>", file=output)
                            filler_weekday += 1

                        print("</tr>", file=output)
                        print("</table>", file=output)

                    first_day = False
                    print(
                        "<h1> {} {} </h1>".format(
                            calendar.month_name[current_date.month], current_date.year
                        ),
                        file=output,
                    )
                    print("<table>", file=output)
                    print("<tr>", file=output)
                    print("<th> Monday </th>", file=output)
                    print("<th> Tuesday </th>", file=output)
                    print("<th> Wednesday </th>", file=output)
                    print("<th> Thursday </th>", file=output)
                    print("<th> Friday </th>", file=output)
                    print("<th> Saturday </th>", file=output)
                    print("<th> Sunday </th>", file=output)
                    print("</tr>", file=output)

                    new_week = False
                    new_month = False
                    print("<tr>", file=output)
                    for _ in range(current_weekday):
                        print("<td></td>", file=output)

                if new_week:
                    print("</tr>", file=output)
                    print("<tr>", file=output)
                    new_week = False

                print("<td class='calendar'><b>", current_date.day, "</b>", file=output)

                current_weekday += 1
                if current_weekday == 7:
                    current_weekday = 0
                    new_week = True

                current_date += datetime.timedelta(days=1)
                if current_date.day == 1:
                    new_month = True

            print("<div>", file=output)
            print(
                "{} {}".format(
                    task_id_link(next_task.task_id), html.escape(next_task.label)
                ),
                file=output,
            )
            print("</div>", file=output)

    print("</td>", file=output)

    # Fill in days up until the end of the month
    end_of_month = utils.first_day_of_next_month(current_date) - datetime.timedelta(
        days=1
    )
    while current_date <= end_of_month:
        if new_week:
            print("</tr>", file=output)
            print("<tr>", file=output)
            new_week = False

        print("<td class='calendar'><b>", current_date.day, "</b></td>", file=output)

        current_weekday += 1
        if current_weekday == 7:
            current_weekday = 0
            new_week = True

        current_date += datetime.timedelta(days=1)

    # Fill in empty cells to contain he last week
    while current_weekday < 7:
        print("<td></td>", file=output)
        current_weekday += 1

    print("</tr></table>", file=output)


def export_html_report(
    task_map: Mapping[Tuple[int], utils.Task], output: IO, config: ExportConfig
):
    """
    Exports a task list into an HTML view, with different components.
    """
    print(HTML_HEADER.replace("%HEAD%", config.head_prefix or ""), file=output)

    if config.include_toc:
        export_table_of_contents(task_map, output, config.fold_toc)
        print("<hr>", file=output)

    if config.include_calendar:
        export_calendar(task_map, output)
        print("<hr>", file=output)

    if config.include_summary:
        export_task_list(utils.sort_tasks(task_map.values()), output)

    print(HTML_FOOTER.replace("%TAIL%", config.body_suffix or ""), file=output)
