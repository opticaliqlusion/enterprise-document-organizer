# enterprise-document-organizer
A rudimentary document scraper and organizer

This simple script is meant to copy files of interest from one media to another, with intention of centralizing files and directories of interest.

Usage:

```
$> python .\main.py --help
usage: main.py [-h] {scan,merge} ...

Process some integers.

positional arguments:
  {scan,merge}  sub-command help
    scan        Scan a directory, volume, etc. and summarize its contents
    merge       Merge a source manifest into a destination manifest

optional arguments:
```

Example:

```
python main.py scan E:\test-scan-root docs-backup --file-filters *.pdf *.doc *.docx --special-dir-globs *.vsproj *.vcxproj
```

Requirements:
* Python 3.6+
* `pip install -r requirements.txt`

