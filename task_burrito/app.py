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

- fold=BOOLEAN: Whether to omit subtasks from the table of contents when all
  of them are completed. True by default.

Calendar Exporter Properties:

- summary=BOOLEAN: Whether to include the full task list with notes. True by default.

Full Exporter Properties:

- summary=BOOLEAN: Whether to include the full task list with notes. True by default.

- fold=BOOLEAN: Whether to omit subtasks from the TOC when all of them are
  completed. True by default.
"""
import sys
from typing import List

from task_burrito import exporter, parser, utils


def build_config_map(configs: List[str]) -> exporter.ExportConfig:
    """
    Parses a configuration list into a mapping of configuration values.
    """
    export_config = exporter.ExportConfig()
    for config in configs:
        if "=" not in config:
            raise ValueError(
                "Invalid option '{}', not in KEY=VALUE format".format(config),
                file=sys.stderr,
            )

        (key, value) = config.split("=", 1)
        if key == "summary":
            try:
                export_config.include_summary = int(value) == 1
            except ValueError:
                raise ValueError(
                    "Invalid value {} for summary config value".format(value)
                )
        elif key == "fold":
            try:
                export_config.fold_toc = int(value) == 1
            except ValueError:
                raise ValueError("Invalid value {} for fold config value".format(value))

    return export_config


def main():
    """
    Parses the input file and dispatches to the chosen exporter.
    """
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__)
        sys.exit(1)

    try:
        logger = utils.Logger(sys.stderr, sys.stderr)
        input_file = sys.argv[1]
        out = sys.argv[2]
        try:
            configs = build_config_map(sys.argv[3:])
        except ValueError as err:
            print(str(err), file=sys.stderr)
            sys.exit(1)

        if input_file == "-":
            in_fobj = sys.stdin
        else:
            in_fobj = open(input_file)

        tasks = parser.parse_file(in_fobj, logger)
        if not tasks:
            print("Tasks file cannot be empty", file=sys.stderr)
            sys.exit(1)

        task_map = utils.verify_task_tree(tasks)
        utils.resolve_task_defaults(task_map)

        is_html_export = out in {"simple", "calendar", "full"}
        if is_html_export:
            configs.include_toc = out in {"simple", "full"}
            configs.include_calendar = out in {"calendar", "full"}
            configs.head_prefix = '<meta http-equiv="refresh" content="5">'
            exporter.export_html_report(task_map, sys.stdout, configs)
        elif out == "plain":
            exporter.plain_exporter(tasks, sys.stdout)
        else:
            print("Unknown exporter:", out, file=sys.stderr)
            sys.exit(1)

    except IndexError:
        print("Usage: burrito INPUT-FILE EXPORTER [property=value]...", file=sys.stderr)
        sys.exit(1)
