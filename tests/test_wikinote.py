from tests.base import IntegrationTest


class TestWriteEmptyFile(IntegrationTest):

    viminput = """
    """

    vimoutput = """
    """

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestWriteRegularFile(IntegrationTest):

    viminput = """
    This is a test line.
    This file contains no facts.
    """

    vimoutput = """
    This is a test line.
    This file contains no facts.
    """

    def execute(self):
        self.command("w", regex="written$", lines=1)
