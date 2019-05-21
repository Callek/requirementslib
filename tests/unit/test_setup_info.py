# -*- coding=utf-8 -*-

import os
import shutil
import sys

import pip_shims.shims
import pytest
import vistir

from requirementslib.models.requirements import Requirement
from requirementslib.models.setup_info import ast_parse_setup_py


@pytest.mark.parametrize(
    "test_artifact",
    [
        {"name": "environ_config", "as_artifact": False},
        {"name": "environ_config", "as_artifact": True},
    ],
    indirect=True,
)
def test_local_req(test_artifact):
    r = Requirement.from_line(test_artifact.as_posix())
    assert r.name == "environ_config"
    setup_dict = r.req.setup_info.as_dict()
    assert sorted(list(setup_dict.get("requires").keys())) == ["attrs"]


@pytest.mark.parametrize(
    "url_line, name, requires",
    [
        [
            "https://github.com/requests/requests/archive/v2.20.1.zip",
            "requests",
            ["urllib3", "chardet", "certifi", "idna"],
        ],
        [
            "https://github.com/dropbox/pyannotate/archive/v1.0.4.zip",
            "pyannotate",
            ["six", "mypy-extensions", "typing"],
        ],
    ],
)
@pytest.mark.needs_internet
def test_remote_req(url_line, name, requires):
    r = Requirement.from_line(url_line)
    assert r.name == name
    setup_dict = r.req.setup_info.as_dict()
    assert sorted(list(setup_dict.get("requires").keys())) == sorted(requires)


def test_no_duplicate_egg_info():
    """When the package has 'src' directory, do not write egg-info in base dir."""
    base_dir = vistir.compat.Path(os.path.abspath(os.getcwd())).as_posix()
    r = Requirement.from_line("-e {}".format(base_dir))
    egg_info_name = "{}.egg-info".format(r.name.replace("-", "_"))
    distinfo_name = "{0}.dist-info".format(r.name.replace("-", "_"))

    def find_metadata(path):
        metadata_names = [
            os.path.join(path, name) for name in (egg_info_name, distinfo_name)
        ]
        if not os.path.isdir(path):
            return None
        pth = next(iter(pth for pth in metadata_names if os.path.isdir(pth)), None)
        if not pth:
            pth = next(
                iter(
                    pth
                    for pth in os.listdir(path)
                    if any(
                        pth.endswith(md_ending)
                        for md_ending in [".egg-info", ".dist-info", ".whl"]
                    )
                ),
                None,
            )
        return pth

    assert not find_metadata(base_dir)
    assert not find_metadata(os.path.join(base_dir, "reqlib-metadata"))
    assert not find_metadata(os.path.join(base_dir, "src", "reqlib-metadata"))
    assert r.req.setup_info and os.path.isdir(r.req.setup_info.egg_base)
    setup_info = r.req.setup_info
    setup_info.get_info()
    assert (
        find_metadata(setup_info.egg_base)
        or find_metadata(setup_info.extra_kwargs["build_dir"])
        or setup_info.get_egg_metadata()
    )


@pytest.mark.needs_internet
def test_without_extras(pathlib_tmpdir):
    """Tests a setup.py or setup.cfg parse when extras returns None for some files"""
    setup_dir = pathlib_tmpdir.joinpath("sanitized-package")
    setup_dir.mkdir()
    assert setup_dir.is_dir()
    setup_py = setup_dir.joinpath("setup.py")
    setup_py.write_text(
        u"""
# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name="sanitized-package",
    version="0.0.1",
    install_requires=["raven==5.32.0"],
    extras_require={
        'PDF': ["socks"]
    }
)
    """.strip()
    )
    setup_dict = None
    with vistir.contextmanagers.cd(setup_dir.as_posix()):
        pipfile_entry = {
            "path": os.path.abspath(os.curdir),
            "editable": True,
            "extras": ["socks"],
        }
        r = Requirement.from_pipfile("e1839a8", pipfile_entry)
        r.run_requires()
        setup_dict = r.req.setup_info.as_dict()
        assert sorted(list(setup_dict.get("requires").keys())) == ["raven"]


@pytest.mark.parametrize(
    "setup_py_name, extras, dependencies",
    [
        (
            "package_with_multiple_extras",
            ["testing", "dev"],
            ["coverage", "flaky", "invoke", "parver", "six", "wheel"],
        ),
        ("package_with_one_extra", ["testing"], ["coverage", "flaky", "six"]),
    ],
)
def test_extras(pathlib_tmpdir, setup_py_dir, setup_py_name, extras, dependencies):
    """Test named extras as a dependency"""
    setup_dir = pathlib_tmpdir.joinpath("test_package")
    shutil.copytree(setup_py_dir.joinpath(setup_py_name).as_posix(), setup_dir.as_posix())
    assert setup_dir.is_dir()
    pipfile_entry = {
        "path": "./{0}".format(setup_dir.name),
        "extras": extras,
        "editable": True,
    }
    setup_dict = None
    with vistir.contextmanagers.cd(pathlib_tmpdir.as_posix()):
        r = Requirement.from_pipfile("test-package", pipfile_entry)
        assert r.name == "test-package"
        r.req.setup_info.get_info()
        setup_dict = r.req.setup_info.as_dict()
        assert sorted(list(setup_dict.get("requires").keys())) == dependencies


def test_ast_parser_finds_variables(setup_py_dir):
    parsed = ast_parse_setup_py(
        setup_py_dir.joinpath("package_with_extras_as_variable/setup.py").as_posix()
    )
    expected = {
        "name": "test_package",
        "version": "1.0.0",
        "description": "The Backend HTTP Server",
        "long_description": "This is a package",
        "install_requires": ["six"],
        "tests_require": ["coverage", "flaky"],
        "extras_require": {"testing": ["coverage", "flaky"]},
        "package_dir": {"": "src"},
        "packages": ["test_package"],
        "include_package_data": True,
        "zip_safe": False,
    }
    for k, v in expected.items():
        assert k in parsed
        if isinstance(v, bool):
            assert str(parsed[k]) == str(v), parsed[k]
        else:
            assert parsed[k] == v, parsed[k]


def test_ast_parser_finds_fully_qualified_setup(setup_py_dir):
    parsed = ast_parse_setup_py(
        setup_py_dir.joinpath(
            "package_using_fully_qualified_setuptools/setup.py"
        ).as_posix()
    )
    expected = {
        "name": "test_package",
        "version": "1.0.0",
        "description": "The Backend HTTP Server",
        "long_description": "This is a package",
        "install_requires": ["six"],
        "tests_require": ["coverage", "flaky"],
        "extras_require": {"testing": ["coverage", "flaky"]},
        "package_dir": {"": "src"},
        "packages": ["test_package"],
        "include_package_data": True,
        "zip_safe": False,
    }
    for k, v in expected.items():
        assert k in parsed
        if isinstance(v, bool):
            assert str(parsed[k]) == str(v), parsed[k]
        else:
            assert parsed[k] == v, parsed[k]
