import importlib
import inspect
import os

from .ZodiacSource import ZodiacSource


def is_zodiacsource(o):
    return inspect.isclass(o) and issubclass(o, ZodiacSource) and o != ZodiacSource


# Generate sources from content of the sources folder
source_classes: list[ZodiacSource] = []
dirname = os.path.dirname(os.path.abspath(__file__))
for file in os.listdir(dirname):
    if (
        file != "__init__.py"
        and os.path.isfile("%s/%s" % (dirname, file))
        and file[-3:] == ".py"
    ):
        module = importlib.import_module(f".{file[:-3]}", __name__)
        members = [
            cls[1] for cls in inspect.getmembers(module, predicate=is_zodiacsource)
        ]
        if members:
            source_classes += members

# Dictionary of source names and the class
sources: dict[str, ZodiacSource] = {cls.name: cls for cls in source_classes}
