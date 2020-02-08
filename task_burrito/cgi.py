"""
Usage: burrito-cgi INPUT-FILE EXPORTER [PROPERTY=VALUE]...

Arguments:

- INPUT-FILE: The path to a Markdown file with Task Burrito anntoations.

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
import html
from io import StringIO
import os
import sys

from task_burrito import app, exporter, parser, utils


def main():
    """
    Parses the input file and dispatches to the chosen exporter.
    """
    args = sys.argv[1:]
    input_file = sys.argv[1]
    out = sys.argv[2]

    warning_buffer = StringIO()
    error_buffer = StringIO()
    output_buffer = StringIO()

    error = False
    try:
        configs = app.build_config_map(sys.argv[3:])
    except ValueError as err:
        print(str(err), file=error_buffer)
        error = True

    if "-h" in args or "--help" in args:
        print(__doc__, file=error_buffer)
    elif not error:
        try:
            logger = utils.Logger(warning_buffer, output_buffer)
            base_path = os.path.dirname(os.path.abspath(input_file))
            in_fobj = open(input_file)

            tasks = parser.parse_file(in_fobj, base_path, logger)
            if not tasks:
                print("Task file cannot be empty", file=error_buffer)
            else:
                task_map = utils.verify_task_tree(tasks)
                utils.resolve_task_defaults(task_map)

                is_html_export = out in {"simple", "calendar", "full"}
                if is_html_export:
                    configs.include_toc = out in {"simple", "full"}
                    configs.include_calendar = out in {"calendar", "full"}
                    configs.head_prefix = '<meta http-equiv="refresh" content="5">'
                    configs.body_suffix = "%WARNING%"
                    exporter.export_html_report(task_map, output_buffer, configs)
                elif out == "plain":
                    print("plain exporter not supported in CGI mode", file=error_buffer)
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
                "%WARNING%",
                "<hr><h1>Warnings</h1><pre>{}</pre></body>".format(
                    html.escape(warning_text)
                ),
            )
        else:
            output_text = output_text.replace("%WARNING%", "")

        print(output_text)
