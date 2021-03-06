import os
import re
import tempfile
from urllib.parse import urlparse
import tempfile
from datetime import datetime

from django.core import serializers
from django.conf import settings


def format_date_for_memento(date_string):
    d = datetime.strptime(date_string, '%Y-%m-%d')
    return d.strftime('%Y%m%d')


def get_full_warc_path(archive_dirname):
    """
    Takes named archive dir (should consist of timestamp_submitted_url)
    Returns full path to warc (should have a single warc per directory)
    """
    full_archive_parent_path = settings.COLLECTIONS_DIR + "/" + archive_dirname + "/archive"
    assert os.path.exists(full_archive_parent_path)
    warc_name = os.listdir(full_archive_parent_path)[0]
    assert "warc.gz" in warc_name
    warc_path = full_archive_parent_path + '/' + warc_name
    assert os.path.exists(warc_path)
    return warc_path


def write_to_static(new_string, filename, compare_id=None):
    dirpath = create_compare_dir(str(compare_id))
    filepath = os.path.join(dirpath, filename)
    with open(filepath, 'w+') as f:
        f.write(new_string)

    print("wrote %s to static: %s" % (filename, filepath))


def create_compare_dir(compare_id):
    dirpath = os.path.join(settings.STATIC_DIR, compare_id)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    return dirpath


def get_compare_dir_path(compare_id):
    return os.path.join(settings.STATIC_DIR, compare_id)


def write_to_temp_file(content):
    f = tempfile.NamedTemporaryFile(delete=False)
    if type(content) is bytes:
        f.write(content)
    else:
        content = bytes(content, 'utf-8')
        f.write(content)
    return f.name


def serialize_model(model):
    return serializers.serialize('json', [model, ])


def shorten_url(url):
    parsed = urlparse(url)

    if len(parsed.path) > 30:
        return "%s%s...%s" % (parsed.netloc, parsed.path[0:10], parsed.path[-10:])
    else:
        return url

