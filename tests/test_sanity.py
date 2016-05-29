"""
This module just tests whether the Mnemosyne script interface can be
initialized, which is a requirement for the knowledge plugin to work.
"""

def test_sanity():
    from mnemosyne.script import Mnemosyne
    mnemo = Mnemosyne('/tmp/')
