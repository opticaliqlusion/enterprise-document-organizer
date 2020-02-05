import os
import sys
import time
import queue
import hashlib
import threading
import mimetypes
import progressbar
import re
import warnings
import datetime
import json
import shutil
import errno
import glob

from os.path import split, join, splitdrive
import posixpath


def sha256_file(fname):
    hash_sha = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha.update(chunk)
    return hash_sha.hexdigest()


def sha256_data(fdata):
    hash_sha = hashlib.sha256()
    hash_sha.update(fdata)
    return hash_sha.hexdigest()


def glob2re(pat):
    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            #res = res + '.*'
            res = res + '[^/]*'
        elif c == '?':
            #res = res + '.'
            res = res + '[^/]'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\','\\\\')
                i = j+1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)
    return res + '\Z(?ms)'


def glob_filter(names,pat):
    return (name for name in names if re.match(glob2re(pat),name))


# recursively scan directory
def scantree(path):
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from scantree(entry.path)
        else:
            yield entry


top_level_globs = [
    '*.vsproj',      # recursively scan directory, with a twist
    '*.vcxproj',     # sometimes we want to grab not just files, but directory trees
    '*.vmx',         # imagine scanning for .vmx files. the files themselves arent all
    '__init__.py',   # that useful, you need the directory that contains them.
    'README.md',             
]
def scantree_with_directory_escape(path, directory_escape_globs=top_level_globs, file_filters=tuple()):
    for entry in os.scandir(path):
        if entry.is_dir():
            # check to see if this is a "special" directory, if so, just return the path so we can shutil.copytree
            # otherwise, recurse
            if any(glob.glob(os.path.join(entry.path, pattern)) for pattern in directory_escape_globs):
                yield entry
            else:
                yield from scantree_with_directory_escape(entry.path, directory_escape_globs=directory_escape_globs, file_filters=file_filters)
        else:
            # check to see if this is a file type we're interested in
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore",category=DeprecationWarning)
                if file_filters and not any(re.match(glob2re(pattern), entry.name) for pattern in file_filters):
                    continue
                else:
                    yield entry

def get_drive_id(path):
    drive_letter = os.path.splitdrive(path)[0]
    if drive_letter:
        vsn = os.stat(drive_letter).st_dev
        result = '{:04X}-{:04X}'.format(vsn >> 16, vsn & 0xffff)
    else:
        result = None
    return result


# generate a path from a timestamp and a filename
# in the form YY/MM/filename
def get_normalized_file_path(timestamp, filename):
    dt = datetime.datetime.fromtimestamp(timestamp)
    normpath = os.path.join(
        '{:02d}'.format(dt.year),
        '{:02d}'.format(dt.month),
        filename)
    return normpath


def load_manifest_from_file(fpath):
    with open(fpath, 'r') as f:
        manifest_data = f.read()
        return json.loads(manifest_data)


def copyanything(src, dst):
    try:
        shutil.copytree(src, dst)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dst)
        else: raise

# recursively scan a root directory, eventually creating a manifest of
# the files discovered. Optionally, pass in a filter to only scan
# certain files.
def scan_to_file(rel_root_dir, out_directory, filters=tuple(), nthreads=4):

    # we're gonna use threading to copy files
    copy_queue = queue.Queue()

    # first, prep the out_directory
    if os.path.isfile(out_directory):
        raise Exception('Target directory may not be a file.')

    manifest_location = os.path.join(out_directory, 'manifest.json')

    # first, check to see if the file exists  and load it
    if os.path.exists(manifest_location):
        result = load_manifest_from_file(manifest_location)
    else:
        result = {
            'media' : [],
            'contents' : {},
        }

    # calculate what we're actually scanning
    root_dir = os.path.abspath(rel_root_dir)
    source_media = get_drive_id(root_dir)

    # record the media we scanned
    if source_media not in result['media']:
        result['media'].append(source_media)

    print('=== Part One: Scan Dirs ===')

    # now record all the files we found
    for entry in scantree_with_directory_escape(root_dir, file_filters=filters):

        # normalize the path and introduce the unique drive name
        npath = (splitdrive(entry.path)[1]).replace(os.sep, posixpath.sep)
        path_key = posixpath.join('/', source_media, *npath.split('/'))
        stat = entry.stat()

        # calculate the output path
        norm_path = get_normalized_file_path(stat.st_ctime, entry.name)
        out_path = os.path.join(out_directory, norm_path)

        # fast fail if we've hashed this file before
        # @TODO should we create a softlink if it's created with a different timestamp someplace else?
        if entry.is_file():
            file_data = open(entry.path, 'rb').read()
            key = sha256_data(file_data)
        else:
            # @TODO find a better way to key directories
            key = sha256_data(bytes(norm_path.encode()))

        if key in result['contents']:
            continue

        # a small struct describing the file's metadata
        result['contents'][key] = {
            'stat'            : stat,
            'normalized_path' : path_key,
            'source_media'    : source_media,
        }

        if not os.path.exists(os.path.dirname(out_path)):
            try:
                os.makedirs(os.path.dirname(out_path))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

        #copyanything(entry.path, out_path)
        copy_queue.put((entry.path, out_path))

    print('=== Part Two: Copy Files ===')
    def fn_threadproc(in_queue):
        while True:
            try:
                src, dst = in_queue.get(block=False)
                copyanything(src, dst)
            except queue.Empty:
                break
        return

    total = copy_queue.qsize()
    threads = []
    for i in range(nthreads):
        thread = threading.Thread(target=fn_threadproc, args=[copy_queue])
        threads.append(thread)
        thread.start()

    bar = progressbar.ProgressBar(maxval=total).start()
    while copy_queue.qsize() > 0:
        bar.update(total - copy_queue.qsize())
        time.sleep(0.2)
    bar.finish()

    for i in range(nthreads):
        threads[i].join()

    # once we're done, write out the manifest of what we found
    with open(manifest_location, 'w') as f:
        f.write(json.dumps(result))

    return


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Process some integers.')
    subparsers = parser.add_subparsers(help='sub-command help', dest='mode')

    parser_scan = subparsers.add_parser('scan', help='Scan a directory, volume, etc. and summarize its contents')
    parser_scan.add_argument('-j', '--num_threads', type=int, default=4, help='Number of threads to use to copy.')
    parser_scan.add_argument('mount_point', help='The mount point to scan. The root of the search for the application.')
    parser_scan.add_argument('output', help='The output manifest to create')
    parser_scan.add_argument('filters', nargs='*', help='A list of file globs to scan, using standard globing syntax.')

    parser_scan = subparsers.add_parser('merge', help='Merge a source manifest into a destination manifest')
    parser_scan.add_argument('src', help='The source manifest to read from.')
    parser_scan.add_argument('dst', help='The destination manifest to merge into. This manifest is modified.')

    args = parser.parse_args()

    if args.mode == 'scan':
        scan_to_file(args.mount_point, args.output, filters=tuple(args.filters), nthreads=args.num_threads)
    else:
        raise NotImplemented('Mode not recognized: {}'.format(args.mode))
