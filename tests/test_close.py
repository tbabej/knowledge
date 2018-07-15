from tests.base import IntegrationTest


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
