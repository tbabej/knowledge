import abc
import sys
import time

from error import KnowledgeException, FactNotFoundException


class SRSProxy(object):

    @abc.abstractmethod
    def __init__(self, path=None):
        """
        Initialize the proxy object. Takes an optional path to the database
        file.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def add_note(self, deck, model, fields, tags=None):
        """
        Adds a new fact to the database. Returns the identifier to the task.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def update_note(self, identifier, fields, deck=None, model=None, tags=None):
        """
        Updates the given fact. If the fact could not be found,
        raises FactNotFoundException.
        """

    @abc.abstractmethod
    def commit(self):
        """
        Actually commits the changes to the database.
        """

    def process_matheq(self, field):
        # Use list to store the string to avoid unnecessary
        # work with copying string once per each letter during buildup
        result = []
        escaped = False
        inside_eq = False

        for index, char in enumerate(field):
            if char == '$' and not escaped:
                if inside_eq:
                    result.append(self.SYMBOL_EQ_CLOSE)
                    inside_eq = False
                else:
                    result.append(self.SYMBOL_EQ_OPEN)
                    inside_eq = True
            elif char == "\\" and field[index+1] == '$':
                escaped = True
                continue
            else:
                result.append(char)

            escaped = False

        return ''.join(result)


    def process_all(self, fields):
        for method in (self.process_matheq,):
            fields = {
                key: method(value)
                for key, value in fields.iteritems()
            }

        return fields


class AnkiProxy(SRSProxy):
    """
    An abstraction over Anki interface.
    """

    DEFAULT_DECK = "Knowledge"
    DEFAULT_MODEL = "Basic"
    SYMBOL_EQ_OPEN = "[$]"
    SYMBOL_EQ_CLOSE = "[/$]"

    def __init__(self, path):
        sys.path.insert(0, "/usr/share/anki")
        import anki

        self.collection = anki.storage.Collection(path, lock=False)
        self.Note = anki.notes.Note

    def add_note(self, deck, model, fields, tags=None):
        """
        Adds a new note of the given model to the given deck.
        """

        model_name = model
        deck_name = deck.replace('.', '::')

        model = self.collection.models.byName(model_name)
        deck = self.collection.decks.byName(deck_name)

        # Pre-process data in fields
        fields = self.process_all(fields)

        if model is None:
            raise KnowledgeException("Model {0} not found".format(model_name))

        if deck is None:
            self.collection.decks.id(deck_name)
            deck = self.collection.decks.byName(deck_name)

        # Create a new Note
        note = self.Note(self.collection, model)

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

    def update_note(self, identifier, fields, deck=None, model=None, tags=None):
        # Get the fact from Anki
        try:
            note = self.Note(self.collection, id=identifier)
        except TypeError:
            # Anki raises TypeError in case ID is not found
            raise FactNotFoundException("Fact with ID '{0}' could not be found"
                                        .format(identifier))

        # Pre-process data in fields
        fields = self.process_all(fields)

        # Generate current card data, deck and tags
        cur_data = {
            key: note[key]
            for key in note.keys()
            if key in fields
        }
        cur_deck = note.model()['did']
        cur_tags = set(note.tags)

        # Bail out if no change is proposed
        deck = self.collection.decks.byName(deck)
        deck_id = deck['id'] if deck is not None else None

        if all([cur_deck == deck_id, cur_tags == tags, cur_data == fields]):
            return

        # There are changes, so update the note
        for key in fields:
            note[key] = fields[key]

        note.tags = list(tags)
        note.model()['did'] = deck_id

        # Push the changes, doesn't get saved without it
        note.flush()

    def commit(self):
        self.collection.save()


