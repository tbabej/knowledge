import sys
sys.path.insert(0, "/usr/share/anki")

import anki


class AnkiException(Exception):
    pass


class AnkiProxy(object):
    """
    An abstraction over Anki interface.
    """

    def __init__(self, path):
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
            raise AnkiException("Model {0} not found".format(model_name))
        elif deck is None:
            raise AnkiException("Deck {0} not found".format(deck_name))

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
            raise AnkiException("First field cannot be empty")
        elif status == 2:
            raise AnkiException("Duplicate note")

        self.collection.addNote(note)
        self.collection.autosave()
        return note.id
