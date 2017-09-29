import abc
import os
import re
import sys
import time

from knowledge.errors import KnowledgeException, FactNotFoundException
from knowledge import config


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
    def add_media_file(self, filename):
        """
        Adds a new media file to the media directory.
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

    @abc.abstractmethod
    def cleanup(self):
        """
        Make sure that proxy instance has been deinitialized.
        """

    def process_matheq(self, field):
        # Process any latex expressions:
        #   - substitute latex keyword not followed by a space
        for command in config.GLUED_LATEX_COMMANDS:
            field = re.sub('\\' + command + '(?! )', '\\' + command + ' ', field)

        # Use list to store the string to avoid unnecessary
        # work with copying string once per each letter during buildup
        result = []
        escaped = False
        inside_eq = False
        last_open_index = 0

        for index, char in enumerate(field):
            if char == '$' and not escaped:
                if inside_eq:
                    result.append(self.SYMBOL_EQ_CLOSE)
                    inside_eq = False
                else:
                    last_open_index = len(result)
                    result.append(self.SYMBOL_EQ_OPEN)
                    inside_eq = True
            elif char == "\\" and field[index+1] == '$':
                escaped = True
                continue
            else:
                result.append(char)

            escaped = False

        # If single $ was converted, roll it back
        if inside_eq:
            result[last_open_index] = '$'

        return ''.join(result)

    def process_bold(self, field):
        """
        Process a field and make sure that text enclosed in star characters is
        depicted in bold. Ignores enumeration and latex environments.
        """

        # Use list to store the string to avoid unnecessary
        # work with copying string once per each letter during buildup
        result = []
        escaped = False
        inside_eq = False
        inside_bold = False
        last_open_index = 0

        for index, char in enumerate(field):
            if char == '$' and not escaped:
                inside_eq = not inside_eq
            elif char == '*' and not (inside_eq or index == 0):
                if not inside_bold:
                    last_open_index = len(result)
                    result.append(self.SYMBOL_B_OPEN)
                    inside_bold = True
                else:
                    result.append(self.SYMBOL_B_CLOSE)
                    inside_bold = False
            elif char == "\\" and field[index+1] == '$':
                escaped = True
                continue
            else:
                result.append(char)

            escaped = False

        # If single * was converted, roll it back
        if inside_eq:
            result[last_open_index] = '*'

        return ''.join(result)

    def process_all(self, fields):
        for method in (self.process_matheq, self.process_bold):
            fields = {
                key: method(value)
                for key, value in fields.items()
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
    SYMBOL_B_OPEN = "<b>"
    SYMBOL_B_CLOSE = "</b>"

    def __init__(self, path):
        sys.path.insert(0, "/usr/share/anki")
        import anki

        self.collection = anki.storage.Collection(path, lock=False)
        self.Note = anki.notes.Note

    def cleanup(self):
        del self.collection
        del self.Note

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
    SYMBOL_B_OPEN = "<b>"
    SYMBOL_B_CLOSE = "</b>"


    def __init__(self, path=None):
        from mnemosyne.script import Mnemosyne

        try:
            self.mnemo = Mnemosyne(path)

            # Activate the Cloze plugin
            # Note: The import needs to be here, since it relies on the
            # presence of the translation engine, which is initialized with
            # the mnemosyne object.
            from mnemosyne.libmnemosyne.card_types.cloze import ClozePlugin
            for plugin in self.mnemo.plugins():
                if isinstance(plugin, ClozePlugin):
                    plugin.activate()
                    break

        except SystemExit:
            raise KnowledgeException(
                "Mnemosyne is running. Please close it and reopen the file."
            )

    def cleanup(self):
        try:
            self.mnemo.finalise()
        except Exception as e:
            pass

        del self.mnemo

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

    def add_media_file(self, filename):
        """
        Adds a new media file to the media directory.
        """

        from mnemosyne.libmnemosyne.utils import copy_file_to_dir, contract_path
        media_dir = self.mnemo.database().media_dir()

        filename_expanded = os.path.expanduser(filename)

        copy_file_to_dir(filename_expanded, media_dir)
        return contract_path(filename_expanded, media_dir)

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

        try:
            cards = controller.create_new_cards(
                data,
                card_type,
                grade=-1,
                tag_names=tags,
                check_for_duplicates=False,
                save=False,
            )
        except AssertionError:
            raise KnowledgeException("Fact '{0}' could not be added, it "
                                     "most likely contains invalid "
                                     "data".format(fields))

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
