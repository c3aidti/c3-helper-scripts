import requests
import argparse
import os
import sys

# Definition of Argument parser
parser = argparse.ArgumentParser('helper function to post data to a c3 tag')
parser.add_argument('--file', help='The file to send', type=str, required=True)
parser.add_argument('--vanity-url', help='The vanity url to use', type=str, required=True)
parser.add_argument('--tenant', help='The tenant to use', type=str, required=True)
parser.add_argument('--tag', help='The tag to use', type=str, required=True)
parser.add_argument('--api-endpoint', help='The API endpoint to upload data to', type=str, required=True)
parser.add_argument('--auth-token', help='The authorization token to use. Generated with Authenticator.generateC3AuthToken()', type=str, required=True)

# Parse Argument
args = parser.parse_args()

file_path = args.file

# User input validation
if not os.path.exists(file_path):
    raise RuntimeError(f"File to send {file_path} doesn't exist!")

# Build full URL
full_url = '/'.join([
    args.vanity_url,
    'import',
    '1',
    args.tenant,
    args.tag,
    args.api_endpoint])

print(f"Sending data to {full_url}")

headers = {}

# Auth token
headers['Content-Type'] = 'text/csv'
headers['Authorization'] = args.auth_token

# From https://stackoverflow.com/questions/13909900/progress-of-python-requests-post
class upload_in_chunks(object):
    def __init__(self, filename, chunksize=1 << 13):
        self.filename = filename
        self.chunksize = chunksize
        self.totalsize = os.path.getsize(filename)
        self.readsofar = 0

    def __iter__(self):
        with open(self.filename, 'rb') as file:
            while True:
                data = file.read(self.chunksize)
                if not data:
                    sys.stderr.write("\n")
                    break
                self.readsofar += len(data)
                percent = self.readsofar * 1e2 / self.totalsize
                sys.stderr.write("\r{percent:3.0f}%".format(percent=percent))
                yield data

    def __len__(self):
        return self.totalsize

# Also from https://stackoverflow.com/questions/13909900/progress-of-python-requests-post
class IterableToFileAdapter(object):
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.length = len(iterable)

    def read(self, size=-1): # TBD: add buffer for `len(data) > size` case
        return next(self.iterator, b'')

    def __len__(self):
        return self.length

file_it = upload_in_chunks(file_path, 125)
r = requests.put(full_url,
                  data=IterableToFileAdapter(file_it),
                  headers=headers)

print(r.status_code)
