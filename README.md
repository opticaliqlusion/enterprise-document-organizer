# enterprise-document-organizer
A rudimentary document scraper and organizer

This simple script is meant to copy files of interest from one media to another, with intention of centralizing files and directories of interest.

Usage:

```
$> python main.py --help
usage: main.py [-h] {scan,merge} ...

Process some integers.

positional arguments:
  {scan,merge}  sub-command help
    scan        Scan a directory, volume, etc. and summarize its contents
    merge       Merge a source manifest into a destination manifest

optional arguments:
```

Currently, only `scan` is implemented.

```
python main.py scan --help
usage: main.py scan [-h] [-j NUM_THREADS]
                    [--file-filters FILE_FILTERS [FILE_FILTERS ...]]
                    [--special-dir-globs SPECIAL_DIR_GLOBS [SPECIAL_DIR_GLOBS ...]]
                    mount_point output

positional arguments:
  mount_point           The mount point to scan. The root of the search for
                        the application.
  output                The output manifest to create

optional arguments:
  -h, --help            show this help message and exit
  -j NUM_THREADS, --num_threads NUM_THREADS
                        Number of threads to use to copy.
  --file-filters FILE_FILTERS [FILE_FILTERS ...]
                        A list of file globs to scan, using standard globing
                        syntax.
  --special-dir-globs SPECIAL_DIR_GLOBS [SPECIAL_DIR_GLOBS ...]
                        A list of special file globs to scan at the top level
                        of special directories, using standard globing syntax.
                        Eg *.vcxproj, *.vmx
```

Example:

```
python main.py scan E:\test-scan-root docs-backup --file-filters *.pdf *.doc *.docx --special-dir-globs *.vsproj *.vcxproj
```



Requirements:
* Python 3.6+
* `pip install -r requirements.txt`

