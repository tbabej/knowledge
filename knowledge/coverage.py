import vim
import os

# Start measuring coverage if in testing
if vim.vars.get('knowledge_measure_coverage'):
    import atexit
    import coverage
    coverage_path = os.path.expanduser('~/knowledge-coverage/.coverage.{0}'.format(os.getpid()))
    cov = coverage.coverage(data_file=coverage_path)
    cov.start()

    def save_coverage():
        cov.stop()
        cov.save()

    atexit.register(save_coverage)
