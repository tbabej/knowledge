import pytest


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
    return rep


@pytest.yield_fixture
def failure_log(request):
    messages = []
    yield messages.append
    item = request.node
    if 'rep_call' in dir(item) and item.rep_call.failed:
        print(f'\nAdditional details: {item.nodeid}')
        for message in messages:
            print (f"- {message}")
