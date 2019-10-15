import random
import re
from string import ascii_letters
from lib.inject_const import *

class Template():

    def __init__(self, text):
        self._text = text

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        self._text = text

    def __str__(self):
        return self.text

    def set(self, key, value):

        r = re.search(r'^{}: (.+)\n'.format(key), self.text, re.MULTILINE)
        if not r:
            return

        inj_type = r[1]

        if inj_type in [INJECT_STRING]: # \b means boundry
            pattern = r'(\b{}:) {}'.format(key, INJECT_STRING)
            repl = f"\\1 '{value}'"
            
        else: 
            pattern = r'(\b{}:) \w+'.format(key)
            repl = f"\\1 {value}"
        
        self.text = re.sub(pattern, repl, self.text, re.MULTILINE)
    
    def delete(self, key):
        if not len(key):
            return
        pattern = r'(\b{}:) \w+'.format(key)
        repl = ''
        self.text = re.sub(r'\b{}:.*'.format(key), '', self.text, re.MULTILINE)


    def fill(self, func):
        self.text = func(self.text)
