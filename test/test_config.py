import pytest
import typing
from ..configurator import (
    BaseConfig,
    Config,
    DEFAULT_SECRET_FILE,
    DEFAULT_CFG_FILE,
    DATA_PATH,
)
from pathlib import Path


def test_init():
    cfg = Config()
    cfg.prune()
    cfg.load(load_path="test/cfg.toml")
    assert cfg.build.type == "Debug"
    assert cfg.project.name == "Configurator test"
    assert cfg.project.dependencies.python == "^3.9"
    assert cfg.generator.exclude == [".git", "assets"]
    assert cfg.build.output.type == "exec"
    assert cfg.project.test.third_level.number == 10


def test_restore():
    cfg = Config()
    cfg.load(load_path="test/cfg.toml")
    cfg.save(save_path=DEFAULT_CFG_FILE, key_path=DEFAULT_SECRET_FILE)
    cfg.restore()
    assert DEFAULT_SECRET_FILE.exists()
    assert DEFAULT_CFG_FILE.exists()
    assert cfg.project
    assert cfg.project.name == "Configurator test"
    assert cfg.build.output.type == "exec"


def test_update():
    cfg = Config(load_path="test/cfg.toml")
    ver = "1.0.0"
    cfg.project.update(version=ver)
    cfg.project.update({"foo": "bar"}, baz="fee")
    assert cfg.project.version == "1.0.0"
    assert cfg.project.foo == "bar"
    assert cfg.project.baz == "fee"


def test_store_path():
    new_path = DATA_PATH.joinpath("test/config")
    cfg = Config(load_path="test/cfg.toml", save_path=new_path)
    cfg.save()
    assert new_path.exists()
    cfg.prune()
    assert not new_path.exists()


def test_prune():
    cfg = Config()
    cfg.prune()
    assert not DEFAULT_SECRET_FILE.exists()
    assert not DEFAULT_CFG_FILE.exists()


def test_save_update_restore():
    cfg = Config()
    cfg.prune()

    cfg.update({"key": "value"})

    new_type = type("Type_attr", (BaseConfig,), {})
    cfg.update({"type_attr": new_type()})
    assert cfg.type_attr
    cfg.type_attr.update(sub_attr="sub_attr_value")
    assert cfg.type_attr.sub_attr

    cfg.save()

    del cfg

    new_cfg = Config()
    new_cfg.restore()
    assert new_cfg.key == "value"
    assert new_cfg.type_attr.sub_attr


def test_add_cls_attr():
    cfg = Config(restore=True)
    cfg.add_cls_attr("class_attr")
    assert cfg.class_attr
    assert isinstance(cfg.class_attr, BaseConfig)
    cfg.class_attr.add_cls_attr("sub_attr", {"key": "value"})
    assert cfg.class_attr.sub_attr
    assert isinstance(cfg.class_attr.sub_attr, BaseConfig)
    assert cfg.class_attr.sub_attr.key == "value"


def test_has_attr():
    cfg = Config()
    cfg.prune()
    cfg.load("test/cfg.toml")
    cfg.save()
    assert not hasattr(cfg, "test")
    cfg.update(attr="attrval")
    assert hasattr(cfg, "attr")
    cfg.add_cls_attr("test_has_attr")
    assert hasattr(cfg, "test_has_attr")
