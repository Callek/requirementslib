# -*- coding=utf-8 -*-
import io
import json
import zipfile

import pytest

import requirementslib.models.metadata


@pytest.mark.parametrize(
    "package_json", [{"name": "celery"}, {"name": "llvmlite"},], indirect=True,
)
def test_metadata(monkeypatch_wheel_download, package_json):
    package = requirementslib.models.metadata.Package.from_json(package_json)
    package = package.get_dependencies()
    deps = sorted([str(d.requirement) for d in package.dependencies])
    if package.name == "llvmlite":
        assert list(deps) == ["enum34"]
    elif package.name == "celery":
        assert list(deps) == [
            "Django>=1.11",
            "PyYAML>=3.10",
            "azure-common==1.1.5",
            "azure-storage-common==1.1.0",
            "azure-storage==0.36.0",
            "backports.lzma",
            "billiard<4.0,>=3.6.1",
            "boto3>=1.9.125",
            "boto3>=1.9.178",
            'brotli>=1.0.0; platform_python_implementation == "CPython"',
            'brotlipy>=0.7.0; platform_python_implementation == "PyPy"',
            "cassandra-driver",
            "couchbase",
            'couchbase-cffi; platform_python_implementation == "PyPy"',
            "cryptography",
            "elasticsearch",
            "ephem",
            "eventlet>=0.24.1",
            "gevent",
            "kazoo>=1.3.1",
            "kombu<4.7,>=4.6.7",
            "librabbitmq>=1.5.0",
            "msgpack",
            "pyArango>=1.3.2",
            "pycouchdb",
            "pycurl",
            "pydocumentdb==2.3.2",
            "pylibmc",
            "pymongo[srv]>=3.3.0",
            "pyro4",
            "python-consul",
            "python-memcached",
            "pytz>dev",
            "redis>=3.2.0",
            "riak>=2.0",
            "softlayer-messaging>=1.0.3",
            "sqlalchemy",
            "tblib>=1.3.0",
            "tblib>=1.5.0",
            "vine==1.3.0",
            "zstandard",
        ]


def test_collect_files_from_zipfile(pathlib_tmpdir):
    wheel_path = pathlib_tmpdir / "test_wheel.whl"
    with zipfile.ZipFile(
        wheel_path.as_posix(), mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        with zf.open("test_wheel.dist-info/METADATA", mode="w") as fh:
            fh.write(b"This is a test")
        with zf.open("other_file", mode="w") as fh:
            fh.write(b"This is a test")
    with zipfile.ZipFile(
        wheel_path.as_posix(), "r", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        files = [
            fh.at
            for fh in requirementslib.models.metadata.collect_files_from_zipfile(
                zipfile.Path(zf)
            )
        ]
        assert list(sorted(files)) == list(
            sorted(["test_wheel.dist-info/METADATA", "other_file"])
        )
