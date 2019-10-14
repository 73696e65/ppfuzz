import copy
import re
import random
import sys

from inject_const import *
from google.protobuf.descriptor import FieldDescriptor as fd

RE_PARENTHESIZED_EXPR = re.compile(r'\([^()]*\)[?+*]')
RE_EXTENDED_NONTERMINAL = re.compile(r'(<[^<> ]*>[?+*])')
RE_NONTERMINAL = re.compile(r'(<[^<> ]*>)')
symbol_name = "<symbol>"

def gpb_to_ebnf(msg):
    """
    Create a EBNF grammer from a protobuf message class
    """
    g = dict()

    def traverse_message(parent, name=None):

        key = name if name else parent.name

        value = str()
        for o in parent.fields:
            if o.label == fd.LABEL_OPTIONAL:
                value += f'(<{o.name}>)?'
            elif o.label == fd.LABEL_REQUIRED:
                value += f'<{o.name}>'
            elif o.label == fd.LABEL_REPEATED:
                value += f'(<{o.name}>)+'
            else:
                raise NotImplementedError

        g[f'<{key}>'] = [ value ]

        for o in parent.fields:
            if o.type == fd.TYPE_MESSAGE:
                traverse_message(o.message_type, o.name)
            elif o.type == fd.TYPE_INT64: # 3
                g[f'<{o.name}>'] = [INJECT_INT64] 
            elif o.type == fd.TYPE_INT32: # 5
                g[f'<{o.name}>'] = [INJECT_INT32]
            elif o.type == fd.TYPE_BOOL:
                g[f'<{o.name}>'] = [INJECT_BOOL]
            elif o.type == fd.TYPE_STRING: # 9
                g[f'<{o.name}>'] = [INJECT_STRING]
            elif o.type == fd.TYPE_BYTES: # 12
                g[f'<{o.name}>'] = [INJECT_BYTES]
            elif o.type == fd.TYPE_ENUM: # 14
                g[f'<{o.name}>'] = [e.name for e in o.enum_type.values]            
            else:
                print(f"{parent.name} -> {o.name}, {o.type}")
                raise NotImplementedError

    traverse_message(msg.DESCRIPTOR)
    return convert_ebnf_grammar(g)


def convert_ebnf_parentheses(ebnf_grammar):
    """
    Convert a parentheses in extended BNF to BNF
    """
    grammar = extend_grammar(ebnf_grammar)
    for nonterminal in ebnf_grammar:
        expansions = ebnf_grammar[nonterminal]

        for i in range(len(expansions)):
            expansion = expansions[i]

            while True:
                parenthesized_exprs = parenthesized_expressions(expansion)
                if len(parenthesized_exprs) == 0:
                    break

                for expr in parenthesized_exprs:
                    operator = expr[-1:]
                    contents = expr[1:-2]

                    new_sym = new_symbol(grammar)
                    expansion = grammar[nonterminal][i].replace(
                        expr, new_sym + operator, 1)
                    grammar[nonterminal][i] = expansion
                    grammar[new_sym] = [contents]

    return grammar

def convert_ebnf_grammar(ebnf_grammar):
    """
    Convert a grammar in extended BNF to BNF
    """
    return convert_ebnf_operators(convert_ebnf_parentheses(ebnf_grammar))

def convert_ebnf_operators(ebnf_grammar):
    """
    Convert the operators in extended BNF to BNF
    """
    grammar = extend_grammar(ebnf_grammar)
    for nonterminal in ebnf_grammar:
        expansions = ebnf_grammar[nonterminal]

        for i in range(len(expansions)):
            expansion = expansions[i]
            extended_symbols = extended_nonterminals(expansion)

            for extended_symbol in extended_symbols:
                operator = extended_symbol[-1:]
                original_symbol = extended_symbol[:-1]

                new_sym = new_symbol(grammar, original_symbol)
                grammar[nonterminal][i] = grammar[nonterminal][i].replace(
                    extended_symbol, new_sym, 1)

                if operator == '?':
                    grammar[new_sym] = ["", original_symbol]
                elif operator == '*':
                    grammar[new_sym] = ["", original_symbol + new_sym]
                elif operator == '+':
                    grammar[new_sym] = [
                        original_symbol, original_symbol + new_sym]

    return grammar

