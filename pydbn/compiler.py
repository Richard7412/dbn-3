from dbnast import *

class DBNCompiler:
    
    def __init__(self, counter=0, module=False):
        self.bytecodes = []
        self.module = module
        self.counter = counter
        self.start = counter
    
    def add(self, code, arg='_'):
        self.bytecodes.append((code, arg))
        self.counter += 1
        return self
    
    def add_set_line_no_unless_module(self, line_no):
        if not self.module:
            self.add('SET_LINE_NO', line_no)

    def extend(self, other):
        for bc in other.bytecodes:
            self.add(*bc)

    def compile(self, node, offset=0):
        new = DBNCompiler(counter=self.counter + offset, module=self.module)

        compile_command_name = "compile_%s_node" % node.type

        try:
            compile_command = getattr(new, compile_command_name)
        except AttributeError:
            raise ValueError("Unknown node type! (%s)" % str(type(node)))
        else:
            compile_command(node)
            return new

    def compile_program_node(self, node):
        self.compile_block_node(node)
        if not self.module:
            self.add('END')
        
    def compile_block_node(self, node):
        for sub_node in node.children:
            self.extend(self.compile(sub_node))

    def compile_set_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)

        self.extend(self.compile(node.right))
        left = node.left

        # If left is a bracket, its a store_bracket op
        if   isinstance(left, DBNBracketNode):
            # Peer inside the bracket
            bracket_left, bracket_right = left.children
            
            self.extend(self.compile(bracket_right))
            self.extend(self.compile(bracket_left))

            self.add('SET_DOT')

        elif isinstance(left, DBNWordNode):
            self.add('STORE', left.name)

    def compile_repeat_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)

        # push on end
        self.extend(self.compile(node.end))
        # push on start
        self.extend(self.compile(node.start))

        # body entry - [end, current]
        body_entry = self.counter

        # dup current for store
        self.add('DUP_TOPX', 1)
        self.add('STORE', node.var.name)

        self.extend(self.compile(node.body))

        # dup [end, current] for comparison
        self.add('DUP_TOPX', 2)

        # compare
        self.add('COMPARE_SAME')
        # now stack is [end, current, current<end]
        # if current is the same as end, lets GTFO
        skip_count = 8
        self.add('POP_JUMP_IF_TRUE', self.counter + skip_count + 1)

        # if we are here, we need either to increment or decrement
        self.add('DUP_TOPX', 2)
        self.add('COMPARE_SMALLER')
        self.add('POP_JUMP_IF_FALSE', self.counter + 3) # the else
        
        self.add('LOAD_INTEGER', 1)
        self.add('JUMP', self.counter + 2)
        
        self.add('LOAD_INTEGER', -1)

        # ok if we are here, we are good to increment (decrement) and repeat
        # (these are the ones counted in skip_count)
        self.add('BINARY_ADD')
        self.add('JUMP', body_entry)

        # ok, now this stuff is cleanup - pop away
        self.add('POP_TOPX', 2)

    def compile_question_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)

        self.extend(self.compile(node.right))
        self.extend(self.compile(node.left))

        questions = {
            'Same': 'COMPARE_SAME',
            'NotSame': 'COMPARE_NSAME',
            'Smaller': 'COMPARE_SMALLER',
            'NotSmaller': 'COMPARE_NSMALLER'
        }

        self.add(questions[node.name])

        body_code = self.compile(node.body, offset=1)

        self.add('POP_JUMP_IF_FALSE', body_code.counter)
        self.extend(body_code)

    def compile_command_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)

        # get the children on the stack in reverse order
        for arg_node in reversed(node.args):
            self.extend(self.compile(arg_node))

        # load the name of the command
        self.add('LOAD_STRING', node.name)

        # run the command!
        self.add('COMMAND', len(node.args))

        # command return value always gets thrown away
        self.add('POP_TOPX', 1)

    def compile_command_definition_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)
        # When I build Number... going to have to 
        # refactor / restructure this all i think
        # sweet

        for arg in reversed(node.args):
            self.add('LOAD_STRING', arg.name)

        self.add('LOAD_STRING', node.command_name.name)

        body_code = self.compile(node.body, offset = 3)

        self.add('LOAD_INTEGER', body_code.start)
        self.add('DEFINE_COMMAND', len(node.args))

        # Implicitly add Return 0
        # if not node.has_return_value
        body_code.add('LOAD_INTEGER', 0)
        body_code.add('RETURN')

        after_body = body_code.counter
        self.add('JUMP', after_body)
        self.extend(body_code)

    def compile_load_node(self, node):
        self.add_set_line_no_unless_module(node.line_no)
        self.add('LOAD_CODE', node.name)

    def compile_bracket_node(self, node):
        self.extend(self.compile(node.right))
        self.extend(self.compile(node.left))

        self.add('GET_DOT')

    def compile_binary_op_node(self, node):
        self.extend(self.compile(node.right))
        self.extend(self.compile(node.left))        

        ops = {
            '+': 'BINARY_ADD',
            '-': 'BINARY_SUB',
            '/': 'BINARY_DIV',
            '*': 'BINARY_MUL',
        }
        self.add(ops[node.name])

    def compile_number_node(self, node):
        self.add('LOAD_INTEGER', node.name)

    def compile_word_node(self, node):
        self.add('LOAD', node.name)
    
    def compile_noop_node(self, node):
        pass #NOOP



    