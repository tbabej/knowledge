import sys

from error import KnowledgeException


class AnkiProxy(object):
    """
    An abstraction over Anki interface.
    """

    def __init__(self, path):
        sys.path.insert(0, "/usr/share/anki")
        import anki

        self.collection = anki.storage.Collection(path, lock=False)

    @property
    def models(self):
        return self.collection.models

    @property
    def decks(self):
        return self.collection.decks

    def add_note(self, deck_name, model_name, fields, tags=None):
        """
        Adds a new note of the given model to the given deck.
        """

        model = self.models.byName(model_name)
        deck = self.decks.byName(deck_name)

        if model is None:
            raise KnowledgeException("Model {0} not found".format(model_name))
        elif deck is None:
            raise KnowledgeException("Deck {0} not found".format(deck_name))

        # Create a new Note
        note = anki.notes.Note(self.collection, model)

        # Set the deck and tags
        note.model()['did'] = deck['id']

        if tags:
            note.tags = tags

        # Fill in all the fields
        for key in fields:
            note[key] = fields[key]

        status = note.dupeOrEmpty()

        if status == 1:
            raise KnowledgeException("First field cannot be empty")
        elif status == 2:
            # This means only that the first field is identical
            pass

        self.collection.addNote(note)
        self.collection.autosave()
        return note.id


class MnemosyneProxy(object):
    """
    An abstraction over Mnemosyne interface.
    """

    def __init__(self, path=None):
        from mnemosyne.script import Mnemosyne

        try:
            self.mnemo = Mnemosyne(path)
        except SystemExit:
            raise KnowledgeException(
                "Mnemosyne is running. Please close it and reopen the file."
            )

    def add_note(self, deck_name, model_name, fields, tags=None):
        """
        Adds a new fact with specified fields, model name and tags.
        Returns the ID of the fact.
        """

        # Transform the fields data to mnemosyne format
        data = {
            'f': fields.get("Front"),
            'b': fields.get("Back"),
        }

        # Convert the deck name to the tag
        tags = (tags or [])
        tags.append(deck_name.replace('.', '::'))

        card_type = self.mnemo.card_type_with_id(model_name)
        controller = self.mnemo.controller()

        cards = controller.create_new_cards(
            data,
            card_type,
            grade=-1,
            tag_names=tags
        )

        # We expect exactly one card created
        assert len(cards) == 1

        # Return the fact ID
        return cards[0].fact.id
