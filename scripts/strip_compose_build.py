#!/usr/bin/env python3
"""Strip 'build:' and 'develop:' blocks from a Docker Compose YAML file.

Used by export-images.sh to produce offline-ready compose files that use
pre-built images instead of trying to build from source.
"""
import sys
import re


def strip_yaml_blocks(content: str, keys_to_strip: list[str]) -> str:
    """Remove top-level service keys (build, develop) and their nested content."""
    lines = content.split('\n')
    result = []
    skipping = False
    skip_indent = 0

    for line in lines:
        stripped = line.lstrip()

        if skipping:
            if stripped == '' or stripped.startswith('#'):
                # Blank lines / comments inside a skipped block — skip them
                continue
            current_indent = len(line) - len(stripped)
            if current_indent > skip_indent:
                continue
            else:
                skipping = False

        # Check if this line starts a block we want to strip.
        # Service-level keys are indented (typically 4 spaces in compose files).
        if stripped and not stripped.startswith('#'):
            for key in keys_to_strip:
                pattern = re.compile(rf'^(\s+){re.escape(key)}:\s*(.*)')
                m = pattern.match(line)
                if m:
                    skip_indent = len(m.group(1))
                    value = m.group(2).strip()
                    if value and not value.startswith('{') and not value.startswith('|') and not value.startswith('>'):
                        # Single-line value like "build: ./path" — skip just this line
                        skipping = False
                    else:
                        # Block value — skip until dedent
                        skipping = True
                    line = None
                    break

        if line is not None:
            result.append(line)

    return '\n'.join(result)


def main():
    # Optional: --strip key1,key2,... overrides the default key list. Any
    # matching block (a service like 'seed-data', or a nested key like 'build'
    # / a 'depends_on' entry of the same name) is removed wherever it appears.
    keys = ['build', 'develop']
    args = sys.argv[1:]
    if args and args[0] == '--strip':
        keys = [k.strip() for k in args[1].split(',') if k.strip()]
        args = args[2:]

    if not args:
        print(f"Usage: {sys.argv[0]} [--strip k1,k2] <input.yml> [output.yml]", file=sys.stderr)
        sys.exit(1)

    input_path = args[0]
    output_path = args[1] if len(args) > 1 else None

    with open(input_path) as f:
        content = f.read()

    result = strip_yaml_blocks(content, keys)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(result)
    else:
        print(result)


if __name__ == '__main__':
    main()
