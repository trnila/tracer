import pprint

import pytest


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
                result.append("ENV: {}".format(
                    pprint.pformat(executed.env)
                ))
                result.append('-' * 100)
                result.append(executed.data)

                rep.sections.append((executed.command, "\n".join(result)))
