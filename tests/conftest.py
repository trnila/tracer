import json
import pprint

import pytest


def _sanitize(string):
    data = json.loads(string)

    for pid, process in data['processes'].items():
        process['env'] = None

    return json.dumps(data, indent=2)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # we only look at actual failing test calls, not setup/teardown
    if rep.when == "call" and rep.failed:
        executes = getattr(item.obj.__self__, 'executed', None)
        if executes:
            for executed in executes:
                result = []
                result.append('tracer {} {}'.format(
                    " ".join(executed.options),
                    executed.command
                ))
                result.append('OPTIONS: {}'.format(
                    executed.options
                ))
                result.append('-' * 100)
                result.append(_sanitize(executed.data))

                rep.sections.append((executed.command, "\n".join(result)))
