"""Local editor integration check using actual held input and production C4 timers.

Requires a running Forest Base Defusal match with a living local host player.
The Editor helper discloses temporary bot/player controls in every report.
"""
import argparse
import json
import time
from pathlib import Path

from forestbase_bridge import call

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'output' / 'forestbase'


def command(value):
    result = call('console_run', {'command': value})
    if not result.get('success'):
        raise RuntimeError(result)


def read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def wait(path, condition, label, run_id=None, timeout=25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = read(path)
        if (run_id is None or result.get('runId') == run_id) and condition(result):
            print(label, flush=True)
            return result
        time.sleep(.15)
    raise TimeoutError(f'{label}: {read(path)}')


def has_event(result, name):
    return any(event['name'] == name for event in result.get('events', []))


def test(site):
    path = FOLDER / f'bomb-site-{site}-qa.json'
    old_run = read(path).get('runId')
    command(f'hc1_forestbase_bomb_prepare {site}')
    try:
        result = wait(path, lambda x: x.get('runId') and x['runId'] != old_run
                      and x.get('stage') == 'ready-to-plant', 'Ready in bomb zone')
        run_id = result['runId']
        if result['menuOpen']:
            command('dev_escape')
            wait(path, lambda x: not x['menuOpen'], 'Class menu closed', run_id)
        command('hc1_forestbase_bomb_hold Attack1 1')
        result = wait(path, lambda x: has_event(x, 'plant-cancelled'), 'Early plant release cancelled', run_id)
        assert next(x for x in result['events'] if x['name'] == 'plant-cancelled')['data']['remainingBombs'] == 0
        command('hc1_forestbase_bomb_hold Attack1 6')
        result = wait(path, lambda x: x.get('stage') == 'planted', 'Bomb planted by normal timer', run_id)
        observed = next(x for x in result['events'] if x['name'] == 'planted-observed')
        assert observed['data']['zone'] == [site], observed
        command('hc1_forestbase_bomb_defender')
        # Let the camera settle at the new position before the Use rising edge.
        time.sleep(.5)
        command('hc1_forestbase_bomb_hold Use 1')
        result = wait(path, lambda x: has_event(x, 'defuse-cancelled-observed'), 'Early defuse release cancelled', run_id)
        assert next(x for x in result['events'] if x['name'] == 'defuse-cancelled-observed')['data']['canUse']
        command('hc1_forestbase_bomb_hold Use 12')
        result = wait(path, lambda x: x.get('stage') == 'round-complete', 'Timed defuse and round result', run_id)
        result_event = next(x for x in result['events'] if x['name'] == 'round-result')
        assert result_event['data']['winner'] == 'CounterTerrorist', result_event
        assert result['isDefused'], result
        start = [x for x in result['events'] if x['name'] == 'defuse-start-observed'][-1]
        finished = next(x for x in result['events'] if x['name'] == 'defused-observed')
        assert finished['data']['elapsed'] >= start['data']['defuseTime'], finished
        evidence = FOLDER / f'bomb-site-{"A" if site == 0 else "B"}-passed.json'
        evidence.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(f'PASS: {evidence}', flush=True)
    finally:
        command('hc1_forestbase_bomb_restore')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=int, choices=[0, 1], required=True)
    test(parser.parse_args().site)
