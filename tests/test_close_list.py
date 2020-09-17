from tests.test_base import IntegrationTest


class TestCreateClozeItemNote(IntegrationTest):

    viminput = """
    List of capitols:
    * England - {London}
    * France - {Paris}
    * Czech Republic - {Prague}
    """


    vimoutput = """
    List of capitols:
    * England - {London} {identifier}
    * France - {Paris} {identifier}
    * Czech Republic - {Prague} {identifier}
    """

    notes = [
        dict(
            mnemosyne_text='List of capitols:\n* England - [London]',
            anki_text='List of capitols:<br>* England - {{c1::London}}'
        ),
        dict(
            mnemosyne_text='List of capitols:\n* France - [Paris]',
            anki_text='List of capitols:<br>* France - {{c1::Paris}}'
        ),
        dict(
            mnemosyne_text='List of capitols:\n* Czech Republic - [Prague]',
            anki_text='List of capitols:<br>* Czech Republic - {{c1::Prague}}'
        ),
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateMultiClozeItemNote(IntegrationTest):

    viminput = """
    List of capitols:
    * {England} - {London}
    * {France} - {Paris}
    * {Czech Republic} - {Prague}
    """


    vimoutput = """
    List of capitols:
    * {England} - {London} {identifier}
    * {France} - {Paris} {identifier}
    * {Czech Republic} - {Prague} {identifier}
    """

    notes = [
        dict(
            mnemosyne_text='List of capitols:\n* [England] - [London]',
            anki_text='List of capitols:<br>* {{c1::England}} - {{c2::London}}',
            count=2
        ),
        dict(
            mnemosyne_text='List of capitols:\n* [France] - [Paris]',
            anki_text='List of capitols:<br>* {{c1::France}} - {{c2::Paris}}',
            count=2
        ),
        dict(
            mnemosyne_text='List of capitols:\n* [Czech Republic] - [Prague]',
            anki_text='List of capitols:<br>* {{c1::Czech Republic}} - {{c2::Prague}}',
            count=2
        ),
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)


class TestCreateMultiLineClozeItemNote(IntegrationTest):

    viminput = """
    List of assembler instructions:
    * {mov eax, ebx} - {copies the data item referred
      to by its second operand into the location
      referred to by its first operand}
    * {push eax} - {places its operand onto the top
      of the hardware supported stack in memory}
    """

    vimoutput = """
    List of assembler instructions:
    * {mov eax, ebx} - {copies the data item referred {identifier}
      to by its second operand into the location
      referred to by its first operand}
    * {push eax} - {places its operand onto the top {identifier}
      of the hardware supported stack in memory}
    """

    notes = [
        dict(
            mnemosyne_text='List of assembler instructions:\n* [mov eax, ebx] - [copies '
                           'the data item referred\n'
                           '  to by its second operand into the location\n'
                           '  referred to by its first operand]',
            anki_text='List of assembler instructions:<br>* {{c1::mov eax, ebx}} - {{c2::copies '
                      'the data item referred<br>'
                      '  to by its second operand into the location<br>'
                      '  referred to by its first operand}}',
            count=2
        ),
        dict(
            mnemosyne_text='List of assembler instructions:\n* [push eax] - '
                           '[places its operand onto the top\n'
                           '  of the hardware supported stack in memory]',
            anki_text='List of assembler instructions:<br>* {{c1::push eax}} - '
                      '{{c2::places its operand onto the top<br>'
                      '  of the hardware supported stack in memory}}',
            count=2
        ),
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)
