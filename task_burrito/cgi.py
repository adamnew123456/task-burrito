"""
Usage: burrito-cgi INPUT-FILE EXPORTER [PROPERTY=VALUE]...

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
import html
from io import StringIO
import sys
from typing import List, Mapping

from task_burrito import app, exporter, parser, utils


def main():
    """
    Parses the input file and dispatches to the chosen exporter.
    """
    args = sys.argv[1:]
    input_file = sys.argv[1]
    out = sys.argv[2]
    configs = app.build_config_map(sys.argv[3:])

    warning_buffer = StringIO()
    error_buffer = StringIO()
    output_buffer = StringIO()

    if "-h" in args or "--help" in args:
        print(__doc__, file=error_buffer)
    else:
        try:
            logger = utils.Logger(warning_buffer, output_buffer)

            if input_file == "-":
                in_fobj = sys.stdin
            else:
                in_fobj = open(input_file)

            tasks = parser.parse_file(in_fobj, logger)
            if not tasks:
                print("Task file cannot be empty", file=error_buffer)
            else:
                task_map = utils.verify_task_tree(tasks)
                utils.resolve_task_defaults(task_map)

                is_html_export = out in {"simple", "calendar", "full"}
                if is_html_export:
                    try:
                        include_summary = int(configs.get("summary", "1")) == 1

                        include_toc = out in {"simple", "full"}
                        include_calendar = out in {"calendar", "full"}
                        exporter.export_html_report(
                            task_map,
                            output_buffer,
                            include_toc,
                            include_calendar,
                            include_summary,
                        )
                    except ValueError:
                        print(
                            "Invalid value for summary config, must be 1 or 0",
                            file=error_buffer,
                        )
                elif out == "plain":
                    exporter.plain_exporter(tasks, output_buffer)
                else:
                    print("Unknown exporter:", out, file=error_buffer)

        except IndexError:
            print(
                "Usage: burrito INPUT-FILE EXPORTER [property=value]...",
                file=error_buffer,
            )
        except SyntaxError as err:
            print(err.args[0], file=error_buffer)

    error_text = error_buffer.getvalue()
    warning_text = warning_buffer.getvalue()
    output_text = output_buffer.getvalue()

    if error_text:
        print("HTTP/1.0 200 OK")
        print("Content-Type: text/plain")
        print()
        print(error_text)
    else:
        print("HTTP/1.0 200 OK")
        print("Content-Type: text/html")
        print()

        if warning_text:
            output_text = output_text.replace(
                "</body>",
                "<hr><h1>Warnings</h1><pre>{}</pre></body>".format(
                    html.escape(warning_text)
                ),
            )

        print(output_text)
