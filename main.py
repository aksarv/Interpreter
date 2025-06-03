def indent(i):
    return " " * (4 * i)


class TokenStream:
    def __init__(self, iterable):
        if len(iterable) <= 0:
            raise ValueError("Empty iterable")
        self._iterable = iterable
        self._curr = 0

    def peek(self):
        if self._curr > len(self._iterable) - 1:
            return "EOF"
        return self._iterable[self._curr]

    def consume(self, token):
        if self._curr > len(self._iterable) - 1:
            return "EOF"
        if self._iterable[self._curr] == token:
            self._curr += 1
        else:
            raise ValueError("Expected '" + str(self._iterable[self._curr]) + "', got '" + str(token) + "'")


class Expr:
    def __init__(self, subExpr, extendExprs):
        self.subExpr = subExpr
        self.extendExprs = extendExprs


class ExtendExpr:
    def __init__(self, subExpr):
        self.subExpr = subExpr


class SubExpr:
    def __init__(self, term, extendSubExprs):
        self.term = term
        self.extendSubExprs = extendSubExprs

    def repr(self, level=0):
        return f"""{indent(level)}SubExpr(\n{self.term.repr(level=level + 1)},\n{",".join(extendSubExpr.repr(level=level + 1) for extendSubExpr in self.extendSubExprs)}\n{indent(level)})"""


class ExtendSubExpr:
    def __init__(self, sign, term):
        self.sign = sign
        self.term = term

    def repr(self, level=0):
        return f"""{indent(level)}ExtendSubExpr(\n{indent(level)}'{self.sign}',\n{self.term.repr(level=level + 1)}\n{indent(level)})"""


class Term:
    def __init__(self, factor, extendTerms):
        self.factor = factor
        self.extendTerms = extendTerms

    def repr(self, level=0):
        return f"""{indent(level)}Term(\n{self.factor.repr(level=level + 1)},\n{",".join(extendTerm.repr(level=level + 1) for extendTerm in self.extendTerms)}\n{indent(level)})"""


class ExtendTerm:
    def __init__(self, sign, factor):
        self.sign = sign
        self.factor = factor

    def repr(self, level=0):
        return f"""{indent(level)}ExtendExpr(\n{indent(level)}'{self.sign}',\n{self.factor.repr(level=level + 1)}\n{indent(level)})"""


class Number:
    def __init__(self, number):
        self.number = number

    def repr(self, level=0):
        return f"""{indent(level)}Number(\n{indent(level + 1)}{self.number}\n{indent(level)})"""


class ParenExpr:
    def __init__(self, expr):
        self.expr = expr

    def repr(self, level=0):
        return f"""{indent(level)}ParenExpr(\n{self.expr.repr(level=level + 1)}\n{indent(level)})"""


class Variable:
    def __init__(self, identifier, expr):
        self.identifier = identifier
        self.expr = expr


class Error(Exception):
    def __init__(self, message):
        super().__init__(message)


class Conditional:
    def __init__(self, expr, statements):
        self.expr = expr
        self.statements = statements


class Builtin:
    def __init__(self, identifier, args):
        self.identifier = identifier
        self.args = args


