import os

from knowledge import config

# Start measuring coverage if in testing
if config.MEASURE_COVERAGE:
    import atexit
    import coverage
    coverage_path = os.path.expanduser('~/knowledge-coverage/.coverage.{0}'.format(os.getpid()))
    cov = coverage.coverage(data_file=coverage_path)
    cov.start()

    def save_coverage():
        cov.stop()
        cov.save()

    atexit.register(save_coverage)
