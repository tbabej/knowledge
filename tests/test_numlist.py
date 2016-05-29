from base import IntegrationTest


class TestCreateNumlistItemNote(IntegrationTest):

    viminput = """
    Steps to prepare an omellete:
    1. Make sure you have money
    2. Go to the shop
    3. Buy eggs and bacon
    4. Fry them on a pan
    5. Eat!
    """

    vimoutput = """
    Steps to prepare an omellete:
    1. Make sure you have money {identifier}
    2. Go to the shop {identifier}
    3. Buy eggs and bacon {identifier}
    4. Fry them on a pan {identifier}
    5. Eat! {identifier}
    """

    notes = [
        dict(
            front='Steps to prepare an omellete:\n1. ',
            back='1. Make sure you have money',
        ),
        dict(
            front='Steps to prepare an omellete:\n1. Make sure you have money\n2. ',
            back='2. Go to the shop',
        ),
        dict(
            front='Steps to prepare an omellete:\n1. Make sure you have money\n'
              '2. Go to the shop\n3. ',
            back='3. Buy eggs and bacon',
        ),
        dict(
            front='Steps to prepare an omellete:\n1. Make sure you have money\n'
               '2. Go to the shop\n3. Buy eggs and bacon\n4. ',
            back='4. Fry them on a pan'
        ),
        dict(
            front='Steps to prepare an omellete:\n1. Make sure you have money\n'
              '2. Go to the shop\n3. Buy eggs and bacon\n4. Fry them on a pan\n5. ',
            back='5. Eat!'
        ),
    ]

    def execute(self):
        self.command("w", regex="written$", lines=1)
