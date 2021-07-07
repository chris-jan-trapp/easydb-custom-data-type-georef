DEFAULT_SEPARATOR = "/"


class Path:
    def __init__(self, path, separator):
        if not isinstance(path, (str, list)):
            raise ValueError("Illegal path type: " + str(type(path)))
        if isinstance(path, str):
            path = path.split(separator)
        



def get(d, path, separator=DEFAULT_SEPARATOR):
