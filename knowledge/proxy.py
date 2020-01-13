import abc
import os
import re
import sys
import time

from datetime import datetime

from knowledge.errors import KnowledgeException, FactNotFoundException
from knowledge import config, utils


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

    @abc.abstractmethod
    def note_info(self, identifier):
        """
        Obtain information about the note.
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
            elif index == len(field) - 1:
                # Last character on the line can be just added
                # since we know from above it's not a valid $
                result.append(char)
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
        escaped_eq = False
        escaped_bold = False
        inside_eq = False
        inside_bold = False
        last_open_index = 0

        for index, char in enumerate(field):
            if char == '$' and not escaped_eq:
                inside_eq = not inside_eq
                result.append(char)
            elif char == '*' and not (inside_eq or escaped_bold):
                if not inside_bold:
                    last_open_index = len(result)
                    result.append(self.SYMBOL_B_OPEN)
                    inside_bold = True
                else:
                    result.append(self.SYMBOL_B_CLOSE)
                    inside_bold = False
            elif index == len(field) - 1:
                # Last character on the line can be just added
                # since we know from above it's not a valid *
                result.append(char)
            elif char == "\\" and field[index+1] == '$':
                escaped_eq = True
                continue
            elif char == "\n" and field[index+1:index+3] == '* ':
                escaped_bold = True
                result.append(char)
                continue
            else:
                result.append(char)

            escaped_bold = False
            escaped_eq = False

        # If single * was converted, roll it back
        if inside_bold:
            result[last_open_index] = '*'

        return ''.join(result)

    def process_italic(self, field):
        """
        Process a field and make sure that text enclosed in star characters is
        depicted in italic. Ignores enumeration and latex environments.
        """

        # Use list to store the string to avoid unnecessary
        # work with copying string once per each letter during buildup
        result = []
        escaped_eq = False
        escaped_italic = False
        inside_eq = False
        inside_italic = False
        last_open_index = 0

        for index, char in enumerate(field):
            if char == '$' and not escaped_eq:
                inside_eq = not inside_eq
                result.append(char)
            elif char == '_' and not (inside_eq or escaped_italic):
                if not inside_italic:
                    last_open_index = len(result)
                    result.append(self.SYMBOL_I_OPEN)
                    inside_italic = True
                else:
                    result.append(self.SYMBOL_I_CLOSE)
                    inside_italic = False
            elif index == len(field) - 1:
                # Last character on the line can be just added
                # since we know from above it's not a valid *
                result.append(char)
            elif char == "\\" and field[index+1] == '$':
                escaped_eq = True
                continue
            elif char == "\n" and field[index+1] == '_':
                escaped_italic = True
                result.append(char)
                continue
            else:
                result.append(char)

            escaped_italic = False
            escaped_eq = False

        # If single * was converted, roll it back
        if inside_italic:
            result[last_open_index] = '_'

        return ''.join(result)

    def process_img(self, field):
        """
        Process a field and make sure that image links included in questions
        get expanded.
        """

        # Use list to store the string to avoid unnecessary
        # work with copying string once per each letter during buildup
        result = []
        inside_img = False
        last_open_index = 0

        for index, char in enumerate(field):
            if ''.join(field[index-7:index]) == '{{file:':
                inside_img = True
                result = result[:-7]
                result.append(self.SYMBOL_IMG_OPEN)
                last_open_index = len(result)
                result.append(char)
            elif inside_img and field[index-1:index+1] == '}}':
                inside_img = False
                result = result[:-1]  # Pop last '}'

                # Extract the filename from the top of the stack
                filepath = ''.join(result[last_open_index:])
                result = result[:last_open_index]

                # Make sure media file exists in SRS media directory
                srs_filepath = self.add_media_file(filepath)

                # Add the corresponding Mnemosyne filename and end img tag
                result.append(srs_filepath)
                result.append(self.SYMBOL_IMG_CLOSE)
            else:
                result.append(char)

        # If single {{ was converted, roll it back
        if inside_img:
            result[last_open_index] = '{{file:'

        return ''.join(result)

    def process_cloze(self, field):
        """
        Process a field and make sure that cloze syntax gets converted.
        """

        if not getattr(self, 'SYMBOL_CLOZE_OPEN', None):
            return field

        # Use list to store the string to avoid unnecessary
        # work with copying string once per each letter during buildup
        result = []
        last_open_index = 0
        cloze_count = 0
        cloze_open = False

        for index, char in enumerate(field):
            if char == '[' and not cloze_open:
                last_open_index = index
                cloze_open = True
                cloze_count += 1
                result.append("{{{{c{count}::".format(count=cloze_count))
            elif char == ']' and cloze_open:
                result.append("}}")
                cloze_open = False
            else:
                result.append(char)

        # If single [ was converted, roll it back
        if cloze_open:
            result[last_open_index] = '['

        return ''.join(result)

    def process_newlines(self, field):
        """
        If symbol for the new line is defined, replace \n with it.
        """

        if not getattr(self, 'SYMBOL_NEWLINE', None):
            return field

        return field.replace('\n', self.SYMBOL_NEWLINE)

    def process_all(self, fields):
        methods = (
            self.process_cloze,
            self.process_bold,
            self.process_italic,
            self.process_matheq,
            self.process_img,
            self.process_newlines,
        )

        for method in methods:
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
    CLOSE_MODEL = "Cloze"
    SYMBOL_EQ_OPEN = "[$]"
    SYMBOL_EQ_CLOSE = "[/$]"
    SYMBOL_B_OPEN = "<b>"
    SYMBOL_B_CLOSE = "</b>"
    SYMBOL_I_OPEN = "<i>"
    SYMBOL_I_CLOSE = "</i>"
    SYMBOL_IMG_OPEN = "<img src=\""
    SYMBOL_IMG_CLOSE = "\">"
    SYMBOL_CLOZE_OPEN = "{{{{c{cloze}::"
    SYMBOL_CLOZE_CLOSE = "}}"
    SYMBOL_NEWLINE = "<br>"

    def __init__(self, path):
        sys.path.insert(0, "/home/tbabej/Installed/anki")
        import anki

        self.collection = anki.storage.Collection(path, lock=False)
        self.Note = anki.notes.Note

    def cleanup(self):
        self.collection.close()
        del self.collection
        del self.Note

    def add_media_file(self, filename):
        """
        Adds a new media file to the media directory.
        """

        # Make sure the path is proper absolute filesystem path
        filename_expanded = os.path.expanduser(filename)
        if os.path.isabs(filename_expanded):
            filename_abs = filename_expanded
        else:
            filename_abs = os.path.join(
                os.path.dirname(utils.get_absolute_filepath()),
                filename_expanded
            )

        return self.collection.media.addFile(filename_abs)

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

        note.tags = set(tags) if tags else set()

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
        return str(note.id)

    def update_note(self, identifier, fields, deck=None, model=None, tags=None):
        tags = tags or set()

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

        deck_name = deck.replace('.', '::')
        deck = self.collection.decks.byName(deck_name)
        if deck is None:
            self.collection.decks.id(deck_name)
            deck = self.collection.decks.byName(deck_name)

        deck_id = deck['id']

        # Bail out if no change is proposed
        if all([cur_deck == deck_id, cur_tags == tags, cur_data == fields]):
            return

        # There are changes, so update the note
        for key in fields:
            note[key] = fields[key]

        note.tags = list(tags)

        if cur_deck != deck_id:
            # Updating deck is done directly via DB, see Anki internals in
            # browser.py::Browser._setDeck
            card_ids = self.collection.db.list(f"SELECT id FROM cards WHERE nid = {identifier}")
            result = self.collection.db.execute(
                f"UPDATE cards SET usn={self.collection.usn()}, "
                f"mod={int(time.time())}, "
                f"did={deck_id} "
                f"WHERE id IN ({','.join(map(str, card_ids))})",
            )

        # Push the changes, doesn't get saved without it
        note.flush()

    def commit(self):
        self.collection.save()

    def note_info(self, identifier):
        """
        Obtain information about the note.
        """

        # Get the fact from Anki
        try:
            note = self.Note(self.collection, id=identifier)
        except TypeError:
            # Anki raises TypeError in case ID is not found
            raise FactNotFoundException("Fact with ID '{0}' could not be found"
                                        .format(identifier))

        card = note.cards()[0]

        first_review = self.collection.db.scalar(f"SELECT min(id) FROM revlog WHERE cid={card.id}")
        last_review = self.collection.db.scalar(f"SELECT max(id) FROM revlog WHERE cid={card.id}")

        average_time = None
        total_time = None
        due = None

        num_revisions, total_time = self.collection.db.first(
            f"SELECT count(), sum(time)/1000 FROM revlog WHERE cid={card.id}"
        )

        if card.type in (1, 2):  # TODO: Document these type values with ENUM
            if card.queue in (2,3):
                due = time.time() + (card.due - self.collection.sched.today) * 86400
            else:
                due = card.due

        return {
            'added': datetime.fromtimestamp(card.id / 1000),
            'first_review': datetime.fromtimestamp(first_review / 1000) if first_review else None,
            'last_review': datetime.fromtimestamp(last_review / 1000) if last_review else None,
            'ease': card.factor / 10.0,
            'reviews': card.reps,
            'lapses': card.lapses,
            'card_type': card.template()['name'],
            'note_type': card.model()['name'],
            'deck': self.collection.decks.name(card.did),
            'note_id': card.nid,
            'card_id': card.id,
            'total_time': total_time,
            'average_time': (total_time / num_revisions) if num_revisions else None,
            'due': datetime.fromtimestamp(due),
            'interval': card.ivl * 86400 if card.queue == 2 else None
        }


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
    SYMBOL_I_OPEN = "<i>"
    SYMBOL_I_CLOSE = "</i>"
    SYMBOL_IMG_OPEN = "<img src=\""
    SYMBOL_IMG_CLOSE = "\">"


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

        # Make sure the path is proper absolute filesystem path
        filename_expanded = os.path.expanduser(filename)
        if os.path.isabs(filename_expanded):
            filename_abs = filename_expanded
        else:
            filename_abs = os.path.join(
                os.path.dirname(utils.get_absolute_filepath()),
                filename_expanded
            )

        copy_file_to_dir(filename_abs, media_dir)
        return contract_path(filename_abs, media_dir)

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
        # TODO: Modifying the deck will not cause the old deck tag to disappear
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
