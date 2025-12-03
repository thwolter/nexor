# Installation

Provisioning Nexor for local development or production services relies on a `uv`-managed virtual environment and a standard `pip` installation of the package.

## Prerequisites

- **Python version**: Nexor requires Python 3.13 or newer as per the project metadata.
- **Tooling**: Install [uv](https://github.com/vmware-labs/uv) so that dependency graphs can be reproduced from `uv.lock`.

## Install dependencies with uv

```bash
uv install
```

- `uv install` reads `uv.lock` and materialises dependencies into `.venv` (the default uv environment).
- If you need dev dependencies, run `uv install --env dev` before installing the package itself.

Activate the generated virtual environment before running `pip`, e.g.:

```bash
source .venv/bin/activate
```

## Install the package

After the virtual environment is active, install Nexor via `pip`:

```bash
pip install -e .
```

Alternative consumers can install Nexor as a path dependency:

```bash
pip install nexor @ file://../nexor
```

## Verification

| Task | Command |
| --- | --- |
| Validate dependency metadata | `uv lock --check` |
| Confirm package imports | `python -c "import nexor; print(nexor.__version__ if hasattr(nexor, '__version__') else 'n/a')"` |

TODO: add platform-specific notes or package mirrors when available.
