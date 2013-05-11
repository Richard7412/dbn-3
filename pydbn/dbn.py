import sys
from optparse import OptionParser

from parser import DBNParser, DBNTokenizer
from compiler import DBNCompiler, assemble
from interpreter import DBNInterpreter, builtins

import output
import threading

option_parser = OptionParser()
option_parser.add_option('-c', '--compile', action="store_true", dest="compile", help="compile code", default=False)
option_parser.add_option('-n', '--numbers', action="store_true", dest="numbers", help="show opcode numbers", default=False)

option_parser.add_option('-f', '--file', action="store", dest="filename", help="file for output", default=None)
option_parser.add_option('-t', '--trace', action="store_true", dest="trace", help="trace interpretation", default=False)

def compile_dbn(filename):
    dbn_script = open(filename).read()
    tokenizer = DBNTokenizer()
    parser = DBNParser()
    compiler = DBNCompiler()

    tokens = tokenizer.tokenize(dbn_script)
    dbn_ast = parser.parse(tokens)
    compilation = compiler.compile(dbn_ast)
    assembly = assemble(compilation)
    return assembly

def run_dbn(bytecode):
    interpreter = DBNInterpreter(bytecode)
    interpreter.load(builtins)
    interpreter.run()
    return interpreter

if __name__ == "__main__":
    (options, args) = option_parser.parse_args()

    filename = args[0]
    bytecode = compile_dbn(filename)

    if options.compile:
        for i, b in enumerate(bytecode):
            print i, b

    else:
        interpreter = DBNInterpreter(bytecode)
        interpreter.load(builtins)

        if options.filename:
            # save it
            interpreter.run(trace=options.trace)
            output.output_bmp(interpreter, options.filename)

        else:
            threading.Thread(target = lambda: interpreter.run(trace=options.trace)).start()
            output.draw_window(interpreter)
        