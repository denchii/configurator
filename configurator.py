"""Universal configurator. 

Allows the custom project to have configuration written in TOML or
JSON file and easily be converted to the class with same hierarchy
of values.
"""
import json
import pytomlpp
import libnacl.secret as crypter
from pathlib import Path
from libnacl.utils import load_key
from typing import Union, Any, Tuple, Callable, Iterator, Iterable, Type
from functools import update_wrapper
from inspect import getmembers, isroutine

DATA_PATH = Path.home().joinpath(".everynet/")
DEFAULT_SECRET_FILE = DATA_PATH.joinpath("secret.key")
DEFAULT_CFG_FILE = DATA_PATH.joinpath("config")
RESERVED = ["name"]


class BaseObject(object):
    def __init__(self, **kwargs) -> None:

        super().__init__()
        self.update(**kwargs)

    @classmethod
    def update(cls, __d: dict = {}, **kwargs) -> None:
        if __d and kwargs:
            data = dict(__d).update(**kwargs)
        else:
            data = __d or kwargs
        for k, v in data.items():
            if "path" in k:
                v = Path(v).expanduser().resolve().as_posix()
            setattr(cls, k, v)


class MapDecoder(json.JSONDecoder):
    def __init__(
        self,
        bases: Tuple = (BaseObject,),
        processor: Callable = (lambda k, v: v),
        **kwargs,
    ):
        """JSONDecoder extend class.

        Recursivelly converts dictionaries to objects which attributes are
        key=value pairs. Keeps nesting - each subdictionary creates 'type'
        object and became attribute of the parent object.

        Attributes:

        bases: Tuple of base classes for type() method.
        processor: Callback to process values before attaching it to class.
        For example, it could be used to convert string path to pathlib.Path().


        """

        self.bases = bases
        self.processor = processor
        json.JSONDecoder.__init__(self, object_hook=self._object_hook, **kwargs)

    def pack_dict(self, __d: dict = {}, parent: str = "") -> Type:
        """Recursively walk thru incoming dict and convert all dict values
        to type() object adding them to parent type as attributes

        Aargs:

        __d (dict): dict to parse
        parent (str): parent key value in case of recursion

        Returns:
            dict: {parent: type(...)} if arent is given or just type()
        """

        attrs = {}
        for k, v in __d.items():
            if isinstance(v, dict):
                v = self.pack_dict(v, parent=k)
            vv = self.processor(k, v) or v
            attrs.update({k: vv})
        new_class = type(parent.capitalize(), self.bases, attrs)
        return new_class()

    def _object_hook(self, dct):
        """Callback that invoked on every object (actually dict) found in
        decoded text

        Args:
            dct (dict): dict object

        Returns:
            dict: dict where values that are also dicts converted to
            type() objects.
        """
        rv = {}
        for k, v in dct.items():
            if isinstance(v, dict):
                v = self.pack_dict(v, parent=k)
            rv.update({k: v})
        return rv

    @staticmethod
    def list_generator(indict: dict, pre=None):
        """Generator, recursivelly converts dict to table(list of lists)
        where every line is a [parent, parent, parent, ..., key-value]

        Args:
            indict (dict):  to convert
            pre ([type], optional): [description]. Defaults to None.

        Yields:
            list: table of the dictionary hierarchy
        """
        pre = pre[:] if pre else []
        if isinstance(indict, dict):
            for key, value in indict.items():
                if isinstance(value, dict):
                    for d in MapDecoder.list_generator(value, pre + [key]):
                        yield d
                elif isinstance(value, list) or isinstance(value, tuple):
                    for v in value:
                        for d in MapDecoder.list_generator(v, pre + [key]):
                            yield d
                else:
                    yield pre + [key, value]
        else:
            yield pre + [indict]

    def walk_map(self, __d: dict, output: list, parent: str = "") -> Type:
        for k, v in __d.items():
            if isinstance(v, dict):
                v = self.walk_map(v, output, parent=k)
        new_type = type(parent.capitalize(), self.bases, __d)
        output.append(new_type)
        return new_type

    def type_generator(self, __d: dict) -> Iterable:
        """Iterate over dict recursively and convert inner dicts to type()

        Args:
            __d (dict): to convert

        Returns:
            list of newly created type() objects. It's name will
            be key.capitalize() and value as an attributes
        """
        rv = []
        self.walk_map(__d, rv, "Root")
        yield from rv


