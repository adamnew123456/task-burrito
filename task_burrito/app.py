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
import sys
from typing import List, Mapping

from task_burrito import exporter, parser, utils


def build_config_map(configs: List[str]) -> Mapping[str, str]:
    """
    Parses a configuration list into a mapping of configuration values.
    """
    config_map = {}
    for config in configs:
        if "=" not in config:
            print(
                "Invalid option '{}', not in KEY=VALUE format".format(config),
                file=sys.stderr,
            )
            sys.exit(1)

        (key, value) = config.split("=", 2)
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
        logger = utils.Logger(sys.stderr, sys.stderr)
        input_file = sys.argv[1]
        out = sys.argv[2]
        configs = build_config_map(sys.argv[3:])

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
            try:
                include_summary = int(configs.get("summary", "1")) == 1
            except ValueError:
                print("Invalid value for summary config, must be 1 or 0")
                sys.exit(1)

            include_toc = out in {"simple", "full"}
            include_calendar = out in {"calendar", "full"}
            exporter.export_html_report(
                task_map, sys.stdout, include_toc, include_calendar, include_summary
            )
        elif out == "plain":
            exporter.plain_exporter(tasks, sys.stdout)
        else:
            print("Unknown exporter:", out, file=sys.stderr)
            sys.exit(1)

    except IndexError:
        print("Usage: burrito INPUT-FILE EXPORTER [property=value]...", file=sys.stderr)
        sys.exit(1)