class MnemosyneProxy(SRSProxy):
    """
    An abstraction over Mnemosyne interface.
    """

    CLOSE_MODEL = "5"
    DEFAULT_DECK = None
    DEFAULT_MODEL = "1"
    SYMBOL_EQ_OPEN = "<$>"
    SYMBOL_EQ_CLOSE = "</$>"

    def __init__(self, path=None):
        from mnemosyne.script import Mnemosyne

        try:
            self.mnemo = Mnemosyne(path)
        except SystemExit:
            raise KnowledgeException(
                "Mnemosyne is running. Please close it and reopen the file."
            )

    def extract_data(self, fields, model):
        """
        Extracts the data dict from the given fields, depending
        on the model being used.
        """

        # Transform the fields data to mnemosyne format
        if model == self.CLOSE_MODEL:
            data = {'text': fields.get("Text")}
        else:
            data = {
                'f': fields.get("Front"),
                'b': fields.get("Back"),
            }

        return data

    def add_note(self, deck, model, fields, tags=None):
        """
        Adds a new fact with specified fields, model name and tags.
        Returns the ID of the fact.
        """

        # Pre-process data in fields
        fields = self.process_all(fields)
        data = self.extract_data(fields, model)

        # Convert the deck name to the tag
        tags = (tags or set())
        if deck is not None:
            tags.add(deck.replace('.', '::'))

        try:
            card_type = self.mnemo.card_type_with_id(model)
        except KeyError:
            raise KnowledgeException("Model (card type) '{0}' does "
                                     "not exist".format(model))
        controller = self.mnemo.controller()

        cards = controller.create_new_cards(
            data,
            card_type,
            grade=-1,
            tag_names=tags,
            check_for_duplicates=False,
            save=False,
        )

        # We expect exactly one card created for regular cards,
        # or at least one for closes
        if model == self.DEFAULT_MODEL:
            assert len(cards) == 1
        elif model == self.CLOSE_MODEL:
            assert len(cards) >= 1

        # Return the fact ID
        return cards[0].fact.id

    def update_note(self, identifier, fields, deck=None, model=None, tags=None):
        # Get the fact from Mnemosyne
        db = self.mnemo.database()

        try:
            fact = db.fact(identifier, is_id_internal=False)
        except TypeError:
            # Mnemosyne raises TypeError in case ID is not found
            raise FactNotFoundException("Fact with ID '{0}' could not be found"
                                        .format(identifier))

        cards = db.cards_from_fact(fact)
        if not cards:
            raise FactNotFoundException("Fact with ID '{0}' does not have any"
                                        "cards assigned".format(identifier))

        # Convert the deck name to the tag
        tags = (tags or set())
        if deck is not None:
            tags.add(deck.replace('.', '::'))

        # Pre-process data in fields
        fields = self.process_all(fields)

        # Transform the fields data to mnemosyne format
        data = self.extract_data(fields, model)

        current_data = fact.data
        current_tags = set([tag.name for tag in cards[0].tags])

        # Bail out if no modifications to be performed
        if current_tags == tags and current_data == data:
            return

        # Update the fact
        card_type = self.mnemo.card_type_with_id(model)
        new, edited, deleted = card_type.edit_fact(fact, data)
        fact.data = data
        db.update_fact(fact)

        # Create, delete and edit all cards that were affected by this update
        # This mainly happens with card types that generate multiple cards, like
        # questions with multiple closes
        for card in deleted:
            db.delete_card(card)

        for card in new:
            db.add_card(card)

        for card in edited:
            db.update_card(card)

        # Refetch the list of cards
        cards = db.cards_from_fact(fact)

        # Set new tags for each card
        old_tag_objects = set()
        new_tag_objects = db.get_or_create_tags_with_names(tags)

        # Fetch the current time
        modification_time = int(time.time())

        for card in cards:
            old_tag_objects |= card.tags
            card.modification_time = modification_time
            card.tags = new_tag_objects
            db.update_card(card)

        # Remove redundant tags
        for tag in old_tag_objects:
            db.delete_tag_if_unused(tag)

    def commit(self):
        db = self.mnemo.database()
        db.save()
