from base import IntegrationTest


class TestCreateClozeItemNote(IntegrationTest):

    viminput = """
    List of capitols:
    * England - [London]
    * France - [Paris]
    * Czech Republic - [Prague]
    """


    vimoutput = """
    List of capitols:
    * England - [London] {identifier}
    * France - [Paris] {identifier}
    * Czech Republic - [Prague] {identifier}
    """

    notes = [
        dict(
            text='List of capitols:\n* England - [London]'
        ),
        dict(
            text='List of capitols:\n* France - [Paris]'
        ),
        dict(
            text='List of capitols:\n* Czech Republic - [Prague]'
        ),
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)