class MapEncoder(json.JSONEncoder):
    """json.JSONEncoder extender.

    Recursively scan object replacing classes with dictionary of class
    attributes.
    """

    def process_cls(self, obj):
        """Convert classes in object into dictionary of class attributes.
        Recursive lookup.
        """

        if hasattr(obj, "__dict__"):
            attrs = [
                a
                for a in getmembers(obj, lambda a: not (isroutine(a)))
                if not (a[0].startswith("_") and a[0].endswith("_"))
            ]
            rv = {}
            for k, v in attrs:
                if hasattr(v, "__dict__"):
                    rv[k] = self.process_cls(v)
                else:
                    rv[k] = v
            return rv
        else:
            return str(obj)

    def iterencode(self, o: Any, _one_shot: bool) -> Iterator[str]:
        return super().iterencode(self.process_cls(o), _one_shot=_one_shot)


class ConfigDecoder(MapDecoder):
    def __init__(self):
        """Default base object for config convertion. Converts keys with 'path'
        into 'pathlib.Path' objects"""
        super().__init__(bases=(BaseConfig,), processor=self.process)

    def process(self, key, val):
        if "path" in key:
            return Path(val).expanduser().resolve().as_posix()
        else:
            return val


class BaseConfig(object):
    """Type container. Parent class for config."""

    def update(
        self, data: dict = None, processor_cb: Callable[[str, Any], Any] = None, **kwargs: Any
    ) -> None:
        """Set config instance attributes.

        Must be used instead of set_attr or setattr, because it also
        stores raw data for save - restore.

        Parameters:
        data [dict] Dictionary of attributes {name: value} to be set. Optional,
                    `name=value` could be set as keyword arguments.
                    Defaults to None.
        processor_cb [Callable] value processor callback
        """

        data = dict(data, **kwargs) if data else dict(**kwargs)
        self.set_attr(data, processor_cb)

    @staticmethod
    def convert_path(key: str, val: Any) -> Any:
        """Resolve relative path and exapand user home sign `~`.

        Return:
        str Posix style path
        """

        return Path(val).expanduser().resolve().as_posix() if "path" in key else val

    @staticmethod
    def path_resolve(_d: dict) -> dict:
        """Recursively convert pathes in dict

        Return:
        dict With converted paths
        """

        rv = {}
        for k, v in _d.items():
            if isinstance(v, dict):
                v = BaseConfig.path_resolve(v)
            else:
                v = BaseConfig.convert_path(k, v)
            rv.update({k: v})
        return rv

    def set_attr(self, data: dict = {}, processor_cb: Callable[[str, Any], Any] = None) -> None:
        """Set instance attributes.

        Resolve paths and call `processor_cb` callback function if provided.

        Args:
        data[dict] dictionary of attribute's {name: value}
        processor_cb[Callable] Value processor callback. It's return value will
        be set if method provided.
        """

        for k, v in data.items():
            val = BaseConfig.convert_path(k, v)
            setattr(self, k, processor_cb(k, val) if processor_cb else v)

    def add_cls_attr(self, name: str, attrs: dict = {}) -> None:
        """Create new type and add it's instance as attribute.

        Args:
            name    [str]   Attribute name and class name (capitilized).
            attrs   [dict]  New class atrributes.
        """

        cls_attr = type(name.capitalize(), (BaseConfig,), attrs)
        self.update({name: cls_attr()})


