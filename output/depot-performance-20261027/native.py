"""Save native editor evidence for the Depot performance audit."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools'))
from photographic_look import call

OUTPUT = Path(__file__).resolve().parent


def normalise(value):
    if not isinstance(value, str) or not value.lstrip().startswith('{'):
        return value
    decoder = json.JSONDecoder()
    remaining = value.strip()
    results = []
    while remaining.startswith('{'):
        try:
            item, end = decoder.raw_decode(remaining)
        except json.JSONDecodeError:
            break
        results.append(item)
        remaining = remaining[end:].strip()
    return {'results': results, 'text': remaining} if results else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool')
    parser.add_argument('--args', type=Path)
    parser.add_argument('--script', type=Path)
    parser.add_argument('--label', required=True)
    parser.add_argument('--brief', action='store_true')
    args = parser.parse_args()
    arguments = json.loads(args.args.read_text(encoding='utf-8-sig')) if args.args else {}
    if args.script:
        state = call('instance_status')
        exchange = Path(state['ExchangeDirectory'])
        exchange.mkdir(parents=True, exist_ok=True)
        target = exchange / args.script.name
        target.write_text(args.script.read_text(encoding='utf-8-sig'), encoding='utf-8')
        arguments['path'] = str(target)
    result = normalise(call(args.tool, arguments))
    destination = OUTPUT / (args.label + '.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if args.brief:
        print(json.dumps({'report': str(destination), 'keys': list(result) if isinstance(result, dict) else type(result).__name__}))
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
