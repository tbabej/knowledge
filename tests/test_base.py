# -*- coding: utf-8 -*-

import os
import re
import six
import shutil
import subprocess
import tempfile

import pytest
import vimrunner

from time import sleep


server_name = f"KnowledgeTaskServer-{os.getpid()}"
server = vimrunner.Server(server_name)


class IntegrationTest(object):

    viminput = None
    vimoutput = None
    notes = None
    tasks = []

    @pytest.fixture(autouse=True)
    def inject_log_fixture(self, request):
        setattr(self, 'log', request.getfixturevalue('failure_log'))

    def add_plugin(self, name, *args):
        plugin_base = os.path.expanduser('~/.vim/bundle/')
        plugin_path = os.path.join(plugin_base, name)
        self.client.add_plugin(plugin_path, *args)

    def write_buffer(self, lines, position=0):
        result = self.client.write_buffer(position + 1, lines)
        assert result == u"0"

    def read_buffer(self, start=0, end=1000):
        return self.client.read_buffer(
            six.text_type(start+1),
            six.text_type(end+1)
            ).splitlines()

    def setup_db(self):
        self.dir = tempfile.mkdtemp(dir='/tmp/')
        self.db_file = os.path.join(self.dir, 'knowledge.db')
        shutil.copyfile("tests/mnemosyne-empty.db",
                        os.path.join(self.dir, "default.db"))

    def start_client(self, retry=3):
        try:
            self.client = server.start_gvim()
        except RuntimeError:
            if retry > 0:
                sleep(2)
                self.start_client(retry=retry-1)
            else:
                raise

    def configure_global_variables(self):
        self.command('let g:knowledge_data_dir="{0}"'.format(self.dir))
        self.command('let g:knowledge_db_file="{0}"'.format(self.db_file))
        self.command('let g:knowledge_srs_provider="Mnemosyne"')
        self.command('let g:knowledge_measure_coverage="yes"')

    def setup(self):
        self.setup_db()
        self.start_client()  # Start client with 3 chances
        self.configure_global_variables()
        self.filepath = os.path.join(self.dir, 'knowledge.txt')
        self.add_plugin('knowledge')
        self.add_plugin('vimwiki', 'plugin/vimwiki.vim')
        self.client.edit(self.filepath)
        self.command('set filetype=vimwiki')

    def teardown(self):
        self.client.quit()
        subprocess.call(['pkill', '-f', f'gvim.*--servername {server_name}'])
        sleep(0.2)  # Killing takes some time
        self.tasks = self.__class__.tasks  # Reset the task list

    def command(self, command, silent=True, regex=None, lines=None):
        result = self.client.command(command)

        # Specifying regex or lines cancels expectations of silence
        if regex or lines:
            silent = False

        # For silent commands, there should be no output
        if silent is not None:
            if silent:
                assert not result
            else:
                assert result

            # Multiline-evaluate the regex
            if regex:
                assert re.search(regex, result, re.MULTILINE)

            if lines:
                assert lines == len(result.splitlines())

        return result

    def check_sanity(self, soft=True):
        """
        Makes sanity checks upon the vim instance.
        """

        # Assert all the important files were loaded
        scriptnames = self.client.command('scriptnames').splitlines()
        expected_loaded_files = [
            'vimwiki/autoload/vimwiki/base.vim',
            'vimwiki/autoload/vimwiki/path.vim',
            'vimwiki/ftplugin/vimwiki.vim',
            'vimwiki/autoload/vimwiki/u.vim',
            'vimwiki/autoload/vimwiki/vars.vim',
            'vimwiki/syntax/vimwiki.vim',
            'knowledge/ftplugin/vimwiki.vim',
        ]

        # Do a partial match for each line from scriptnames
        for scriptfile in expected_loaded_files:
            if not soft:
                assert any([scriptfile in line for line in scriptnames])
            elif not any([scriptfile in line for line in scriptnames]):
                return False

        # Success in the sanity check
        return True

    def test_execute(self):
        # First, run sanity checks
        success = False

        for i in range(5):
            if self.check_sanity(soft=True):
                success = True
                break
            else:
                self.teardown()
                self.setup()

        if not success:
            self.check_sanity(soft=False)

        # Then load the input
        if self.viminput:
            # Unindent the lines
            lines = [l[4:]
                     for l in self.viminput.strip('\n').splitlines()]
            self.write_buffer(lines)

        # Do the stuff
        self.execute()

        # Check expected output
        if self.vimoutput:
            lines = [
                l[4:]
                for l in self.vimoutput.strip('\n').splitlines()[:-1]
            ]

            # Replace any identifiers in the output by {identifier}
            # placeholder
            buffer_lines = [
                re.sub('@(?P<identifier>[^\s]+)\s*$', '{identifier}', line)
                for line in self.read_buffer()
            ]

            assert buffer_lines == lines

        if self.notes:
            import sys
            from mnemosyne.script import Mnemosyne

            from pony import orm

            know_db = orm.Database('sqlite', self.db_file)

            class Mapping(know_db.Entity):
                knowledge_id = orm.PrimaryKey(str)
                fact_id = orm.Required(str)

            know_db.generate_mapping()

            @orm.db_session
            def backend_get(knowledge_id):
                mapping = Mapping.get(knowledge_id=knowledge_id)

                # If mapping not found in the local database, raise an exception
                if mapping is None:
                    raise errors.MappingNotFoundException(knowledge_id)

                return mapping.fact_id

            mnemosyne = Mnemosyne(self.dir)
            db = mnemosyne.database()

            identifiers = filter(lambda x: x is not None, [
                re.search('@(?P<identifier>[^\s]+)\s*$', line)
                for line in self.read_buffer()
            ])

            # We need to translate the identifiers to Mnemosyne identifiers
            # using backend
            translated_identifiers = [
                backend_get(identifier.group('identifier'))
                for identifier in identifiers
            ]

            facts = [
                db.fact(identifier, is_id_internal=False)
                for identifier in translated_identifiers
            ]

            for index, fact in enumerate(facts):
                expected_fact = self.notes[index]

                assert expected_fact.get('text') == fact.data.get('text')
                assert expected_fact.get('front') == fact.data.get('f')
                assert expected_fact.get('back') == fact.data.get('b')

                cards = db.cards_from_fact(fact)
                tags = (expected_fact.get('tags') or []) + ['knowledge']
                assert set(tags) == set([tag.name for tag in cards[0].tags])

                # Assert that expected number of cards have been generated
                assert len(db.cards_from_fact(fact)) == expected_fact.get('count', 1)

            # Assert that all facts have been tested
            assert len(facts) == len(self.notes)

            # Assert that all facts have been obtained
            assert len(facts) == db.fact_count()

    def execute(self):
        pass


# Mock vim to test vim-nonrelated functions
class MockVim(object):

    class current(object):
        buffer = ['']

    vars = dict()
    warriors = dict()

    def eval(*args, **kwargs):
        return 42

    def reset(self):
        self.current.buffer = ['']
        self.vars.clear()
        self.warriors.clear()


class MockBuffer(object):

    def __init__(self):
        self.data = ['']

    def obtain(self):
        pass

    def push(self):
        pass

    def __getitem__(self, index):
        try:
            return self.data[index]
        except IndexError:
            return ''

    def __setitem__(self, index, lines):
        self.data[index] = lines

    def __delitem__(self, index):
        del self.data[index]

    def __iter__(self):
        for line in self.data:
            yield line

    def __len__(self):
        return len(self.data)

    def append(self, data, position=None):
        if position is None:
            self.data.append(data)
        else:
            self.data.insert(position, data)
