"""Read-only CLI wrapper for Programme Compiler / Validator V0.1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from new_earth_platform.programme_compiler import compile_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile a new-earth.programme.v1 definition without operational writes."
        )
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/programme-definition.schema.json"),
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    result = compile_file(args.input, schema_path=args.schema)
    rendered = json.dumps(
        result.to_dict(),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    if args.out:
        args.out.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    return 0 if result.outcome == "VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
