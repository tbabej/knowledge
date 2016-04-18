import sys

from error import KnowledgeException


class AnkiProxy(object):
    """
    An abstraction over Anki interface.
    """

    DEFAULT_DECK = "Knowledge"
    DEFAULT_MODEL = "Basic"

    def __init__(self, path):
        sys.path.insert(0, "/usr/share/anki")
        import anki

        self.collection = anki.storage.Collection(path, lock=False)

    def add_note(self, deck, model, fields, tags=None):
        """
        Adds a new note of the given model to the given deck.
        """

        model = self.collection.models.byName(model)
        deck = self.collection.decks.byName(deck)

        if model is None:
            raise KnowledgeException("Model {0} not found".format(model))
        elif deck is None:
            raise KnowledgeException("Deck {0} not found".format(deck))

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
        return note.id

    def commit(self):
        self.collection.autosave()


class MnemosyneProxy(object):
    """
    An abstraction over Mnemosyne interface.
    """

    DEFAULT_DECK = None
    DEFAULT_MODEL = "1"

    def __init__(self, path=None):
        from mnemosyne.script import Mnemosyne

        try:
            self.mnemo = Mnemosyne(path)
        except SystemExit:
            raise KnowledgeException(
                "Mnemosyne is running. Please close it and reopen the file."
            )

    def add_note(self, deck, model, fields, tags=None):
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
        tags = (tags or set())
        if deck is not None:
            tags.add(deck.replace('.', '::'))

        card_type = self.mnemo.card_type_with_id(model)
        controller = self.mnemo.controller()

        cards = controller.create_new_cards(
            data,
            card_type,
            grade=-1,
            tag_names=tags,
            check_for_duplicates=False,
            save=False,
        )

        # We expect exactly one card created
        assert len(cards) == 1

        # Return the fact ID
        return cards[0].fact.id

    def update_note(self, identifier, fields, deck=None, model=None, tags=None):
        # Get the fact from Mnemosyne
        db = self.mnemo.database()
        fact = db.fact(identifier, is_id_internal=False)
        cards = db.cards_from_fact(fact)

        # Convert the deck name to the tag
        tags = (tags or set())
        if deck is not None:
            tags.add(deck.replace('.', '::'))

        # Transform the fields data to mnemosyne format
        data = {
            'f': fields.get("Front"),
            'b': fields.get("Back"),
        }

        current_data = fact.data
        current_tags = set([tag.name for tag in cards[0].tags])

        # Bail out if no modifications to be performed
        if current_tags == tags and current_data == data:
            return

        # Update the fact
        fact.data = data
        db.update_fact(fact)

        # Set new tags for each card
        old_tag_objects = set()
        new_tag_objects = db.get_or_create_tags_with_names(tags)
        for card in cards:
            old_tag_objects |= card.tags
            card.tags = new_tag_objects
            db.update_card(card)

        # Remove redundant tags
        for tag in old_tag_objects:
            db.delete_tag_if_unused(tag)

    def commit(self):
        db = self.mnemo.database()
        db.save()
