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


class TestCreateBasicMathNote(IntegrationTest):

    viminput = """
    Q: State the Pythagorean theorem
    - $c^2 = a^2 + b^2$
    """

    vimoutput = """
    Q: State the Pythagorean theorem {identifier}
    - $c^2 = a^2 + b^2$
    """

    notes = [
        dict(
            front='State the Pythagorean theorem',
            back='<$>c^2 = a^2 + b^2</$>',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateClozeNote(IntegrationTest):

    viminput = """
    The circumference of Earth is approximately [6378] km.
    """

    vimoutput = """
    The circumference of Earth is approximately [6378] km. {identifier}
    """

    notes = [
        dict(
            text='The circumference of Earth is approximately [6378] km.',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateClozeNoteParagraph(IntegrationTest):

    viminput = """
    The circumference of Earth is
    approximately [6378] km.
    """

    vimoutput = """
    The circumference of Earth is {identifier}
    approximately [6378] km.
    """

    notes = [
        dict(
            text='The circumference of Earth is\napproximately [6378] km.',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateClozeNoteLongParagraph(IntegrationTest):

    viminput = """
    The circumference of Earth,
    the third planet in the Solar System
    by its distance from the Sun (the central star of the system)
    is approximately [6378] km.
    """

    vimoutput = """
    The circumference of Earth, {identifier}
    the third planet in the Solar System
    by its distance from the Sun (the central star of the system)
    is approximately [6378] km.
    """

    notes = [
        dict(
            text='The circumference of Earth,\n'
                 'the third planet in the Solar System\n'
                 'by its distance from the Sun (the central star of the system)\n'
                 'is approximately [6378] km.',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateMultilineClozeNote(IntegrationTest):

    viminput = """
    First law: The orbit of a planet is [an ellipse with the Sun at one of the two
    foci]
    """

    vimoutput = """
    First law: The orbit of a planet is [an ellipse with the Sun at one of the two {identifier}
    foci]
    """

    notes = [
        dict(
            text='First law: The orbit of a planet is [an ellipse with the Sun at '
                 'one of the two\nfoci]',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateClozeNoteParagraphReformatting(IntegrationTest):

    viminput = """
    The circumference of Earth is approximately [6378] km.
    """

    vimoutput = """
    The circumference of {identifier}
    Earth is approximately [6378] km.
    """

    notes = [
        dict(
            text='The circumference of\nEarth is approximately [6378] km.',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)

        # Wrap the line after third word
        self.client.type("3wi")
        self.client.type("<Enter>")
        self.client.type("<Esc>")

        # The following seems redundant, however weirdly enough, does not work
        # if either of the lines is removed
        self.client.type(":w<Enter>")
        self.command("w", regex="written$", lines=1)


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


class TestOpenDollarSign(IntegrationTest):

    viminput = """
    Q: Command: How to list block devices
    - $ blkid
    """

    vimoutput = """
    Q: Command: How to list block devices {identifier}
    - $ blkid
    """

    notes = [
        dict(
            front='Command: How to list block devices',
            back='$ blkid',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestOpenDollarSignMultiple(IntegrationTest):

    viminput = """
    Q: Command: How to list block devices
    - $ blkid

    Q: Command: How to list USB devices
    - $ lsusb
    """

    vimoutput = """
    Q: Command: How to list block devices {identifier}
    - $ blkid

    Q: Command: How to list USB devices {identifier}
    - $ lsusb
    """

    notes = [
        dict(
            front='Command: How to list block devices',
            back='$ blkid',
        ),
        dict(
            front='Command: How to list USB devices',
            back='$ lsusb',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)
