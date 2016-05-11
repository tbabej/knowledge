from base import IntegrationTest


class TestCreateBasicNoteUnderHeader(IntegrationTest):

    viminput = """
    === Life questions @ deck:Life ===

    Q: This is a question
    - And this is the answer
    """

    vimoutput = """
    === Life questions @ deck:Life ===

    Q: This is a question {identifier}
    - And this is the answer
    """

    notes = [
        dict(
            front='This is a question',
            back='And this is the answer',
            tags=['Life']
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)
