#!/usr/bin/env python3

""" refresh-zims: update YAML packages list using disk-discovered ZIM files

    This is an optional feature, yet it is enabled by default.
    Set `DONT_UPDATE_PACKAGES` environ to disable

    Once enabled, this loops over ZIM files present on disk (at `ZIM_DIR` path)
    and updates the Packages YAML (at `PACKAGES_PATH`) accordingly:
        - if the package (using its ident) was in YAML: keep YAML entry
        - if the ZIM was not in YAML: add entry using in-ZIM info
        - entries in YAML for which ZIM is missing are disabled but kept.

    Dependencies:
    - PyYAML
    - libzim
"""

from __future__ import annotations

import base64
import os
import pathlib
import traceback
from typing import Any

import yaml
from libzim.reader import Archive

try:
    from yaml import CDumper as Dumper
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    # we don't NEED cython ext but it's faster so use it if avail.
    from yaml import Dumper, SafeLoader

packages_path = (
    pathlib.Path(os.getenv("PACKAGES_PATH", "home.yaml")).expanduser().resolve()
)
zims_dir = pathlib.Path(os.getenv("ZIM_DIR", "/src"))
dont_update = bool(os.getenv("DONT_UPDATE_PACKAGES", ""))

kiwix_reader_link_tpl = os.getenv("KIWIX_READER_LINK_TPL", "//kiwix.{fqdn}/{zim_name}")
kiwix_download_link_tpl = os.getenv(
    "KIWIX_DOWNLOAD_LINK_TPL", "//zim-download.{fqdn}/{zim_filename}"
)


def get_metadata(archive: Archive, name: str) -> str:
    if name not in archive.metadata_keys:
        return ""
    return archive.get_metadata(name).decode("UTF-8")


def get_kiwix_url(template: str, fqdn: str, name: str, filename: str) -> str:
    return (
        template.replace("{fqdn}", fqdn)
        .replace("{zim_name}", name)
        .replace("{zim_filename}", filename)
    )


def get_entry_for(
    fpath: pathlib.Path, document_metadata: dict[str, str]
) -> dict[str, Any]:
    zim = Archive(fpath)
    publisher = get_metadata(zim, "Publisher")
    name = get_metadata(zim, "Name")
    flavour = get_metadata(zim, "Flavour")
    ident = f"{publisher}:{name}:{flavour}"
    icon = None
    if zim.has_illustration and 48 in zim.get_illustration_sizes():  # noqa: PLR2004
        icon = base64.b64encode(bytes(zim.get_illustration_item(48).content)).decode(
            "ASCII"
        )
    return {
        "kind": "zim",
        "ident": ident,
        "title": get_metadata(zim, "Title"),
        "description": get_metadata(zim, "Description"),
        "languages": get_metadata(zim, "Language").split(",") or ["eng"],
        "tags": get_metadata(zim, "Tags").split(";"),
        "url": get_kiwix_url(
            template=kiwix_reader_link_tpl,
            fqdn=document_metadata["fqdn"],
            name=name,
            filename=fpath.name,
        ),
        "download": {
            "url": get_kiwix_url(
                template=kiwix_download_link_tpl,
                fqdn=document_metadata["fqdn"],
                name=name,
                filename=fpath.name,
            ),
            "size": fpath.stat().st_size,
        },
        "icon": icon,
    }


def refresh_zims(
    packages_path: pathlib.Path,
    zims_dir: pathlib.Path,
    *,
    debug: bool | None = False,  # noqa: ARG001
):
    print(f"refreshing ZIMs from {zims_dir=}")
    try:
        document = yaml.load(packages_path.read_text(), Loader=SafeLoader)
        document["packages"]
        document["metadata"]
        document["metadata"]["fqdn"]
        document["metadata"]["name"]
    except Exception as exc:
        print("[CRITICAL] unable to read home YAML document, skiping")
        traceback.print_exception(exc)
        return

    # copy list of packages from YAML
    conf_packages = {
        package.get("ident", ""): package for package in document["packages"]
    }

    # get packages from what's on the filesystem
    fs_packages = {}
    for zim_fpath in zims_dir.glob("*.zim"):
        try:
            package = get_entry_for(zim_fpath, document["metadata"])
        except Exception as exc:
            print(f"Failed to read from {zim_fpath}, skiping ({exc})")
            continue
        else:
            fs_packages[package["ident"]] = package

    # now let's start from scratch
    document["packages"] = []

    # first, adding files in config, in their original order, disabling missing ones
    for ident, package in conf_packages.items():
        # make sure we keep non-ZIM packages
        if ident in fs_packages or package.get("kind", "") != "zim":
            package.pop("disabled", None)
        else:
            package["disabled"] = True
        document["packages"].append(package)

    # second, add all the fs ones, but not those already in conf
    for ident, package in fs_packages.items():
        # dont add twice, was already handled
        if ident in conf_packages:
            continue
        document["packages"].append(package)

    try:
        packages_path.write_text(yaml.dump(document, Dumper=Dumper))
    except Exception as exc:
        print("[CRITICAL] unable to update(save) home YAML document, skiping")
        traceback.print_exception(exc)
        return


if __name__ == "__main__":
    if not dont_update and zims_dir.exists() and zims_dir.is_dir():
        refresh_zims(
            packages_path=packages_path,
            zims_dir=zims_dir,
            debug=bool(os.getenv("DEBUG", False)),
        )
    else:
        print(f"Not refreshing ZIMs for {dont_update=}, {zims_dir=}")
