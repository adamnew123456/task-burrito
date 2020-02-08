# What is this?

**Task Burrito** is a personal project manager based on plain-text. It focuses
on generating useful reports while leaving the details of task manipulation to
your text editor.

# Input Format

Task Burrito files a series of task and include blocks.

## Tasks

Task Burrito uses a basic extension to Markdown which adds some metadata similar
to what you would see in Jekyll front-matter. For example, this is a basic task
definition:

```markdown
---
task 1.1.2
label Add documentation page for timeout settings
status DONE
priority 3
deadline 2020-02-01
depends 1.2 1.3.1
---

Include information about the default settings, supported units and edge cases around disabling timeouts.
```

The front block enclosed in three hyphens and contains the basic details of a
task. All of these task options must be at the start of a line and are 
case-sensitive:

- *task* is the task identifier, which is used to refer to the task. Task
  identifiers form a tree, so that task 1.1.2 is the second child of task 1.1
  and a grand-child of task 1.
  
- *label* is the display name of the task that shows up in rendered views. It
  can contain any text except a newline, although leading and trailing
  whitespace is ignored.
  
- *status* may be one of: **DONE** meaning the task is completed, **IN-PROGRESS**
  meaning that the task is being worked on but is not complete, **BLOCKED** meaning
  the task is waiting on one of its dependent tasks to finish and **TODO** meaning
  that the task has not been started yet. All of these are case-insensitive.
  
- *priority* is a number from 1 to 5. Lower values are considered to be higher
  priority.
  
- *deadline* is a date in the format YYYY-MM-DD indicating what date the task is
  required to be done by.
  
- *depends* is a space-separated list of task identifiers which refer to tasks
  that that must be finished before this task can complete.
  
Note that the *deadline* and *priority* values are optional, and if not provided
are inherited from the parent task (or its parent task, and so on). *depends* is
also optional and if not included the task does not depend upon any others.

To prevent this behavior, the special value **none** can be provided for the 
*deadline* or *priority* properties. This disables inheritance from the parent
task for the task and all its children (although they can still set their own
values which follow the rules of inheritance for *their* children).
  
Everything after the front block is plain Markdown and are considered the notes
for this task. The only special aspect is that Task Burrito will arrange for
anchor links to each task by its identifier:

```markdown
---
...
---

I am related to the [timeout settings docs](#1.1.2)
```

## Include Blocks

In addition to the standard task blocks, there is also a special kind of block
which you can use to reference other files. It contains only values (possibly
more than one) for the include property:

```markdown
---
include personal.md
include work.md
---
```

All non-absolute paths in the include block are processed relative to the root file 
given on the command line. The only exception is if standard input is used as 
the input. In that case the base directory is the working directory at the time 
you run `burrito`.

# Exporters

Once you have a Task Burrito file, you can export it into one of a few different
export formats. Each has a list of possible options that can be given to control
its output.

All formats other than plain export to HTML.

## calendar

This builds a calendar from the deadlines of all non-DONE tasks. In addition, it
includes a full listing of each property as well as its notes after the calendar.

Options:

* `summary=0|1` determines whether to include the full property listing. True (1)
  by default.

## simple

This adds a table of contents, where each task is included with a color-coded status
as well as a brief message showing more detailed information. In addition, it 
includes a full listing of each property as well as its notes after the TOC.

Options:

* `summary=0|1` determines whether to include the full property listing. True (1)
  by default.

* `fold=0|1` determines whether to omit a task's sub-tasks from the TOC if all of
  those subtasks are marked as DONE. Note that this does not take into account the
  status of sub-sub tasks so non-DONE tasks may be hidden if their parent is marked
  as DONE.

## full

This combines the calendar and simple formats, listing both a table of contents as
well as a calendar.

Options:

* `summary=0|1` determines whether to include the full property listing. True (1)
  by default.

* `fold=0|1` determines whether to omit a task's sub-tasks from the TOC if all of
  those subtasks are marked as DONE. Note that this does not take into account the
  status of sub-sub tasks so non-DONE tasks may be hidden if their parent is marked
  as DONE.

## plain

This parses and validates the file, and re-assembles it into a single task file with
the same format as the input. It has no extra options.

# Running

Once you have a task file and have chosen an exporter, you can run the `burrito` 
command-line tool. It takes a task file, an exporter name and an optional list
of properties for the exporter. This will write the exported result on stdout.

```sh
burrito tasks.md full
```

In addition, you can also use the CGI wrapper which will render the result
(including any errors of warnings) along with some extra HTML which performs
live reloading. For example:

```sh
mkdir cgi-bin
echo '#!/bin/sh
burrito-cgi ~/tasks.md full' > cgi-bin/view
chmod +x cgi-bin/view
python3 -m http.server --cgi
```