class Interpreter:
    def __init__(self):
        self.tokens = []
        self.pos = 0
        self.globals = {}
        self.builtins = {
            "max": (lambda a, b: a if a >= b else b)
        }

    def nextToken(self):
        if self.pos >= len(self.tokens):
            return "EOF"
        return self.tokens[self.pos]

    def nextNextToken(self):
        if self.pos + 1 >= len(self.tokens):
            return "EOF"
        return self.tokens[self.pos + 1]

    def eat(self, token):
        if self.nextToken() != token:
            if token == ")":
                raise SyntaxError(f'unmatched parentheses')
            elif token == "(":
                raise SyntaxError(f"unexpected left parenthesis")
            else:
                raise SyntaxError(f"invalid syntax")
        self.pos += 1

    def parseString(self):
        string = ""
        while self.nextToken() != "EOF" and self.nextToken().isalpha():
            char = self.nextToken()
            string += char
            self.eat(char)
        return string

    def parseNumber(self):
        string = ""
        if self.nextToken() == "-":
            sign = "-"
            self.eat("-")
        else:
            sign = "+"
        while self.nextToken() != "EOF" and (self.nextToken().isnumeric() or self.nextToken() == "."):
            char = self.nextToken()
            string += char
            self.eat(char)
        return sign + string

    def parseAssignment(self):
        identifier = self.parseString()
        self.eat("=")
        expr = self.parseExpr()
        self.globals[identifier] = expr

    def parseExpr(self):
        initialSubExpr = self.parseSubExpr()
        extendExprs = []
        while self.nextToken() == "=" and self.nextNextToken() == "=":
            self.eat("=")
            self.eat("=")
            extendExprs.append(ExtendExpr(self.parseSubExpr()))
        return Expr(initialSubExpr, extendExprs)

    def parseSubExpr(self):
        initialTerm = self.parseTerm()
        extendSubExprs = []
        while self.nextToken() in ['+', '-']:
            sign = self.nextToken()
            self.eat(sign)
            extendSubExprs.append(ExtendSubExpr(sign, self.parseTerm()))
        return SubExpr(initialTerm, extendSubExprs)

    def parseTerm(self):
        initialFactor = self.parseFactor()
        extendTerms = []
        while self.nextToken() in ['*', '/']:
            sign = self.nextToken()
            self.eat(sign)
            extendTerms.append(ExtendTerm(sign, self.parseFactor()))
        return Term(initialFactor, extendTerms)

    def parseFactor(self):
        nextToken = self.nextToken()
        if nextToken.isnumeric():
            number = self.parseNumber()
            return Number(number)
        elif nextToken == "(":
            self.eat('(')
            parenExpr = self.parseExpr()
            self.eat(')')
            return ParenExpr(parenExpr)
        elif nextToken.isalpha():
            identifier = self.parseString()
            if self.nextToken() == "(":
                if self.nextNextToken() == ")":
                    self.eat("(")
                    self.eat(")")
                    return Builtin(identifier, [])
                else:
                    self.eat("(")
                    args = []
                    while True:
                        args.append(self.parseExpr())
                        if self.nextToken() == ")":
                            break
                        else:
                            self.eat(",")
                    self.eat(")")
                    return Builtin(identifier, args)
            try:
                return Variable(identifier, self.globals[identifier])
            except KeyError:
                raise Error("Undefined global variable referenced before assignment")

    def evaluateExpr(self, expr):
        prevValue = self.evaluateSubExpr(expr.subExpr)
        for extendExpr in expr.extendExprs:
            nextValue = self.evaluateSubExpr(extendExpr.subExpr)
            if prevValue != nextValue:
                return 0
            prevValue = nextValue
        return 1 if expr.extendExprs else prevValue

    def evaluateSubExpr(self, subExpr):
        initialTerm = self.evaluateTerm(subExpr.term)
        for extendSubExpr in subExpr.extendSubExprs:
            if extendSubExpr.sign == "+":
                initialTerm += self.evaluateTerm(extendSubExpr.term)
            elif extendSubExpr.sign == "-":
                initialTerm -= self.evaluateTerm(extendSubExpr.term)
        return initialTerm

    def evaluateTerm(self, term):
        initialFactor = self.evaluateFactor(term.factor)
        for extendTerm in term.extendTerms:
            if extendTerm.sign == "*":
                initialFactor *= self.evaluateFactor(extendTerm.factor)
            elif extendTerm.sign == "/":
                initialFactor /= self.evaluateFactor(extendTerm.factor)
        return initialFactor

    def evaluateFactor(self, factor):
        if isinstance(factor, Number):
            return float(factor.number)
        elif isinstance(factor, ParenExpr):
            return self.evaluateExpr(factor.expr)
        elif isinstance(factor, Variable):
            return self.evaluateExpr(factor.expr)
        elif isinstance(factor, Builtin):
            return self.builtins[factor.identifier](*[self.evaluateExpr(x) for x in factor.args])


interpreter = Interpreter()

while True:
    line = input(">>> ")
    if line == "exit()" or line == "quit()":
        break
    interpreter.tokens = list(line.replace(" ", ""))
    interpreter.pos = 0
    try:
        interpreter.parseAssignment()
    except SyntaxError:
        interpreter.tokens = list(line.replace(" ", ""))
        interpreter.pos = 0
        parsed = interpreter.parseExpr()
        print(interpreter.evaluateExpr(parsed))
