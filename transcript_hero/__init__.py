import types
import os


def parse_config(filename):
    """
    Taken from Flask
    """
    root_path = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(root_path, filename)
    config = {}
    d = types.ModuleType('config')
    d.__file__ = filename
    try:
        with open(filename, mode='rb') as config_file:
            exec(compile(config_file.read(), filename, 'exec'), d.__dict__)
    except IOError as e:
        e.strerror = 'Unable to load configuration file (%s)' % e.strerror
        raise

    for key in dir(d):
        if key.isupper():
            config[key] = getattr(d, key)
    return config
