#!/usr/bin/env python3

""" gen-home: generate static home page from Packages YAML

    - Reads Packages YAML from `PACKAGES_PATH`
    - Prepares an HTML output with templates defined in `SRC_DIR`/templates
    - Writes and index.html in `DEST_DIR`
    - Optionally (`DEBUG`) outputs index to stdout as well

    Dependencies:
    - PyYAML
    - Jinja2
    - humanfriendly
"""

from __future__ import annotations

import os
import pathlib
import re
import traceback
import urllib.parse

import humanfriendly
import iso639
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    # we don't NEED cython ext but it's faster so use it if avail.
    from yaml import SafeLoader


src_dir = pathlib.Path(os.getenv("SRC_DIR", "/src")).expanduser().resolve()
packages_path = (
    pathlib.Path(os.getenv("PACKAGES_PATH", "home.yaml")).expanduser().resolve()
)
dest_dir = pathlib.Path(os.getenv("DEST_DIR", "/var/www")).expanduser().resolve()
templates_dir = src_dir.joinpath("templates")
env = Environment(
    loader=FileSystemLoader(templates_dir), autoescape=select_autoescape()
)


def format_fsize(size: str | int) -> str:
    one_gib = 2**30
    one_mib = 2**20
    hundred_mib = one_gib / 10

    def round_to(size: int, scale: int) -> int:
        return (size // scale) * scale

    if not str(size).isdigit():
        size = humanfriendly.parse_size(str(size))
    size = int(size)

    if size > one_gib and size >= 100 * one_gib:
        size = round_to(size, one_gib)
    elif size > one_gib:
        size = round_to(size, hundred_mib)
    else:
        size = round_to(size, one_mib)
    try:
        return humanfriendly.format_size(
            int(size), keep_width=False, binary=True
        ).replace("iB", "B")
    except Exception:
        return str(size)


env.filters["fsize"] = format_fsize


def normalize(url: str) -> str:
    if not url.strip():
        return ""
    uri = urllib.parse.urlparse(url)
    if not uri.scheme and not url.startswith("//"):
        url = f"//{url}"

    url = re.sub(r"{([a-z]+)-fqdn}", r"\1.{fqdn}", url)
    url = url.replace("{fqdn}", Conf.fqdn)
    return url


class Conf:
    debug: bool = bool(os.getenv("DEBUG", ""))
    fqdn: str = ""
    name: str = ""
    footer_note: str = ""

    @classmethod
    def from_doc(cls, document):
        for key in ("name", "fqdn", "footer_note"):
            setattr(cls, key, document.get(key, "--"))

    @classmethod
    def to_dict(cls):
        return {
            key: getattr(cls, key) for key in ("debug", "fqdn", "name", "footer_note")
        }


class Link(dict):
    MANDATORY_FIELDS = ("name", "url")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["url"] = normalize(self.get("url", ""))


class Reader(dict):
    MANDATORY_FIELDS = ("platform", "url", "size")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["url"] = normalize(self.get("url", ""))

    @property
    def name(self) -> str:
        return {
            "windows": "Windows",
            "android": "Android",
            "macos": "macOS",
            "linux": "Linux",
        }.get(self["platform"].lower(), self["platform"])

    @property
    def icon(self) -> str:
        return {
            "windows": "windows",
            "android": "android",
            "macos": "apple",
            "linux": "linux",
        }.get(self["platform"].lower(), "robot")


class Package(dict):
    MANDATORY_FIELDS = ("title", "url")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["url"] = normalize(self.get("url", ""))
        try:
            self["download"]["url"] = normalize(self["download"]["url"])
        except KeyError:
            ...

    @property
    def tags(self) -> list[str]:
        return [tag for tag in self.get("tags", []) if tag and not tag.startswith("_")]

    @property
    def private_tags(self) -> list[str]:
        return [tag for tag in self.get("tags", []) if tag.startswith("_")]

    @property
    def visible(self):
        if self.get("disabled", False):
            return False
        try:
            return all(self[key] for key in self.MANDATORY_FIELDS)
        except KeyError:
            return False

    @property
    def langs(self) -> list[str]:
        return [lang[:2] for lang in self.get("languages", [])]


def gen_home(fpath: pathlib.Path):
    try:
        document = yaml.load(fpath.read_text(), Loader=SafeLoader)
    except Exception as exc:
        print("[CRITICAL] unable to read home YAML document, using fallback homepage")
        traceback.print_exception(exc)
        return

    Conf.from_doc(document.get("metadata", {}))
    context = Conf.to_dict()
    context["packages"] = list(
        filter(lambda p: p.visible, [Package(**item) for item in document["packages"]])
    )
    context["languages"] = {}
    context["categories"] = set()
    for package in context["packages"]:
        for lang in package.get("languages", []):
            context["languages"][lang] = iso639.Lang(lang).name
        for tag in package.get("tags", []):
            if tag.startswith("_category:"):
                package["category"] = tag.split(":", 1)[-1]
                context["categories"].add(package["category"])
    context["categories"] = sorted(context["categories"])
    context["readers"] = [Reader(**item) for item in document.get("readers", [])]
    context["links"] = [Link(**item) for item in document.get("links", [])]

    try:
        with open(dest_dir / "index.html", "w") as fh:
            context["page"] = "home"
            fh.write(env.get_template("home.html").render(**context))

        with open(dest_dir / "download.html", "w") as fh:
            context["page"] = "download"
            fh.write(env.get_template("download.html").render(**context))
    except Exception as exc:
        print("[CRITICAL] unable to gen homepage, using fallback")
        traceback.print_exception(exc)
        return

    print("Generated homepage")


if __name__ == "__main__":
    gen_home(packages_path)

    if Conf.debug:
        with open(dest_dir / "index.html") as fh:
            print(fh.read())
