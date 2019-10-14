import random
import requests
import re
import google.protobuf.text_format as tf

from functools import lru_cache
from pprint import pprint

import helper
import tree_helper
import grammar

from inject import Template
from inject_const import *
from config import replace, delete

INT32_FILE = "fuzzlist/int32.txt"
INT64_FILE = "fuzzlist/int64.txt"

# from https://github.com/fuzzdb-project/fuzzdb/blob/master/attack/all-attacks/all-attacks-unix.txt
STRING_FILE = "fuzzlist/string.txt"

class Runner():
    
    def __init__(self):
        pass

    def run(self, url, serialized):

        if len(serialized):
            r = requests.post(url=url, data=serialized)
            print(f"Status code: {r.status_code}")
            print(f"Headers: {r.headers}")
            print(f"Response: {r.text}")

class Fuzzer():

    def __init__(self):
        pass

    @lru_cache(maxsize=32)
    def read_txtfile(self, fname):
        with open(fname, "r") as f:
            data = f.read().splitlines()
        return data

    def rand_string(self):
        n = random.randint(0, 20)
        # return ''.join( [random.choice(ascii_letters + "<>") for x in range(n)] )
        # alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%&\'()*+,-./:;<=>?@[]^_`{|}~ \t\x0c"
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return ''.join( [random.choice(alphabet) for x in range(n)] )
        # return ''.join( [chr(random.randint(0, 0xff)) for x in range(n)] )

    def inject_int32(self, txt):
        FUZZ = self.read_txtfile(INT32_FILE)
        while INJECT_INT32 in txt:
            txt = txt.replace(INJECT_INT32, str(random.choice(FUZZ)), 1)
        return txt
        
    def inject_int64(self, txt):
        FUZZ = self.read_txtfile(INT64_FILE)
        while INJECT_INT64 in txt:
            txt = txt.replace(INJECT_INT64, str(random.choice(FUZZ)), 1)
        return txt

    def inject_bool(self, txt):
        while INJECT_BOOL in txt:
            txt = txt.replace(INJECT_BOOL, str(random.randint(0, 1)), 1)
        return txt

    def inject_string(self, txt):
        FUZZ = self.read_txtfile(STRING_FILE)
        while INJECT_STRING in txt:
            # txt = txt.replace(INJECT_STRING, f'"{str(random.choice(FUZZ))}"', 1)
            txt = txt.replace(INJECT_STRING, f'"{self.rand_string()}"', 1)
        return txt
            
    def inject_bytes(self, txt):
        FUZZ = self.read_txtfile(STRING_FILE)
        while INJECT_BYTES in txt:
            # txt = txt.replace(INJECT_BYTES, f'"{str(random.choice(FUZZ))}"', 1)
            txt = txt.replace(INJECT_BYTES, f'"{self.rand_string()}"', 1)
        return txt


