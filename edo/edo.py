# Builtin
import os
import sys
import glob
import pdfminer
import hashlib
import json
import shutil
from io import StringIO



class EDOCache():
    def __init__(self):
        # if the cache file does not exist, create it
        self.lock = None
        self.lock_location = os.path.realpath(os.path.expanduser('~/.edo/edo.lck'))
        self.cache_location = os.path.realpath(os.path.expanduser('~/.edo/edo.dat'))

        if not os.path.exists(self.cache_location):
            os.makedirs(os.path.dirname(self.cache_location), exist_ok=True)
            self.write_cache({})

        return

    def acquire_cache_lock(self):

        if self.lock != None:
            raise Exception('Lock already acquired!')

        if os.path.exists(self.lock_location):
            raise Exception('Could not acquire lock!')

        self.lock = open(self.lock_location, 'w')
        return

    def release_lock(self):

        if self.lock == None:
            raise Exception('No lock acquired!')

        if not os.path.exists(self.lock_location):
            raise Exception('Error verifying lock!')

        self.lock.close()
        os.remove(self.lock_location)
        self.lock = None

        return

    def write_cache(self, obj):
        data = json.dumps(obj).encode()

        self.acquire_cache_lock()
        with open(self.cache_location, 'wb') as f:
            f.write(data)
        self.release_lock()

        return

    def load_cache(self):
        
        self.acquire_cache_lock()
        with open(self.cache_location, 'rb') as f:
            data = f.read()
        self.release_lock()   

        obj = json.loads(data.decode())
        return obj


def format(mystr):
    return mystr.replace('\n', ' ').replace('  ', ' ').strip()




def hash_file(fpath):
    with open(fpath, 'rb') as f:
        document_data = f.read()
    m = hashlib.sha256()
    m.update(document_data)
    return m.hexdigest()


def process_dir(target_dir):

    cache = EDOCache()
    master_file_dict = cache.load_cache()

    retval = glob.glob(os.path.join(target_dir, '**/*.pdf'), recursive=True)

    for val in retval:

        hash = hash_file(val)
        if hash in master_file_dict:
            continue

        try:
            metadata, subdata = process_file(val)
            master_file_dict[hash] = {
                'metadata' : metadata,
                'subdata' : subdata,
                'path' : val,
                }

            cache.write_cache(master_file_dict)
        except:
            print(f'failed to process file {val}')

    return


def bad_ratio_comparison(tstring, substring):
    if substring in tstring:
        return 1.0
    elif substring.replace(' ', '') in tstring.replace(' ', ''):
        return 0.5
    else:
        return 0.0


def query_cache(query, max_results=10):

    cache = EDOCache()
    master_file_dict = cache.load_cache()

    results = []

    for key, value in master_file_dict.items():
        compare_list = list(value['metadata'].values()) + list(value['subdata'].values())
        scores = [ (bad_ratio_comparison(i.lower(), query.lower()), i.lower()) for i in compare_list ]
        highest_match = max(scores,key=lambda x: x[0])

        result = (value['path'], highest_match[0], highest_match[1])
        results.append(result)
        results.sort(key = lambda x : x[1], reverse=True)
        results = results[:max_results]

    return results

def main():
    import argparse
    parser = argparse.ArgumentParser(description='')
    subparsers = parser.add_subparsers(help='sub-command help', dest="command")

    parser_scan = subparsers.add_parser('scan', help='Scan a subdirectory and cache the results')
    parser_scan.add_argument('subdir', help='The subdirectory to scan')

    parser_search = subparsers.add_parser('search', help='Search cached results for relavent files')
    parser_search.add_argument('query', help='The query to search')

    parser_server = subparsers.add_parser('server', help='Host the server interface.')

    args = parser.parse_args()

    if args.command == 'scan':
        process_dir(args.subdir)
    elif args.command == 'search':
        query_cache(args.query)
    elif args.command == 'server':
        from edo.server import app
        app.run()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
