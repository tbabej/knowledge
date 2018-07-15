from tests.base import IntegrationTest


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


class TestCreateMultiClozeItemNote(IntegrationTest):

    viminput = """
    List of capitols:
    * [England] - [London]
    * [France] - [Paris]
    * [Czech Republic] - [Prague]
    """


    vimoutput = """
    List of capitols:
    * [England] - [London] {identifier}
    * [France] - [Paris] {identifier}
    * [Czech Republic] - [Prague] {identifier}
    """

    notes = [
        dict(
            text='List of capitols:\n* [England] - [London]',
            count=2
        ),
        dict(
            text='List of capitols:\n* [France] - [Paris]',
            count=2
        ),
        dict(
            text='List of capitols:\n* [Czech Republic] - [Prague]',
            count=2
        ),
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateMultiLineClozeItemNote(IntegrationTest):

    viminput = """
    List of assembler instructions:
    * [mov eax, ebx] - [copies the data item referred
      to by its second operand into the location
      referred to by its first operand]
    * [push eax] - [places its operand onto the top
      of the hardware supported stack in memory]
    """

    vimoutput = """
    List of assembler instructions:
    * [mov eax, ebx] - [copies the data item referred {identifier}
      to by its second operand into the location
      referred to by its first operand]
    * [push eax] - [places its operand onto the top {identifier}
      of the hardware supported stack in memory]
    """

    notes = [
        dict(
            text='List of assembler instructions:\n* [mov eax, ebx] - [copies '
                 'the data item referred\n'
                 '  to by its second operand into the location\n'
                 '  referred to by its first operand]',
            count=2
        ),
        dict(
            text='List of assembler instructions:\n* [push eax] - '
                 '[places its operand onto the top\n'
                 '  of the hardware supported stack in memory]',
            count=2
        ),
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)