class ProtoFuzzer(Fuzzer):

    def __init__(self, min_nonterminals=0, max_nonterminals=10, disp=False, log=False):

        self.disp = disp
        self.log = log

        self.min_nonterminals = min_nonterminals
        self.max_nonterminals = max_nonterminals

        proto_files = helper.get_proto_files()
        libs = helper.get_proto_libs(proto_files)

        if self.log:
            print("Creating grammars, please wait..")
        self.vectors = helper.create_vectors(libs)
        for v in self.vectors:
            v['grammar'] = grammar.gpb_to_ebnf(v['msg'])
            v['start_symbol'] = f'<{v["request"]}>'
            # Check if the created grammar is valid and if not, exit
            grammar.check_grammar(v['grammar'], v['start_symbol'])

    def expansion_to_children(self, expansion):
        expansion = grammar.exp_string(expansion)
        assert isinstance(expansion, str)

        if expansion == "":  # Special case: epsilon expansion
            return [("", [])]

        strings = re.split(grammar.RE_NONTERMINAL, expansion)
        return [(s, None) if grammar.is_nonterminal(s) else (s, [])
                for s in strings if len(s) > 0]

    def choose_node_expansion(self, node, possible_children):
        """
        Return index of expansion in `possible_children` to be selected.  Defaults to random.
        """
        return random.randrange(0, len(possible_children))

    def process_chosen_children(self, chosen_children, expansion):
        """
        Process children after selection.  By default, does nothing.
        """
        return chosen_children

    def any_possible_expansions(self, node):
        """
        Returns True if the tree has any unexpanded nodes
        """
        (symbol, children) = node
        if children is None:
            return True

        return any(self.any_possible_expansions(c) for c in children)

    def choose_tree_expansion(self, tree, children):
        """
        Return index of subtree in `children` to be selected for expansion.  Defaults to random.
        """
        return random.randrange(0, len(children))

    def expand_tree_once(self, tree):
        """
        Choose an unexpanded symbol in tree; expand it.  Can be overloaded in subclasses.
        """
        (symbol, children) = tree
        if children is None:
            # Expand this node
            return self.expand_node(tree)

        # Find all children with possible expansions
        expandable_children = [
            c for c in children if self.any_possible_expansions(c)]

        # `index_map` translates an index in `expandable_children`
        # back into the original index in `children`
        index_map = [i for (i, c) in enumerate(children)
                     if c in expandable_children]

        # Select a random child
        child_to_be_expanded = \
            self.choose_tree_expansion(tree, expandable_children)

        # Expand in place
        children[index_map[child_to_be_expanded]] = \
            self.expand_tree_once(expandable_children[child_to_be_expanded])

        return tree

    def expand_node_randomly(self, node):
        (symbol, children) = node
        assert children is None

        if self.log:
            print("Expanding", tree_helper.all_terminals(node), "randomly")

        # Fetch the possible expansions from grammar...
        expansions = self.v['grammar'][symbol]
        possible_children = [self.expansion_to_children(
            expansion) for expansion in expansions]

        # ... and select a random expansion
        index = self.choose_node_expansion(node, possible_children)
        chosen_children = possible_children[index]

        # Process children (for subclasses)
        chosen_children = self.process_chosen_children(chosen_children,
                                                       expansions[index])

        # Return with new children
        return (symbol, chosen_children)

    def symbol_cost(self, symbol, seen=set()):
        """
        Returns the minimum cost of all expansions of a symbol
        """
        expansions = self.v['grammar'][symbol]
        return min(self.expansion_cost(e, seen | {symbol}) for e in expansions)

    def expansion_cost(self, expansion, seen=set()):
        """
        Returns the sum of all expansions in expansions
        """
        symbols = grammar.nonterminals(expansion)
        if len(symbols) == 0:
            return 1  # no symbol

        # indicating (potentially infinite) recursion
        if any(s in seen for s in symbols):
            return float('inf')

        # the value of a expansion is the sum of all expandable variables
        # inside + 1
        return sum(self.symbol_cost(s, seen) for s in symbols) + 1

    def expand_node_by_cost(self, node, choose=min):
        """
        Determines the minimum cost cost across all children and then 
        chooses a child from the list using the choose function, which by 
        default is the minimum cost. If multiple children all have the 
        same minimum cost, it chooses randomly between these
        """
        (symbol, children) = node
        assert children is None

        # Fetch the possible expansions from grammar...
        expansions = self.v['grammar'][symbol]

        possible_children_with_cost = [(self.expansion_to_children(expansion),
                                        self.expansion_cost(
                                            expansion, {symbol}),
                                        expansion)
                                       for expansion in expansions]

        costs = [cost for (child, cost, expansion)
                 in possible_children_with_cost]
        chosen_cost = choose(costs)
        children_with_chosen_cost = [child for (child, child_cost, _) in possible_children_with_cost
                                     if child_cost == chosen_cost]
        expansion_with_chosen_cost = [expansion for (_, child_cost, expansion) in possible_children_with_cost
                                      if child_cost == chosen_cost]

        index = self.choose_node_expansion(node, children_with_chosen_cost)

        chosen_children = children_with_chosen_cost[index]
        chosen_expansion = expansion_with_chosen_cost[index]
        chosen_children = self.process_chosen_children(
            chosen_children, chosen_expansion)

        # Return with a new list
        return (symbol, chosen_children)

    def expand_node_max_cost(self, node):
        if self.log:
            print("Expanding", tree_helper.all_terminals(node), "at maximum cost")

        return self.expand_node_by_cost(node, max)

    def expand_node_min_cost(self, node):
        """The shortcut expand_node_min_cost() passes min() as the choose 
        function, which makes it expand nodes at minimum cost."""
        if self.log:
            print("Expanding", tree_helper.all_terminals(node), "at minimum cost")

        return self.expand_node_by_cost(node, min)

    def expand_tree_with_strategy(self, tree, expand_node_method, limit=None):
        """
        Expand tree using `expand_node_method` as node expansion function
        until the number of possible expansions reaches `limit`.
        """
        self.expand_node = expand_node_method
        while ((limit is None
                or self.possible_expansions(tree) < limit)
               and self.any_possible_expansions(tree)):
            tree = self.expand_tree_once(tree)
            self.log_tree(tree)
        return tree

    def possible_expansions(self, node):
        """
        Counts how many unexpanded symbols there are in a tree
        """
        (symbol, children) = node
        if children is None:
            return 1
        return sum(self.possible_expansions(c) for c in children)

    def log_tree(self, tree):
        """
        Output a tree if self.log is set; if self.display is also set, show the tree structure
        """
        if self.log:
            print("Tree:")
            pprint(tree)
            print("-" * 80)
            print(self.possible_expansions(tree), "possible expansion(s) left")

    def expand_tree(self, tree):
        """
        Expand `tree` in a three-phase strategy until all expansions are complete.
        """
        self.log_tree(tree)
        tree = self.expand_tree_with_strategy(
            tree, self.expand_node_max_cost, self.min_nonterminals)
        tree = self.expand_tree_with_strategy(
            tree, self.expand_node_randomly, self.max_nonterminals)
        tree = self.expand_tree_with_strategy(
            tree, self.expand_node_min_cost)

        assert self.possible_expansions(tree) == 0

        return tree

    def init_tree(self):
        return (self.v['start_symbol'], None)

    def fuzz_tree(self):

        tree = self.init_tree()
        
        # Expand all nonterminals
        tree = self.expand_tree(tree)
        if self.log:
            print("Final tree:")
            pprint(tree)
        if self.disp:
            tree_helper.display_tree(tree)
        return tree

    def fuzz(self):
        """
        Return fuzz input, or empty string in case of error
        """
        self.v = random.choice(self.vectors)
        print()
        print("----------------- ENDPOINTS ------------------")
        print(f"{self.v['request']} => {self.v['url']} :: {self.v['msg']}")

        derivation_tree = self.fuzz_tree()
        tmp = tree_helper.tree_to_gpb(derivation_tree)

        template = Template(tmp)
        print("----------------- TEMPLATE ------------------")
        print(template)
        print("---------------------------------------------")

        [template.delete(key) for key in delete]
        [template.set(key, value) for key, value in replace.items()]

        template.fill(self.inject_int32)
        template.fill(self.inject_int64)
        template.fill(self.inject_bool)
        template.fill(self.inject_string)
        template.fill(self.inject_bytes)

        print("----------------- SENDING -------------------")
        print(template)
        print("---------------------------------------------")
        
        try:
            msg = tf.Parse(template.text, self.v['msg']())
            serialized = msg.SerializeToString()
            return self.v['url'], serialized
        except tf.ParseError:
            print("Unable to deserialize the message")
            return '', ''

    def run(self, runner=Runner()):
        """
        Run `runner` with fuzz input
        """
        return runner.run(*self.fuzz())
