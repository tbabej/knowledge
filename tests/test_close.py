from tests.test_base import IntegrationTest


class TestCreateClozeNote(IntegrationTest):

    viminput = """
    The circumference of Earth is approximately {6378} km.
    """

    vimoutput = """
    The circumference of Earth is approximately {6378} km. {identifier}
    """

    notes = [
        dict(
            mnemosyne_text='The circumference of Earth is approximately [6378] km.',
            anki_text='The circumference of Earth is approximately {{c1::6378}} km.',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateClozeNoteParagraph(IntegrationTest):

    viminput = """
    The circumference of Earth is
    approximately {6378} km.
    """

    vimoutput = """
    The circumference of Earth is {identifier}
    approximately {6378} km.
    """

    notes = [
        dict(
            mnemosyne_text='The circumference of Earth is\napproximately [6378] km.',
            anki_text='The circumference of Earth is<br>approximately {{c1::6378}} km.',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateClozeNoteLongParagraph(IntegrationTest):

    viminput = """
    The circumference of Earth,
    the third planet in the Solar System
    by its distance from the Sun (the central star of the system)
    is approximately {6378} km.
    """

    vimoutput = """
    The circumference of Earth, {identifier}
    the third planet in the Solar System
    by its distance from the Sun (the central star of the system)
    is approximately {6378} km.
    """

    notes = [
        dict(
            mnemosyne_text='The circumference of Earth,\n'
                           'the third planet in the Solar System\n'
                           'by its distance from the Sun (the central star of the system)\n'
                           'is approximately [6378] km.',
            anki_text='The circumference of Earth,<br>'
                      'the third planet in the Solar System<br>'
                      'by its distance from the Sun (the central star of the system)<br>'
                      'is approximately {{c1::6378}} km.',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateClozeAtLineStart(IntegrationTest):

    viminput = """
    {Bratislava} is the capital city of Slovakia.
    """

    vimoutput = """
    {Bratislava} is the capital city of Slovakia. {identifier}
    """

    notes = [
        dict(
            mnemosyne_text='[Bratislava] is the capital city of Slovakia.',
            anki_text='{{c1::Bratislava}} is the capital city of Slovakia.',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateMultilineClozeNote(IntegrationTest):

    viminput = """
    First law: The orbit of a planet is {an ellipse with the Sun at one of the two
    foci}
    """

    vimoutput = """
    First law: The orbit of a planet is {an ellipse with the Sun at one of the two {identifier}
    foci}
    """

    notes = [
        dict(
            mnemosyne_text='First law: The orbit of a planet is [an ellipse with the Sun at '
                           'one of the two\nfoci]',
            anki_text='First law: The orbit of a planet is {{c1::an ellipse with the Sun at '
                      'one of the two<br>foci}}',
        )
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateClozeNoteParagraphReformatting(IntegrationTest):

    viminput = """
    The circumference of Earth is approximately {6378} km.
    """

    vimoutput = """
    The circumference of {identifier}
    Earth is approximately {6378} km.
    """

    notes = [
        dict(
            mnemosyne_text='The circumference of\nEarth is approximately [6378] km.',
            anki_text='The circumference of<br>Earth is approximately {{c1::6378}} km.',
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


class TestCreateClozeCodeBlockIgnored(IntegrationTest):

    viminput = """
    A efficient way of computing the fibbonaci numbers uses the ideas of
    the dynamic programming:

        fib = [1] * n
        for i in range(2, n):
            fib[i] = fib[i-1] + fib[i-2]
    """

    vimoutput = """
    A efficient way of computing the fibbonaci numbers uses the ideas of
    the dynamic programming:

        fib = [1] * n
        for i in range(2, n):
            fib[i] = fib[i-1] + fib[i-2]
    """

    notes = []

    def execute(self):
        self.command("w", regex="written$", lines=1)
