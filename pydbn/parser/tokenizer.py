import re

from structures import DBNToken

class DBNTokenizer:

    def __init__(self):
        """
        initializes the tokenizer to a newborn state,
        then registers the DBNTokenTypes
        """
        self.type_re_pairs = []
        self.raw_patterns = []

        # comment, whitespace garbage first
        self.register('COMMENT',      r'//(.+)')

        # then path - above whitespace because of the lookbehind
        self.register('PATH',         r'(?<=Load)\s+([\w\.\\/\-]+)')

        # then real whitespace
        self.register('WHITESPACE',   r'[^\S\n]+')

        # operators next
        self.register('OPERATOR',     r'([*\-/+])')

        # the groupers
        self.register('OPENPAREN',    r'(\()')
        self.register('OPENBRACKET',  r'(\[)')
        self.register('OPENBRACE',    r'({)')
        self.register('CLOSEPAREN',   r'(\))')
        self.register('CLOSEBRACKET', r'(\])')
        self.register('CLOSEBRACE',   r'(})')

        # then keywords
        self.register('SET',          r'(Set)')
        self.register('REPEAT',       r'(Repeat)')
        self.register('QUESTION',     r'(Same|NotSame|Smaller|NotSmaller)\?'),
        self.register('COMMAND',      r'(Command)'),
        self.register('LOAD',         r'(Load)'),

        # then literals
        self.register('WORD',         r'([A-z_][\w\d]*)')
        self.register('NUMBER',       r'(\d+)')

        # then newline (command seperator)
        self.register('NEWLINE',      r'\n')

        # then everything else... we need this to catch illegal tokens
        self.register(None,           r".")

    def register(self, type_, type_pattern):
        """
        registers the token with type string type_
        and the pattern string type_pattern

        if type_ is None, then it will not be registered as
        a token type for classification purposes
        """
        self.raw_patterns.append(type_pattern)

        if type_ is not None:
            type_re = re.compile(type_pattern)
            type_re_pair = (type_, type_re)
            self.type_re_pairs.append(type_re_pair)

        return self

    def classify(self, string, pos):
        """
        given a string and a position where a token match has been found,
        returns a tuple of its (type_, value)
        we try token types in the order they were registered
        """
        for type_, type_re in self.type_re_pairs:
            match = type_re.match(string, pos)
            if match:
                try:
                    value = match.group(1)
                except IndexError:
                    value = ''
                return (type_, value)

        raise ValueError("No matching token type for token at pos %d (%s)" % (pos, string[pos:pos+10]))

    def token_re(self):
        """
        returns a re matching all token types (in order)
        """
        token_pattern = "|".join(self.raw_patterns)
        return re.compile(token_pattern)

    def tokenizeiter(self, string):
        """
        returns a generator that will yield tokens!
        """

        line_no = 1

        # the absolute character number at which the current line begins:
        line_start_char_no = 0

        token_re = self.token_re()
        token_string_iter = token_re.finditer(string)

        for token_match in token_string_iter:
            token_string = token_match.group(0)  # the whole matching string

            # character number of the token; plus 1 becaue of 0 indexing
            token_char_no = token_match.start() - line_start_char_no + 1

            try:
                token_type, token_value = self.classify(string, token_match.start())
            except ValueError as e:
                raise ValueError(str(e) + " at %d:%d" % (line_no, token_char_no))

            token = DBNToken(
                token_type,
                token_value,
                line_no,
                token_char_no,
                token_string
            )

            if token.type == 'NEWLINE':
                line_no += 1
                line_start_char_no = token_match.end()

            if not token.type == 'WHITESPACE' and not token.type == 'COMMENT':
                yield token

        # always yield an extra newline
        yield DBNToken(
            'NEWLINE',
            '\n',
            -1,
            -1,
            '\n',
        )

        raise StopIteration

    def tokenize(self, string):
        return list(self.tokenizeiter(string))