class Config(BaseConfig):
    def __init__(
        self,
        load_path: Union[str, Path] = None,
        save_path: Union[str, Path] = DEFAULT_CFG_FILE,
        key_path: Union[str, Path] = DEFAULT_SECRET_FILE,
        restore: bool = False,
    ) -> None:
        """Project configurator. Parse TOML or JSON file and dynamically creates
        subclasses if needed.

        Args:
            path (Union[str, Path], optional): Path to configuration file.
            Defaults to None.
        """
        super().__init__()
        self._save_path_ = Path(save_path).expanduser().resolve()
        self._key_path_ = Path(key_path).expanduser().resolve()
        if load_path and restore:
            raise ValueError("load_path and restore can't be set simultaneously")

        if load_path:
            self.load(load_path)

        if restore:
            self.restore()

    @property
    def save_path(self):
        return self._save_path_.as_posix()

    @save_path.setter
    def save_path(self, val):
        self._save_path_ = Path(val).expanduser().resolve()

    @property
    def key_path(self):
        return self._key_path_.as_posix()

    @key_path.setter
    def key_path(self, val):
        self._key_path_ = Path(val).expanduser().resolve()

    def load(self, load_path: Union[str, Path]) -> None:
        """Read JSON or TOML file and convert it to the Config attributes.
        Dictionaries are converted to the `type` objects

        Args:
        path - path to the file to read

        Return:
        dict - data loaded with json or pytomlpp modules
        """
        data = {}
        self._save_path_.parent.mkdir(exist_ok=True)
        if p := Path(load_path):
            if p.exists() and p.is_file():
                with open(p, "r") as _file:
                    if p.suffix == ".json":
                        data = json.load(_file)
                    elif p.suffix == ".toml":
                        data = pytomlpp.load(_file)
                    else:
                        raise NotImplementedError("Unknown file type")
                    if raw_dict := BaseConfig.path_resolve(data):
                        self._converted_ = json.loads(json.dumps(raw_dict), cls=ConfigDecoder)
                        self.set_attr(self._converted_)
            else:
                raise FileNotFoundError("Path isn't a file or not exist")

    def save(
        self,
        save_path: Union[str, Path] = None,
        key_path: Union[str, Path] = None,
    ) -> None:
        """Encrypt and write configuration into file at `save_path`.
        Key stored at `key_path`. If save_path provided as argument,
        it will be used instead of value from constructor.

        Args:
        save_path [str, Path]  Path to file where configuration should
                                be written. If no path provided,
                                initialization value will be used
                                (self._save_path_). Defaults to
                                $HOME/.ethingz/config

        Returns:
        (str, str)  Tuple of two strings: actual path to config file,
                    actual path to secret key file.
        """
        data = json.dumps(self, cls=MapEncoder).encode("utf-8")

        if save_path:
            self._save_path_ = Path(save_path).expanduser().resolve()

        if key_path:
            self._key_path_ = Path(key_path).expanduser().resolve()

        encrypted = self._encrypt(data)
        self._save_path_.write_bytes(encrypted)

    def _decrypt(self, path: Path) -> bytes:
        key = load_key(self._key_path_)
        content = self._save_path_.read_bytes()
        return crypter.SecretBox(key.sk).decrypt(content)

    def _encrypt(self, data: Any) -> Any:
        if self._key_path_.exists():
            key = load_key(self._key_path_)
            box = crypter.SecretBox(key.sk)
        else:
            box = crypter.SecretBox()
            box.save(self._key_path_)

        return box.encrypt(data)

    def restore(self) -> None:
        """
        Load and decrypt stored config file using secret key.
        """
        if self._key_path_:
            if self._key_path_.exists() and self._key_path_.is_file():
                decrypted = self._decrypt(self._save_path_)
                self._converted_ = json.loads(decrypted.decode("utf-8"), cls=ConfigDecoder)
                self.set_attr(self._converted_)

    def prune(self):
        """
        Delete stored config and key files.
        """
        self._save_path_.unlink(missing_ok=True)
        self._key_path_.unlink(missing_ok=True)
        self._converted_ = {}

        return True


def configurable(
    f,
    load_path: Union[str, Path] = None,
    save_path: Union[str, Path] = None,
    key_path: Union[str, Path] = None,
) -> Callable[[Config, Any], Any]:
    """
    Decorator to transorm function to receive existed Config() object.
    Arguments are the same as for Config class.
    """
    cli_config = Config(load_path=load_path, save_path=save_path, key_path=key_path)

    def new_func(config: Config, *args, **kwargs):
        return f(cli_config, *args, **kwargs)

    return update_wrapper(new_func, f)
