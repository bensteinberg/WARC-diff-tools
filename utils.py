import os
import re
import urlparse
import warc
from httplib import HTTPResponse
from StringIO import StringIO
from bs4 import BeautifulSoup
import zlib
import minhash
import simhash

class FakeSocket():
    def __init__(self, response_str):
        self._file = StringIO(response_str)
    def makefile(self, *args, **kwargs):
        return self._file

def html_to_text(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    [s.extract() for s in soup('script')]
    return soup.body.getText()

def is_minified(script):
    """
    !!! HACKY APPROXIMATION !!!
    - if has high line count and low char count
      and if includes newlines, tabs, returns, and more than two spaces,
    in second half of script (allowing for copyright notices / authoring comments)
    not likely to be minified
    - for js if params have chars with length > 3, not likely to be minified
    """
    high_char_count = False
    halved_script = script[len(script)/2:]
    whitespaces_found = len(re.compile('\n|\t|\r|\s{2}').findall(halved_script)) > 2

    lines = script.split('\n')
    low_line_count = len(lines) < 500

    for line in lines:
        if len(line) > 500:
            high_char_count = True
            break

    try:
        params_found = re.compile('function\s+\w+\(\w{3,}').search(halved_script).group()
    except AttributeError:
        params_found = False

    return params_found or not whitespaces_found or (low_line_count and high_char_count)

def get_simhash_distance(str1, str2):
    try:
        res = simhash.Simhash(str1).distance(simhash.Simhash(str2))
    except:
        res = None
        pass
    finally:
        return res

def get_minhash(str1, str2):
    return minhash.calculate(str1, str2)

def get_combined_distance(str1, str2):
    return

def decompress_payload(payload):
    try:
        source = FakeSocket(payload)
        res = HTTPResponse(source)
        res.begin()
        result = zlib.decompress(res.read(), 16+zlib.MAX_WBITS)
    except Exception as e:
        result = payload
        # try:
        #     result = '.'.join(str(ord(c)) for c in payload)
        # except:
        #     result = payload
    return result

def sort_resources(warc1_expanded, warc2_expanded):
    """
    sorting dictionaries of collections into:
        - missing (no longer available)
        - added (newly added since first capture)
        - modified (common resources that whose hashes are unequal)
        - unchanged
    """

    missing, added, modified, unchanged = dict(), dict(), dict(), dict()

    for key in warc1_expanded.keys():
        if key not in warc2_expanded.keys():
            missing[key] = set(warc1_expanded[key])
        else:
            set_a = set(warc1_expanded[key])
            set_b = set(warc2_expanded[key])

            common = list(set_a & set_b)

            missing[key] = list(set_a - set_b)
            added[key] = list(set_b - set_a)

            if len(missing[key]) == 0:
                missing.pop('key', None)

            if len(added[key]) == 0:
                missing.pop('key', None)

            for url in common:
                hashes_are_equal = warc1_expanded[key][url]['hash'] == warc2_expanded[key][url]['hash']
                if hashes_are_equal:
                    if key in unchanged:
                        unchanged[key].append(url)
                    else:
                        unchanged[key] = [url]
                else:
                    if key in modified:
                        modified[key].append(url)
                    else:
                        modified[key] = [url]

    return missing, added, modified, unchanged

def get_payload_headers(payload):
    """
    return resource's recorded header
    """
    header_dict = dict()
    headers = payload.split('\r\n\r\n')[0].split('\n')
    for head in headers:
        if ":" in head:
            key,val = head.split(": ",1)
            header_dict[key] = val
    return header_dict

def expand_warc(warc_path):
    """
    expand warcs into dicts with compressed responses
    organized by content type
    Each response obj consists of compressed payload and SHA1
    """
    warc_open = warc.open(warc_path)
    responses = dict()
    for record in warc_open:
        if record.type != 'response':
            continue

        payload = record.payload.read()
        headers = get_payload_headers(payload)
        try:
            content_type = format_content_type(headers['Content-Type'])
        except KeyError:
            # HACK: figure out a better solution for unknown content types
            content_type = "unknown"

        new_record =  {
            'payload' : payload,
            'hash': record.header.get('warc-payload-digest'),
        }

        if content_type in responses:
            responses[content_type][record.url] = new_record
        else:
            responses[content_type] = { record.url: new_record }

    return responses

def find_resource_by_url(urlpath, expanded_warc):
    """
    returns { "payload": compressed_payload, "hash":"sha1" }
    """
    for content_type in expanded_warc:
        urls = expanded_warc[content_type].keys()
        if urlpath in urls:
            return expanded_warc[content_type][urlpath]

def format_content_type(content_type):
    """
    removes parameter and whitespaces
    should only return type/subtype
    e.g. 'text/html' and 'application/javascript'
    """
    rx = re.compile('\n|\t|\r')
    return rx.sub('', content_type).split(';')[0]
