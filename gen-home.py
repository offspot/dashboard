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

import collections
import gettext
import os
import pathlib
import re
import traceback
import urllib.parse

import humanfriendly
import pycountry
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    # we don't NEED cython ext but it's faster so use it if avail.
    from yaml import SafeLoader

LanguageDef = collections.namedtuple(
    "LanguageDef", ["alpha_3", "alpha_2", "native", "english"]
)

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


def get_lang_def(alpha_3: str) -> LanguageDef:
    """LanguageDef tuple with parsed/prepared language info"""
    try:
        language = pycountry.languages.get(alpha_3=alpha_3)
        if not language:
            raise ValueError("")
    except Exception:
        return LanguageDef(alpha_3, alpha_3[:2], alpha_3, alpha_3)

    try:
        alpha_2 = language.alpha_2
    except AttributeError:
        alpha_2 = alpha_3[:2]

    try:
        translator = gettext.translation(
            "iso639-3", pycountry.LOCALES_DIR, languages=[alpha_2]
        )
        native = translator.gettext(language.name).title()
    except Exception:
        native = language.name

    return LanguageDef(
        alpha_3=alpha_3, alpha_2=alpha_2, native=native, english=language.name
    )


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
    version: str = "n/a"
    footer_note: str = ""

    @classmethod
    def from_doc(cls, document):
        for key in ("name", "fqdn", "footer_note", "version"):
            setattr(cls, key, document.get(key, "--"))

    @classmethod
    def to_dict(cls):
        return {
            key: getattr(cls, key)
            for key in ("debug", "fqdn", "name", "version", "footer_note")
        }


class Link(dict):
    MANDATORY_FIELDS = ("name", "url")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["url"] = normalize(self.get("url", ""))


class Reader(dict):
    MANDATORY_FIELDS = ("platform", "download_url", "filename", "size")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["download_url"] = normalize(self.get("download_url", ""))

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

        self["category"] = ""
        for tag in self.private_tags:
            if tag.startswith("_category:"):
                self["category"] = tag.split(":", 1)[-1]

    @property
    def category(self) -> str:
        return self.get("category") or ""

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
    def langs(self) -> list[LanguageDef]:
        return [get_lang_def(lang) for lang in self.get("languages", [])]


def is_monolingual(packages: list[Package]) -> bool:
    """whether a collection of packages is monolingual or not

    Special code `mul` is not considered a different language as it is used for
    tools that are not language-bound.

    Packages and ZIMs that contain multiple language content dont use `mul` and
    provide an importance-sorted list of languages instead"""
    langs = []
    for package in packages:
        langs.extend(package.langs)
    mul = get_lang_def("mul")
    if mul in langs:
        langs.remove(mul)
    return len(set(langs)) == 1


def is_monocategorized(packages: list[Package]) -> bool:
    return len({package.category for package in packages if package.category}) == 1


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
    context["languages"] = {
        lang.alpha_3: lang.native
        for package in context["packages"]
        for lang in package.langs
    }
    context["languages"] = dict(
        sorted(context["languages"].items(), key=lambda item: item[1])
    )
    context["categories"] = sorted(
        {package.category for package in context["packages"] if package.category}
    )
    context["readers"] = [Reader(**item) for item in document.get("readers", [])]
    context["links"] = [Link(**item) for item in document.get("links", [])]
    context["is_monolingual"] = is_monolingual(context["packages"])
    context["is_monocategorized"] = is_monocategorized(context["packages"])

    try:
        with open(dest_dir / "index.html", "w") as fh:
            context["page"] = "home"
            fh.write(env.get_template("home.html").render(**context))

        with open(dest_dir / "about.html", "w") as fh:
            context["page"] = "about"
            fh.write(env.get_template("about.html").render(**context))

        with open(dest_dir / "download.html", "w") as fh:
            context["page"] = "download"
            fh.write(env.get_template("download.html").render(**context))

        with open(dest_dir / "blocked/" / "index.html", "w") as fh:
            fh.write(env.get_template("external.html").render(**context))
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
