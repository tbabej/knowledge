import pytest


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
    return rep


def pytest_exception_interact(node, call, report):
    """
    If an exception was raised (such as AssertError) call the post_mortem
    method of the class, if it exists.
    """

    if report.failed:
        print(node.parent._obj)
        node.parent._obj.post_mortem()


@pytest.yield_fixture
def failure_log(request):
    messages = []
    yield messages.append
    item = request.node
    if item.rep_call.failed:
        print(f'\nAdditional details: {item.nodeid}')
        for message in messages:
            print (f"- {message}")
