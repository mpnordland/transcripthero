import os
from flask_uploads import UploadSet, IMAGES, configure_uploads

signatures = UploadSet('signatures', IMAGES)


def get_stream_size(stream):
    current_pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    file_size = stream.tell()
    stream.seek(current_pos, os.SEEK_SET)
    return file_size


def setup_uploads(app):
    signatures.default_dest = lambda _: os.path.join(
        app.instance_path, "signature_images")
    configure_uploads(app, signatures)
