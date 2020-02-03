"""
Processes Markdown files containing Task Burrito annotations into a series of
Tasks.
"""
import datetime
from typing import Any, IO, List, Optional

from task_burrito import utils


def parse_task_property(
    prop: str, value: str, logger: utils.Logger, position: utils.FilePosition
) -> Optional[Any]:
    """
    Parses and validates a value for the given task property, and returns its
    parsed form if it is valid.
    """
    if prop == "task":
        try:
            return utils.parse_task_id(value)
        except ValueError as err:
            logger.warn(position, "{}", err.args[0])
            return None

    elif prop == "label":
        if not value:
            logger.warn(position, "Task label cannot be empty")
            return None

        return value

    elif prop == "status":
        value = value.upper()
        if value not in ("DONE", "IN-PROGRESS", "BLOCKED", "TODO"):
            logger.warn(position, "Invalid status value '{}'", value)
            return None

        return utils.TaskStatus[value.replace("-", "_")]

    elif prop == "priority":
        try:
            if value.lower() == "none":
                return utils.NOT_PROVIDED
            else:
                priority = int(value)
                if priority not in range(1, 6):
                    logger.warn(position, "Priority value '{}' not in range 1..5", priority)
                    return None

                return priority
        except ValueError:
            logger.warn(position, "Priority value '{}' must be an integer", value)
            return None

    elif prop == "deadline":
        try:
            if value.lower() == "none":
                return utils.NOT_PROVIDED
            else:
                return datetime.date.fromisoformat(value)
        except ValueError:
            logger.warn(position, "Deadline value '{}' not in format YYYY-MM-DD", value)
            return None

    elif prop == "depends":
        tasks = value.split()
        if not tasks:
            logger.warn(
                position,
                "Depends list should be left out if there are no dependent tasks",
            )
            return None

        task_ids = []
        for task in tasks:
            try:
                task_ids.append(utils.parse_task_id(task))
            except ValueError as err:
                logger.warn(position, "Issue with task ID {}: {}", task, err.args[0])
                return None

        return set(task_ids)

    else:
        logger.warn(position, "Invalid task property {}", prop)
        return None


def parse_task(
    fobj: IO, logger: utils.Logger, position: utils.FilePosition
) -> utils.Task:
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
            logger.warn(position, "Blank lines are not recommended within task blocks")
            continue

        if line == "---":
            found_end = True
            break

        try:
            prop_end = line.index(" ")
            prop = line[:prop_end]

            if prop not in property_words:
                logger.warn(
                    position, "Unexpected property type '{}' in task block", prop
                )
                continue

            if prop in properties:
                logger.warn(
                    position, "Duplicate property '{}' not allowed in task block", prop
                )
                continue

            raw_value = line[prop_end + 1 :].strip()
            value = parse_task_property(prop, raw_value, logger, position)
            if value is not None:
                properties[prop] = value

        except ValueError:
            logger.warn(position, "Ignoring non-property line within task block")

    if not found_end:
        logger.warn(position, "Unexpected task block at end of file")
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

    return utils.Task(
        properties["task"],
        properties["label"],
        properties["status"],
        properties.get("priority"),
        properties.get("deadline"),
        properties.get("depends", set()),
    )


def parse_file(fobj: IO, logger: utils.Logger) -> List[utils.Task]:
    """
    Parses the contents of a task file and returns each task along with the
    notes associated with it.
    """
    position = utils.FilePosition()
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

            current_task = parse_task(fobj, logger, position)
        elif current_task is None:
            logger.warn(position, "Ignoring content that does not belong to a task")
        else:
            current_content.append(line)

    if current_task is not None:
        current_task.content = "".join(current_content)
        tasks.append(current_task)
        current_content.clear()

    return tasks
