import re

from knowledge import config, utils, regexp


class Header(object):

    def __init__(self):
        self.data = dict()

    @classmethod
    def from_line(cls, buffer_proxy, number):
        match = re.search(regexp.NOTE_HEADLINE, buffer_proxy[number])

        if not match:
            return None, 1

        self = cls()
        self.data.update({
            'header_start': match.group('header_start'),
            'header_end': match.group('header_end'),
            'name': match.group('name'),
        })

        # Update the header data from the hidden config string
        metadata = match.group('metadata').strip()
        self.data.update(utils.string_to_kwargs(metadata))

        return self, 1


class WikiNote(object):

    def __init__(self, buffer_proxy, proxy):
        self.fields = dict()
        self.data = dict()
        self.buffer_proxy = buffer_proxy
        self.proxy = proxy

    @classmethod
    def from_line(cls, buffer_proxy, number, proxy, heading=None, tags=None, model=None, deck=None):
        """
        This methods detects if a current line is a note-defining headline. If
        positive, it will try to parse the note data out of the block.
        """

        basic_question = re.search(regexp.QUESTION, buffer_proxy[number])
        close_mark_present = re.search(regexp.CLOSE_MARK, buffer_proxy[number])
        numlist_item = re.match(regexp.NUMLIST_MARK, buffer_proxy[number])

        if not any([basic_question, close_mark_present, numlist_item]):
            return None, 1

        self = cls(buffer_proxy, proxy)

        tags = tags or []
        deck = deck or proxy.DEFAULT_DECK

        if close_mark_present:
            model = model or proxy.CLOSE_MODEL
        else:
            model = model or proxy.DEFAULT_MODEL

        self.data.update({
            'line': number,
            'tags': set(tags),
            'model': model,
            'deck': deck,
            'heading': heading,
        })

        if close_mark_present:
            if utils.is_list_item(buffer_proxy, number):
                line_shift = self.parse_close_list_item()
            else:
                line_shift = self.parse_close()
        elif numlist_item:
            line_shift = self.parse_numlist_item()
        elif basic_question:
            line_shift = self.parse_basic(basic_question)

        return self, line_shift

    def parse_basic(self, match):
        # If we have a match, determine if it's an existing note
        self.data['id'] = match.group('identifier')
        question = match.group('question').strip()

        # Strip the question prefixes that should be ignored
        for prefix in config.QUESTION_OMITTED_PREFIXES:
            if question.startswith(prefix):
                question = question.lstrip(prefix).strip()
                break

        # Parse out the remaining question and answer parts
        questionlines = [question]
        answerlines = []
        parsing_question = True

        for line in self.buffer_proxy[(self.data['line']+1):]:
            candidate = line.strip()

            # Empty line finishes the parsing
            if not candidate:
                break

            # First line starting with '- ' denotes start of the answer
            if candidate.startswith('- '):
                answerlines.append(candidate[2:])
                parsing_question = False
            elif parsing_question:
                questionlines.append(candidate)

        # Compute question size before prepending the heading
        question_size = len(questionlines) + len(answerlines)
        self.data['last_line'] = self.data['line'] + question_size - 1

        # Inject heading into the question
        if self.data.get('heading'):
            questionlines.insert(0, self.data.get('heading') + '\n')

        self.fields.update({
            'Front': '\n'.join(questionlines),
            'Back': '\n'.join(answerlines),
        })

        return question_size

    def parse_close(self):
        lines = []

        # First, let's add upper part of the paragraph
        lines_included_upwards = 0

        for line in reversed(self.buffer_proxy[:(self.data['line'])]):
            candidate = line.strip()

            # Empty line finishes the parsing
            if not candidate:
                break
            else:
                lines_included_upwards += 1
                lines.insert(0, line)

        # Now the lower part of the paragraph
        lines_inspected_forward = 0

        for line in self.buffer_proxy[(self.data['line']):]:
            lines_inspected_forward += 1
            candidate = line.strip()

            # Empty line finishes the parsing
            if not candidate:
                break
            else:
                lines.append(line)

        # If anything was in the upper part of the paragraph, shift the
        # marked line for this note
        position = self.data['line']
        self.data['line'] = position - lines_included_upwards
        self.data['last_line'] = position + lines_inspected_forward - 1

        # Look for the identifier on any line
        textlines = '\n'.join(lines)
        match = re.search(regexp.CLOSE_IDENTIFIER, textlines)
        if match:
            # If present, do not include it in the field, and save it
            textlines = re.sub(regexp.CLOSE_IDENTIFIER, '', textlines)
            self.data['id'] = match.group('identifier')

        # Inject heading into the question
        if self.data.get('heading'):
            textlines = self.data.get('heading') + '\n\n' + textlines

        self.fields.update({
            'Text': textlines
        })

        return lines_inspected_forward

    def parse_close_list_item(self):
        lines = []

        # First, let's add upper part of the paragraph, including the
        # current line
        lines_included_upwards = -1

        list_item_parsed_upwards = False
        for line in reversed(self.buffer_proxy[:(self.data['line']+1)]):
            if not list_item_parsed_upwards:
                # We know that each line starts with either '* ' or '  '
                if line.startswith('* '):
                    list_item_parsed_upwards = True

                lines_included_upwards += 1
                lines.insert(0, line)
            else:
                # If the current item has been parsed, let's go all the way
                # up and include any non-item parts
                if line.startswith('* ') or line.startswith('  '):
                    continue
                elif not line.strip():
                    # Empty line means end of parsing
                    break
                else:
                    # Non-empty, non-intended line
                    # We do not count these lines as included upwards,
                    # as that number is used to place the identifier
                    # and we want that to be placed at the beginning
                    # of the item
                    lines.insert(0, line)

        # Now the lower part of the paragraph
        lines_inspected_forward = 1

        for line in self.buffer_proxy[(self.data['line']+1):]:
            if line.startswith('* '):
                # Start of the new item, let's terminate here
                break
            elif line.startswith('  '):
                # Continuation of the current item, let's add
                lines_inspected_forward += 1
                lines.append(line)
            else:
                # Anything else terminates the list
                break

        # If anything was in the upper part of the paragraph, shift the
        # marked line for this note
        position = self.data['line']
        self.data['line'] = position - lines_included_upwards
        self.data['last_line'] = position + lines_inspected_forward - 1

        # Look for the identifier on any line
        textlines = '\n'.join(lines)
        match = re.search(regexp.CLOSE_IDENTIFIER, textlines)
        if match:
            # If present, do not include it in the field, and save it
            textlines = re.sub(regexp.CLOSE_IDENTIFIER, '', textlines)
            self.data['id'] = match.group('identifier')

        # Inject heading into the question
        if self.data.get('heading'):
            textlines = self.data.get('heading') + '\n\n' + textlines

        self.fields.update({
            'Text': textlines
        })

        return lines_inspected_forward

    def __repr__(self):
        return repr(self.fields)

    def parse_numlist_item(self):
        questionlines = []
        answerlines = []

        # First, let's add upper part of the paragraph, not including the
        # current line

        for line in reversed(self.buffer_proxy[:(self.data['line'])]):
            # If the current item has been parsed, let's go all the way
            # up and include everything until the line break comes

            if not line.strip():
                break
            else:
                questionlines.insert(0, line)

        # Add a hint about the item number to the question
        current_line = self.buffer_proxy[(self.data['line'])]
        numlist_mark = re.match(regexp.NUMLIST_MARK, current_line).group()
        questionlines.append(numlist_mark)

        # Now the lower part of the paragraph
        answerlines.append(current_line)
        lines_inspected_forward = 1

        for line in self.buffer_proxy[(self.data['line']+1):]:
            if re.match(regexp.NUMLIST_MARK, line):
                # Start of the new item, let's terminate here
                break
            elif line.startswith('  '):
                # Continuation of the current item, let's add
                lines_inspected_forward += 1
                answerlines.append(line)
            else:
                # Anything else terminates the list
                break

        # Mark the last line of this item
        self.data['last_line'] = self.data['line'] + lines_inspected_forward - 1

        # Look for the identifier on any line among the scope of this item
        answerlines = '\n'.join(answerlines)

        match = re.search(regexp.CLOSE_IDENTIFIER, answerlines)
        if match:
            # If present, do not include it in the field, and save it
            answerlines = re.sub(regexp.CLOSE_IDENTIFIER, '', answerlines)
            self.data['id'] = match.group('identifier')

        # Also remove any identifier from the question
        questionlines = '\n'.join(questionlines)
        questionlines = re.sub(regexp.CLOSE_IDENTIFIER, '', questionlines)

        # Inject heading into the question
        if self.data.get('heading'):
            questionlines = self.data.get('heading') + '\n\n' + questionlines

        self.fields.update({
            'Front': questionlines,
            'Back': answerlines
        })

        return lines_inspected_forward

    @property
    def created(self):
        return self.data.get('id') is not None

    def save(self):
        if self.data.get('id') is not None:
            self._update()
            return

        obtained_id = self.proxy.add_note(
            fields=self.fields,
            deck=self.data['deck'],
            model=self.data['model'],
            tags=self.data['tags'],
        )

        if obtained_id:
            self.data['id'] = obtained_id
            self.update_identifier()

    def _update(self):
        self.proxy.update_note(
            identifier=self.data['id'],
            fields=self.fields,
            deck=self.data['deck'],
            model=self.data['model'],
            tags=self.data['tags']
        )
        # This is just for reformatting purposes
        self.update_identifier()

    def update_identifier(self):
        """
        Updates the representation of the note in the buffer.
        Note: Only affects the placement of the identifier.
        """

        # Get the identifier
        identifier = self.data.get('id')

        # Obtain lines that belong under the scope of this note
        lines = self.buffer_proxy[self.data['line']:self.data['last_line']+1]

        # If there is identifier and it's not in the first line, we need to fix it
        if identifier is not None and identifier not in lines[0]:
            lines[0] = u'{0} @{1}'.format(lines[0].rstrip(), identifier)

            # Remove identifier from any other line
            for index in range(1, len(lines)):
                lines[index] = lines[index].replace(' @' + identifier, '')

            # Update all the lines over which the question spans
            position = self.data['line']
            self.buffer_proxy[position:position+len(lines)] = lines
