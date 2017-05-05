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

def is_unminified(script_str, type_of_script):
    """
        if includes newlines, tabs, returns, and more than two spaces,
        not likely to be minified
    """
    whitespaces_found = len(re.compile('\n|\t|\r|\s{2}').findall(script_str)) > 1

    if type_of_script == "css":
        return whitespaces_found

    elif type_of_script == "js":
        # minifiers reduce params to single letters
        try:
            params_found = re.compile('function\s+\w+\(\w{3,}').search(script_str).group()
        except:
            params_found = None

        if params_found:
            return True

        return whitespaces_found

def get_comparison(str_one, str_two, algorithm="simhash"):
    rx = re.compile('\n|\t|\r|\s{2}')
    cleaned_one = rx.sub(' ', str_one)
    cleaned_two = rx.sub(' ', str_two)

    if algorithm == "simhash":
        return get_simhash_distance(str_one, str_two)
    elif algorithm == "minhash":
        return minhash.get_minhash(cleaned_one, cleaned_two)
    elif algorithm == "mix":
        get_combined_distance(str_one, str_one)

def get_simhash_distance(str_one, str_two):
    try:
        res = simhash.Simhash(str_one).distance(simhash.Simhash(str_two))
    except:
        res = None
        pass
    finally:
        return res


def get_combined_distance(str_one, str_two):
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

def sort_resources(warc_one_expanded, warc_two_expanded):
    """
    sorting dictionaries of collections into:
        - missing (no longer available),
        - added (newly added since first capture), and
        - common (seen in both)
    """

    missing_resources, added_resources, common_resources = dict(), dict(), dict()

    for key in warc_one_expanded.keys():
        set_a = set(warc_one_expanded[key])
        set_b = set(warc_two_expanded[key])
        common_resources[key] = list(set_a & set_b)
        missing_resources[key] = list(set_a - set_b)
        added_resources[key] = list(set_b - set_a)

    return missing_resources, added_resources, common_resources

def get_payload_headers(payload):
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
    """
    warc_open = warc.open(warc_path)
    responses = dict()
    for record in warc_open:
        if record.type == 'response':
            payload = record.payload.read()
            headers = get_payload_headers(payload)
            content_type = headers['Content-Type']
            """
                Each record consists of compressed payload and SHA1
            """
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
    for content_type in expanded_warc:
        if urlpath in expanded_warc[content_type]:
            return expanded_warc[content_type][urlpath]