def extend_grammar(grammar, extension={}):
    new_grammar = copy.deepcopy(grammar)
    new_grammar.update(extension)
    return new_grammar

def parenthesized_expressions(expansion):
    if isinstance(expansion, tuple):
        expansion = expansion[0]

    return re.findall(RE_PARENTHESIZED_EXPR, expansion)


def new_symbol(grammar, symbol_name=symbol_name):
    """
    Return a new symbol for `grammar` based on `symbol_name`
    """
    if symbol_name not in grammar:
        return symbol_name

    count = 1
    while True:
        tentative_symbol_name = symbol_name[:-1] + "-" + repr(count) + ">"
        if tentative_symbol_name not in grammar:
            return tentative_symbol_name
        count += 1

def is_nonterminal(s):
    return re.match(RE_NONTERMINAL, s)

def nonterminals(expansion):
    if isinstance(expansion, tuple):
        expansion = expansion[0]

    return re.findall(RE_NONTERMINAL, expansion)

def extended_nonterminals(expansion):
    if isinstance(expansion, tuple):
        expansion = expansion[0]

    return re.findall(RE_EXTENDED_NONTERMINAL, expansion)


def reachable_nonterminals(grammar, start_symbol):
    reachable = set()

    def _find_reachable_nonterminals(grammar, symbol):
        nonlocal reachable
        reachable.add(symbol)
        for expansion in grammar.get(symbol, []):
            for nonterminal in nonterminals(expansion):
                if nonterminal not in reachable:
                    _find_reachable_nonterminals(grammar, nonterminal)

    _find_reachable_nonterminals(grammar, start_symbol)
    return reachable

def unreachable_nonterminals(grammar, start_symbol):
    return grammar.keys() - reachable_nonterminals(grammar, start_symbol)


def def_used_nonterminals(grammar, start_symbol):
    defined_nonterminals = set()
    used_nonterminals = {start_symbol}

    for defined_nonterminal in grammar:
        defined_nonterminals.add(defined_nonterminal)
        expansions = grammar[defined_nonterminal]
        if not isinstance(expansions, list):
            print(repr(defined_nonterminal) + ": expansion is not a list")
            return None, None

        if len(expansions) == 0:
            print(repr(defined_nonterminal) + ": expansion list empty")
            return None, None

        for expansion in expansions:
            if isinstance(expansion, tuple):
                expansion = expansion[0]
            if not isinstance(expansion, str):
                print(repr(defined_nonterminal) + ": " + repr(expansion) + ": not a string")
                return None, None

            for used_nonterminal in nonterminals(expansion):
                used_nonterminals.add(used_nonterminal)

    return defined_nonterminals, used_nonterminals


def is_valid_grammar(grammar, start_symbol):
    defined_nonterminals, used_nonterminals = def_used_nonterminals(grammar, start_symbol)
    if defined_nonterminals is None or used_nonterminals is None:
        return False

    # Do not complain about '<start>' being not used,
    # even if start_symbol is different
    if start_symbol in grammar:
        used_nonterminals.add(start_symbol)

    for unused_nonterminal in defined_nonterminals - used_nonterminals:
        print(repr(unused_nonterminal) + ": defined, but not used")

    for undefined_nonterminal in used_nonterminals - defined_nonterminals:
        print(repr(undefined_nonterminal) + ": used, but not defined")

    # Symbols must be reachable either from <start> or given start symbol
    unreachable = unreachable_nonterminals(grammar, start_symbol)
    msg_start_symbol = start_symbol
    if start_symbol in grammar:
        unreachable = unreachable - \
            reachable_nonterminals(grammar, start_symbol)
        if start_symbol != start_symbol:
            msg_start_symbol += " or " + start_symbol
    for unreachable_nonterminal in unreachable:
        print(repr(unreachable_nonterminal) + ": unreachable from " + msg_start_symbol)

    return used_nonterminals == defined_nonterminals and len(unreachable) == 0

def check_grammar(grammar, start_symbol):
        assert start_symbol in grammar
        assert is_valid_grammar(
            grammar,
            start_symbol=start_symbol)

def exp_string(expansion):
    """
    Return the string to be expanded
    """
    if isinstance(expansion, str):
        return expansion
    return expansion[0]

__all__ = ["create_grammar", "grammar_to_gpb", "check_grammar"]
