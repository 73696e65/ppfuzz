import re
import os

from grammar import is_nonterminal, symbol_name

def unicode_escape(s, error="backslashreplace"):
    """
    Escaping unicode characters into ASCII for user-facing strings
    """
    def ascii_chr(byte):
        if 0 <= byte <= 127:
            return chr(byte)
        return r"\x%02x" % byte

    bytes = s.encode('utf-8', error)
    return "".join(map(ascii_chr, bytes))

def extract_node(node, id):
    symbol, children, *annotation = node
    return symbol, children, ''.join(str(a) for a in annotation)

def dot_escape(s):
    """Return s in a form suitable for dot"""
    s = re.sub(r'([^a-zA-Z0-9" ])', r"\\\1", s)
    return s

def default_node_attr(dot, nid, symbol, ann):
    dot.node(repr(nid), dot_escape(unicode_escape(symbol)))

def default_edge_attr(dot, start_node, stop_node):
    dot.edge(repr(start_node), repr(stop_node))

def custom_node_attr(dot, nid, symbol, ann):
    if symbol.startswith(symbol_name[:-1]):
        dot.node(repr(nid), dot_escape(unicode_escape(symbol)), color='firebrick1', style='dashed', shape='ellipse')
    elif not len(symbol):
        dot.node(repr(nid), dot_escape(unicode_escape(symbol)), color='royalblue', shape='terminator')
    else:
        dot.node(repr(nid), dot_escape(unicode_escape(symbol)), color='orangered', style='filled', shape='box')

def default_graph_attr(dot):
    dot.attr('node', shape='plain')

def display_tree(derivation_tree,
                 log=False,
                 extract_node=extract_node,
                 node_attr=custom_node_attr,
                 edge_attr=default_edge_attr,
                 graph_attr=default_graph_attr,
                 output_prefix='output'):

    # If we import display_tree, we also have to import its functions
    from graphviz import Digraph

    counter = 0

    def traverse_tree(dot, tree, id=0):
        (symbol, children, annotation) = extract_node(tree, id)
        node_attr(dot, id, symbol, annotation)

        if children:
            for child in children:
                nonlocal counter
                counter += 1
                child_id = counter
                edge_attr(dot, id, child_id)
                traverse_tree(dot, child, child_id)

    dot = Digraph(comment="Derivation Tree")
    graph_attr(dot)
    traverse_tree(dot, derivation_tree)
    if log:
        print(dot)

    with open(f"{output_prefix}.dot", "w") as f:
        f.write(str(dot))
    os.system(f"dot -Tpdf {output_prefix}.dot -o {output_prefix}.pdf")

    return dot


def display_annotated_tree(tree, a_nodes, a_edges, log=False):
    def graph_attr(dot):
        dot.attr('node', shape='plain')
        dot.graph_attr['rankdir'] = 'LR'

    def annotate_node(dot, nid, symbol, ann):
        if nid in a_nodes:
            dot.node(repr(nid), "%s (%s)" % (dot_escape(unicode_escape(symbol)), a_nodes[nid]))
        else:
            dot.node(repr(nid), dot_escape(unicode_escape(symbol)))

    def annotate_edge(dot, start_node, stop_node):
        if (start_node, stop_node) in a_edges:
            dot.edge(repr(start_node), repr(stop_node),
                     a_edges[(start_node, stop_node)])
        else:
            dot.edge(repr(start_node), repr(stop_node))

    return display_tree(tree, log=log,
                 node_attr=annotate_node,
                 edge_attr=annotate_edge,
                 graph_attr=graph_attr)


def all_terminals(tree):
    (symbol, children) = tree
    if children is None:
        # This is a nonterminal symbol not expanded yet
        return symbol

    if len(children) == 0:
        # This is a terminal symbol
        return symbol

    # This is an expanded symbol:
    # Concatenate all terminal symbols from all children
    return ''.join([all_terminals(c) for c in children])


def tree_to_gpb(tree):
    
    result = str()

    def next_leaf(node):
        """
        True if there is no more expansion needed, which is denoted by '[]')
        eg: ('<symbol-14-1>', [('', [])])
        """
        return len(node[1][0][1]) == 0

    def next_leaf_content(node):
        """
        Return the content of "leaf", eg:
        ('<field>', [(':::STRING:::', [])]),
        """
        return node[1][0][0]

    def traverse(tree):
        """
        Traverse the tree and return a protobuf message
        """
        nonlocal result

        symbol, children, *_ = tree

        if children:
            for c in children:
                if c[0].startswith("<"):
                    if not c[0].startswith(symbol_name[:-1]):
                        if next_leaf(c):
                            result += c[0].replace("<", "").replace(">", ": ") + next_leaf_content(c) + "\n"
                        else:
                            result += c[0].replace("<", "").replace(">", "") + " {" + "\n"
                            traverse(c)
                            result += "}" + "\n"
                    else:
                        traverse(c) # do not update anything, just traverse

    traverse(tree)
    return result

def tree_to_string(tree):
    symbol, children, *_ = tree
    if children:
        return ''.join(tree_to_string(c) for c in children)
    else:
        return '' if is_nonterminal(symbol) else symbol

