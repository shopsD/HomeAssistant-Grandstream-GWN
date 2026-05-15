import argparse
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import project_meta as _project_meta
else:
    try:
        from . import project_meta as _project_meta
    except ImportError:
        import project_meta as _project_meta

def replace_or_fail(path: Path, pattern: str, repl: str) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Expected exactly 1 match in {path} for pattern: {pattern}")
    path.write_text(new_text, encoding="utf-8")

def main() -> None:
    APP_VERSION = _project_meta.APP_VERSION
    HOMEASSISTANT_MIN_VERSION = _project_meta.HOMEASSISTANT_MIN_VERSION
    PYTHON_REQUIRES = _project_meta.PYTHON_REQUIRES
    PYTHON_VERSION = _project_meta.PYTHON_VERSION
    REPOSITORY_URL = _project_meta.REPOSITORY_URL
    UPDATE_URL = _project_meta.UPDATE_URL

    SCRIPT_PATH: Path = Path(__file__).resolve()

    parser = argparse.ArgumentParser(description="Repository Meta Data Sync")
    parser.add_argument(
        "-r"
        ,"--repo-root"
        ,type=Path
        ,default=SCRIPT_PATH.parent.parent
        ,help="Path to the repository root folder"
    )

    parser.add_argument("-s", "--set-hook", action=argparse.BooleanOptionalAction)
    
    args = parser.parse_args()

    if args.set_hook:
        print ("Setting up Pre-Commit Hook")
        GITHOOKS = Path(args.repo_root / ".git/hooks/pre-commit")
        with GITHOOKS.open("w", encoding="utf-8") as file_handle:
            file_handle.write(f'#!/usr/bin/env sh\npython3 {SCRIPT_PATH} --repo-root "{args.repo_root}"\n')
        GITHOOKS.chmod(0o755)
        print ("Set up Pre-Commit Hook")

    GWN_CONSTANTS = args.repo_root / "gwn/constants/Constants.py"
    VERSION_MANAGER = args.repo_root / "mqtt/app/VersionManager.py"
    PYPROJECT = args.repo_root / "pyproject.toml"
    HACS = args.repo_root / "hacs.json"
    HACS_MANIFEST = args.repo_root / "custom_components/grandstream_gwn/manifest.json"
    PYTHON_VERSION_FILE = args.repo_root / ".python-version"
    README = args.repo_root / "README.md"
    print (f"Syncing files:\n\t{PYPROJECT}\n\t{HACS}\n\t{PYTHON_VERSION_FILE}\n\t{README}\nVersions:\n\tApp Version: {APP_VERSION}\n\tPython Version: {PYTHON_VERSION}\n\tPython Requires: {PYTHON_REQUIRES}\n\tHome Assistant Min Version: {HOMEASSISTANT_MIN_VERSION}")

    replace_or_fail(
        PYPROJECT,
        r'^version = "[^"]+"$',
        f'version = "{APP_VERSION}"'
    )
    replace_or_fail(
        PYPROJECT,
        r'^requires-python = "[^"]+"$',
        f'requires-python = "{PYTHON_REQUIRES}"'
    )
    replace_or_fail(
        PYPROJECT,
        r'^ha = \["homeassistant>=[^"]+"\]$',
        f'ha = ["homeassistant>={HOMEASSISTANT_MIN_VERSION}"]'
    )
    replace_or_fail(
        HACS,
        r'^(\s*)"homeassistant": "[^"]+"(,?)$',
        rf'\1"homeassistant": "{HOMEASSISTANT_MIN_VERSION}"\2'
    )
    replace_or_fail(
        HACS_MANIFEST,
        r'^(\s*)"version": "[^"]+"(,?)$',
        rf'\1"version": "{APP_VERSION}"\2'
    )
    replace_or_fail(
        HACS_MANIFEST,
        r'^(\s*)"documentation": "[^"]+"(,?)$',
        rf'\1"documentation": "{REPOSITORY_URL}"\2'
    )
    replace_or_fail(
        PYTHON_VERSION_FILE,
        r"^[^\n]+$",
        PYTHON_VERSION
    )
    replace_or_fail(
        GWN_CONSTANTS,
        r'^(\s*)APP_VERSION: ClassVar\[str\] = "[^"]+"$',
        rf'\1APP_VERSION: ClassVar[str] = "{APP_VERSION}"'
    )
    replace_or_fail(
        README,
        r'^(\s*-\s+)Python `[^`]+`(.*)$',
        rf'\1Python `{PYTHON_VERSION}`\2'
    )
    replace_or_fail(
        VERSION_MANAGER,
        r'^(\s*)self\._repo_url\: str \=  "[^"]+"(.*)$',
        rf'\1self._repo_url: str = "{UPDATE_URL}"\2'
    )
    print ("Sync Complete")

if __name__ == "__main__":
    main()
