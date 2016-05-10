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


class TestWriteInTaskwikiFile(IntegrationTest):

    viminput = """
    * [ ] This is a taskwiki task that should be ignored
    """

    vimoutput = """
    * [ ] This is a taskwiki task that should be ignored
    """

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateBasicNote(IntegrationTest):

    viminput = """
    Q: This is a question
    - And this is the answer
    """

    vimoutput = """
    Q: This is a question {identifier}
    - And this is the answer
    """

    notes = [
        dict(
            front='This is a question',
            back='And this is the answer',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateBasicMultilineNote(IntegrationTest):

    viminput = """
    Q: This is a multiline question
    - And this is the answer
    - which spans over multiple lines
    - and nobody minds.
    """

    vimoutput = """
    Q: This is a multiline question {identifier}
    - And this is the answer
    - which spans over multiple lines
    - and nobody minds.
    """

    notes = [
        dict(
            front='This is a multiline question',
            back="And this is the answer\n"
                 "which spans over multiple lines\n"
                 "and nobody minds."
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)
