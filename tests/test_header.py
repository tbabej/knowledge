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


class TestCreateClozeNoteUnderHeader(IntegrationTest):

    viminput = """
    === Life questions @ deck:Physics ===

    The visible spectrum is between [390 to 700] nm.
    """

    vimoutput = """
    === Life questions @ deck:Physics ===

    The visible spectrum is between [390 to 700] nm. {identifier}
    """

    notes = [
        dict(
            text="The visible spectrum is between [390 to 700] nm.",
            tags=['Physics']
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateBasicNoteUnderHeaderWithSubdeck(IntegrationTest):

    viminput = """
    === Life questions @ deck:Life.Questions ===

    Q: This is a question
    - And this is the answer
    """

    vimoutput = """
    === Life questions @ deck:Life.Questions ===

    Q: This is a question {identifier}
    - And this is the answer
    """

    notes = [
        dict(
            front='This is a question',
            back='And this is the answer',
            tags=['Life::Questions']
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateBasicNoteUnderNestedHeadersOverriden(IntegrationTest):

    viminput = """
    == Universe @ deck:Universe ==

    === Life @ deck:Life ===

    Q: This is a question
    - And this is the answer
    """

    vimoutput = """
    == Universe @ deck:Universe ==

    === Life @ deck:Life ===

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


class TestTokenInterpretedAsDeckByDefault(IntegrationTest):

    viminput = """
    === Life questions @ Life ===

    Q: This is a question
    - And this is the answer
    """

    vimoutput = """
    === Life questions @ Life ===

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


class TestHeaderExtraTag(IntegrationTest):

    viminput = """
    === Life questions @ Life +extra ===

    Q: This is a question
    - And this is the answer
    """

    vimoutput = """
    === Life questions @ Life +extra ===

    Q: This is a question {identifier}
    - And this is the answer
    """

    notes = [
        dict(
            front='This is a question',
            back='And this is the answer',
            tags=['Life', 'extra']
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestHeaderStacking(IntegrationTest):

    viminput = """
    == Math formulas @ Math +formulas ==

    === Life questions @ Math.Goniometric ===

    Q: This is a question
    - And this is the answer
    """

    vimoutput = """
    == Math formulas @ Math +formulas ==

    === Life questions @ Math.Goniometric ===

    Q: This is a question {identifier}
    - And this is the answer
    """

    notes = [
        dict(
            front='This is a question',
            back='And this is the answer',
            tags=['Math::Goniometric', 'formulas']
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)
