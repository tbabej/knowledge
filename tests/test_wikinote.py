# -*- coding: utf-8 -*-
from tests.test_base import IntegrationTest


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


class TestCreateBasicUnicodeNote(IntegrationTest):

    viminput = u"""
    Q: Toto je otázka ktorá nemá úplne ľahkú odpoveď.
    Bude tento program fungovať aj s krásnou diakritikou?
    - Veruže bude, prečo by nefungoval?
    """

    vimoutput = u"""
    Q: Toto je otázka ktorá nemá úplne ľahkú odpoveď. {identifier}
    Bude tento program fungovať aj s krásnou diakritikou?
    - Veruže bude, prečo by nefungoval?
    """

    notes = [
        dict(
            front=u'Toto je otázka ktorá nemá úplne ľahkú odpoveď.\n'
                  u'Bude tento program fungovať aj s krásnou diakritikou?',
            back=u'Veruže bude, prečo by nefungoval?',
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
