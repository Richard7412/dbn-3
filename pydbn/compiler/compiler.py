import structures
from parser.structures.ast_nodes import *
from parser import DBNAstVisitor


class DBNCompiler(DBNAstVisitor):

    def __init__(self, module=False):
        self.code = []
        self.module = module

        # stuff for labels
        self.label_prefix_counts = {}

    def add(self, code, arg='_'):
        self.code.append(structures.Bytecode(code, arg))
        return self

    def add_set_line_no_unless_module(self, line_no):
        if not self.module:
            self.add('SET_LINE_NO', line_no)

    def generate_label(self, prefix):
        """
        generates a unique label for given prefix
        """
        count = self.label_prefix_counts.get(prefix, 0)
        label_name = "%s_%d" % (prefix, count)
        self.label_prefix_counts[prefix] = count + 1
        return structures.Label(label_name)

    def add_label(self, label):
        """
        does not generate a label
        """
        self.code.append(label)

    def compile(self, node):
        self.visit(node)
        return self.code

    def visit_program_node(self, node):
        self.visit_block_node(node)
        if not self.module:
            self.add('END')

    def visit_block_node(self, node):
        for sub_node in node.children:
            self.visit(sub_node)

    def visit_set_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)

        self.visit(node.right)
        left = node.left

        # If left is a bracket, its a store_bracket op
        if   isinstance(left, DBNBracketNode):
            # Peer inside the bracket
            bracket_left, bracket_right = left.children

            self.visit(bracket_right)
            self.visit(bracket_left)

            self.add('SET_DOT')

        elif isinstance(left, DBNWordNode):
            self.add('STORE', left.value)

    def visit_repeat_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)

        # push on end
        self.visit(node.end)
        # push on start
        self.visit(node.start)

        # body entry - [end, current]
        body_entry_label = self.generate_label('repeat_body_entry')
        repeat_end_label = self.generate_label('repeat_end')

        # mark current location
        self.add_label(body_entry_label)

        # dup current for store
        self.add('DUP_TOPX', 1)
        self.add('STORE', node.var.value)

        self.visit(node.body)

        # dup [end, current] for comparison
        self.add('DUP_TOPX', 2)

        # compare
        self.add('COMPARE_SAME')
        # now stack is [end, current, current<end]
        # if current is the same as end, lets GTFO
        self.add('POP_JUMP_IF_TRUE', repeat_end_label)

        # if we are here, we need either to increment or decrement
        repeat_decrement_setup_label = self.generate_label('repeat_decrement_setup')
        repeat_step_label = self.generate_label('repeat_step')

        self.add('DUP_TOPX', 2)
        self.add('COMPARE_SMALLER')
        self.add('POP_JUMP_IF_FALSE', repeat_decrement_setup_label) # the else

        self.add('LOAD_INTEGER', 1)
        self.add('JUMP', repeat_step_label)

        self.add_label(repeat_decrement_setup_label)
        self.add('LOAD_INTEGER', -1)

        # ok if we are here, we are good to increment (decrement) and repeat
        # (these are the ones counted in skip_count)
        self.add_label(repeat_step_label)
        self.add('BINARY_ADD')
        self.add('JUMP', body_entry_label)

        # ok, now this stuff is cleanup - pop away
        self.add_label(repeat_end_label)
        self.add('POP_TOPX', 2)

    def visit_question_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)

        self.visit(node.right)
        self.visit(node.left)

        questions = {
            'Same': 'COMPARE_SAME',
            'NotSame': 'COMPARE_NSAME',
            'Smaller': 'COMPARE_SMALLER',
            'NotSmaller': 'COMPARE_NSMALLER'
        }

        self.add(questions[node.value])

        after_body_label = self.generate_label('question_after_body')

        self.add('POP_JUMP_IF_FALSE', after_body_label)
        self.visit(node.body)
        self.add_label(after_body_label)

    def visit_command_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)

        # get the children on the stack in reverse order
        for arg_node in reversed(node.args):
            self.visit(arg_node)

        # load the name of the command
        self.add('LOAD_STRING', node.value)

        # run the command!
        self.add('COMMAND', len(node.args))

        # command return value always gets thrown away
        self.add('POP_TOPX', 1)

    def visit_command_definition_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)
        # When I build Number... going to have to
        # refactor / restructure this all i think
        # sweet

        for arg in reversed(node.args):
            self.add('LOAD_STRING', arg.value)

        self.add('LOAD_STRING', node.command_name.value)

        command_start_label = self.generate_label('command_definition_%s' % node.command_name.value)
        after_command_label = self.generate_label('after_command_definition')

        self.add('LOAD_INTEGER', command_start_label)
        self.add('DEFINE_COMMAND', len(node.args))



        self.add('JUMP', after_command_label)

        self.add_label(command_start_label)

        self.visit(node.body)

        # Implicitly add Return 0
        # if not node.has_return_value
        self.add('LOAD_INTEGER', 0)
        self.add('RETURN')

        self.add_label(after_command_label)

    def visit_load_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)
        self.add('LOAD_CODE', node.value)

    def visit_bracket_node(self, node):
        self.visit(node.right)
        self.visit(node.left)

        self.add('GET_DOT')

    def visit_binary_op_node(self, node):
        self.visit(node.right)
        self.visit(node.left)

        ops = {
            '+': 'BINARY_ADD',
            '-': 'BINARY_SUB',
            '/': 'BINARY_DIV',
            '*': 'BINARY_MUL',
        }
        self.add(ops[node.value])

    def visit_number_node(self, node):
        self.add('LOAD_INTEGER', node.value)

    def visit_word_node(self, node):
        self.add('LOAD', node.value)

    def visit_noop_node(self, node):
        pass #NOOP