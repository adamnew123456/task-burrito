# What is this?

**Task Burrito** is a personal project manager based on plain-text. It focuses
on generating useful reports while leaving the details of task manipulation to
your text editor.

# Input Format

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
  that the task has not been started yet. All of these are case-sensitive.
  
- *priority* is a number from 1 to 5. Lower values are considered to be higher
  priority.
  
- *deadline* is a date in the format YYYY-MM-DD indicating what date the task is
  required to be done by.
  
- *depends* is a space-separated list of task identifiers which refer to tasks
  that that must be finished before this task can complete.
  
Note that the *deadline* and *priority* values are optional, and if not provided
are inherited from the parent task (or its parent task, and so on). *depends* is
also optional and if not included the task does not depend upon any others.
  
Everything after the front block is plain Markdown and are considered the notes
for this task. The only special aspect is that Task Burrito will arrange for
anchor links to each task by its identifier:

```markdown
---
...
---

I am related to the [timeout settings docs](#1.1.2)
```

Task Burrito files are just a sequence of these tasks, sorted by the task
identifier.

# Exporters

Once you have a Task Burrito file, you can export it into one of a few different
export formats:

- A **calendar** view which shows tasks according to the dates when they're due.
  
- A **simple** view which renders the file to HTML and adds a table of contents

- A **plain** view which parses the file and re-assembles it for printing
