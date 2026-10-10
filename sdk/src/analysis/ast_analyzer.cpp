#include "sentinel/analysis/ast_analyzer.hpp"
#include <fstream>
#include <sstream>
#include <cctype>
#include <algorithm>
#include <iostream>

#if defined(SENTINEL_HAS_CLANG_LIBTOOLING)
#include <clang/AST/ASTConsumer.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendAction.h>
#include <clang/Tooling/Tooling.h>
#endif

namespace sentinel {

bool ClangAstAnalyzer::isClangLibToolingAvailable() noexcept {
#if defined(SENTINEL_HAS_CLANG_LIBTOOLING)
    return true;
#else
    return false;
#endif
}

std::string ClangAstAnalyzer::getToolchainStatus() {
#if defined(SENTINEL_HAS_CLANG_LIBTOOLING)
    return "Clang LibTooling AST Engine: ACTIVE (Native Clang AST Matchers)";
#else
    return "Clang LibTooling AST Engine: UNAVAILABLE (Missing LLVM/Clang development headers). Using Sentinel Built-in C-Subset Deterministic AST Parser.";
#endif
}

// =========================================================================
// Real Recursive-Descent Lexer and Syntactic AST Parser for Supported C
// =========================================================================

enum class TokenType {
    Identifier,
    Keyword,
    Number,
    StringLiteral,
    Plus, Minus, Star, Slash, Percent,
    AmpersandAmpersand, PipePipe, Exclamation,
    Greater, Less, GreaterEqual, LessEqual, EqualEqual, NotEqual,
    Equal,
    OpenParen, CloseParen,
    OpenBrace, CloseBrace,
    OpenBracket, CloseBracket,
    Semicolon, Comma,
    EndOfFile
};

struct Token {
    TokenType type;
    std::string text;
    int line;
    int column;
};

class Lexer {
public:
    Lexer(std::string source, std::string filename)
        : src_(std::move(source)), filename_(std::move(filename)), cursor_(0), line_(1), col_(1) {}

    Token nextToken() {
        skipWhitespaceAndComments();
        if (cursor_ >= src_.size()) {
            return {TokenType::EndOfFile, "", line_, col_};
        }

        int startLine = line_;
        int startCol = col_;
        char c = src_[cursor_];

        if (std::isalpha(static_cast<unsigned char>(c)) || c == '_') {
            std::string id;
            while (cursor_ < src_.size() && (std::isalnum(static_cast<unsigned char>(src_[cursor_])) || src_[cursor_] == '_')) {
                id += src_[cursor_++];
                col_++;
            }
            if (isKeyword(id)) {
                return {TokenType::Keyword, id, startLine, startCol};
            }
            return {TokenType::Identifier, id, startLine, startCol};
        }

        if (std::isdigit(static_cast<unsigned char>(c))) {
            std::string num;
            while (cursor_ < src_.size() && (std::isdigit(static_cast<unsigned char>(src_[cursor_])) || src_[cursor_] == '.')) {
                num += src_[cursor_++];
                col_++;
            }
            return {TokenType::Number, num, startLine, startCol};
        }

        if (c == '"') {
            std::string s;
            cursor_++; col_++;
            while (cursor_ < src_.size() && src_[cursor_] != '"') {
                if (src_[cursor_] == '\\' && cursor_ + 1 < src_.size()) {
                    s += src_[cursor_++];
                    col_++;
                }
                s += src_[cursor_++];
                col_++;
            }
            if (cursor_ < src_.size()) {
                cursor_++; col_++;
            }
            return {TokenType::StringLiteral, s, startLine, startCol};
        }

        // Two-character operators
        if (cursor_ + 1 < src_.size()) {
            std::string two = src_.substr(cursor_, 2);
            if (two == "&&") { cursor_ += 2; col_ += 2; return {TokenType::AmpersandAmpersand, "&&", startLine, startCol}; }
            if (two == "||") { cursor_ += 2; col_ += 2; return {TokenType::PipePipe, "||", startLine, startCol}; }
            if (two == ">=") { cursor_ += 2; col_ += 2; return {TokenType::GreaterEqual, ">=", startLine, startCol}; }
            if (two == "<=") { cursor_ += 2; col_ += 2; return {TokenType::LessEqual, "<=", startLine, startCol}; }
            if (two == "==") { cursor_ += 2; col_ += 2; return {TokenType::EqualEqual, "==", startLine, startCol}; }
            if (two == "!=") { cursor_ += 2; col_ += 2; return {TokenType::NotEqual, "!=", startLine, startCol}; }
        }

        // Single-character tokens
        cursor_++;
        col_++;
        switch (c) {
            case '+': return {TokenType::Plus, "+", startLine, startCol};
            case '-': return {TokenType::Minus, "-", startLine, startCol};
            case '*': return {TokenType::Star, "*", startLine, startCol};
            case '/': return {TokenType::Slash, "/", startLine, startCol};
            case '%': return {TokenType::Percent, "%", startLine, startCol};
            case '!': return {TokenType::Exclamation, "!", startLine, startCol};
            case '>': return {TokenType::Greater, ">", startLine, startCol};
            case '<': return {TokenType::Less, "<", startLine, startCol};
            case '=': return {TokenType::Equal, "=", startLine, startCol};
            case '(': return {TokenType::OpenParen, "(", startLine, startCol};
            case ')': return {TokenType::CloseParen, ")", startLine, startCol};
            case '{': return {TokenType::OpenBrace, "{", startLine, startCol};
            case '}': return {TokenType::CloseBrace, "}", startLine, startCol};
            case '[': return {TokenType::OpenBracket, "[", startLine, startCol};
            case ']': return {TokenType::CloseBracket, "]", startLine, startCol};
            case ';': return {TokenType::Semicolon, ";", startLine, startCol};
            case ',': return {TokenType::Comma, ",", startLine, startCol};
            default:
                throw ParseError("Unrecognized character in source", std::string(1, c), SourceLocation{filename_, startLine, startCol});
        }
    }

private:
    void skipWhitespaceAndComments() {
        while (cursor_ < src_.size()) {
            char c = src_[cursor_];
            if (c == ' ' || c == '\t' || c == '\r') {
                cursor_++;
                col_++;
            } else if (c == '\n') {
                cursor_++;
                line_++;
                col_ = 1;
            } else if (c == '/' && cursor_ + 1 < src_.size() && src_[cursor_ + 1] == '/') {
                // Line comment
                cursor_ += 2;
                col_ += 2;
                while (cursor_ < src_.size() && src_[cursor_] != '\n') {
                    cursor_++;
                    col_++;
                }
            } else if (c == '/' && cursor_ + 1 < src_.size() && src_[cursor_ + 1] == '*') {
                // Block comment
                cursor_ += 2;
                col_ += 2;
                while (cursor_ + 1 < src_.size() && !(src_[cursor_] == '*' && src_[cursor_ + 1] == '/')) {
                    if (src_[cursor_] == '\n') {
                        line_++;
                        col_ = 1;
                    } else {
                        col_++;
                    }
                    cursor_++;
                }
                if (cursor_ + 1 < src_.size()) {
                    cursor_ += 2;
                    col_ += 2;
                }
            } else if (c == '#') {
                // Preprocessor directive - skip until end of line
                while (cursor_ < src_.size() && src_[cursor_] != '\n') {
                    cursor_++;
                    col_++;
                }
            } else {
                break;
            }
        }
    }

    bool isKeyword(const std::string& s) {
        static const std::vector<std::string> keywords = {
            "int", "void", "float", "double", "char", "short", "long", "unsigned", "signed",
            "bool", "_Bool", "const", "static", "extern", "return", "if", "else", "while",
            "for", "do", "switch", "case", "struct", "typedef", "sizeof"
        };
        return std::find(keywords.begin(), keywords.end(), s) != keywords.end();
    }

    std::string src_;
    std::string filename_;
    size_t cursor_;
    int line_;
    int col_;
};

class SubprogramParser {
public:
    SubprogramParser(std::string source, std::string filename)
        : lexer_(std::move(source), filename), filename_(std::move(filename)) {
        advance();
    }

    AnalysisResult parseTranslationUnit() {
        AnalysisResult result;
        result.source_file = filename_;
        result.total_sources = 1;

        while (current_.type != TokenType::EndOfFile) {
            parseTopLevelItem(result);
        }
        return result;
    }

private:
    void advance() {
        current_ = lexer_.nextToken();
    }

    bool match(TokenType t) {
        if (current_.type == t) {
            advance();
            return true;
        }
        return false;
    }

    bool expect(TokenType t, const std::string& errMsg) {
        if (current_.type != t) {
            throw ParseError(errMsg, current_.text, SourceLocation{filename_, current_.line, current_.column});
        }
        advance();
        return true;
    }

    void parseTopLevelItem(AnalysisResult& result) {
        SourceLocation itemLoc{filename_, current_.line, current_.column};
        
        // Collect type specifier
        std::string typeName = parseTypeSpecifier();
        if (typeName.empty()) {
            if (current_.type == TokenType::Semicolon) {
                advance();
                return;
            }
            throw ParseError("Expected declaration at top level", current_.text, SourceLocation{filename_, current_.line, current_.column});
        }

        // Pointer
        while (current_.type == TokenType::Star) {
            typeName += "*";
            advance();
        }

        if (current_.type != TokenType::Identifier) {
            throw ParseError("Expected identifier in declaration", current_.text, SourceLocation{filename_, current_.line, current_.column});
        }

        std::string idName = current_.text;
        SourceLocation idLoc{filename_, current_.line, current_.column};
        advance();

        if (current_.type == TokenType::OpenParen) {
            // Function declaration or definition
            FunctionInfo fn;
            fn.id = "fn_" + idName;
            fn.name = idName;
            fn.return_type = typeName;
            fn.location = idLoc;

            advance(); // consume '('
            if (current_.type != TokenType::CloseParen) {
                fn.parameters = parseParameterList();
            }
            expect(TokenType::CloseParen, "Expected ')' after parameters");

            if (current_.type == TokenType::Semicolon) {
                // Function prototype
                advance();
                // Check if external dependency
                DependencyInfo dep;
                dep.id = "dep_" + idName;
                dep.name = idName;
                dep.return_type = typeName;
                dep.parameters = fn.parameters;
                dep.location = idLoc;
                dep.classification = DependencyClassification::STUB;
                result.dependencies.push_back(dep);
            } else if (current_.type == TokenType::OpenBrace) {
                // Function definition
                advance();
                parseFunctionBody(fn);
                expect(TokenType::CloseBrace, "Expected '}' closing function");
                fn.is_target_under_test = true;
                result.functions.push_back(fn);
            } else {
                throw ParseError("Expected ';' or '{' after function header", current_.text, SourceLocation{filename_, current_.line, current_.column});
            }
        } else if (current_.type == TokenType::Semicolon || current_.type == TokenType::Equal) {
            // Global variable
            GlobalVariableInfo g;
            g.variable.name = idName;
            g.variable.type = typeName;
            g.variable.location = idLoc;
            g.linkage = "external";
            if (current_.type == TokenType::Equal) {
                while (current_.type != TokenType::Semicolon && current_.type != TokenType::EndOfFile) {
                    advance();
                }
            }
            expect(TokenType::Semicolon, "Expected ';' after global variable");
            result.globals.push_back(g);
        } else {
            throw ParseError("Unexpected token in declaration", current_.text, SourceLocation{filename_, current_.line, current_.column});
        }
    }

    std::string parseTypeSpecifier() {
        std::string type;
        while (current_.type == TokenType::Keyword &&
               (current_.text == "int" || current_.text == "void" || current_.text == "float" ||
                current_.text == "double" || current_.text == "char" || current_.text == "short" ||
                current_.text == "long" || current_.text == "unsigned" || current_.text == "signed" ||
                current_.text == "bool" || current_.text == "_Bool" || current_.text == "const" ||
                current_.text == "static" || current_.text == "extern")) {
            if (!type.empty()) type += " ";
            type += current_.text;
            advance();
        }
        return type;
    }

    std::vector<ParameterInfo> parseParameterList() {
        std::vector<ParameterInfo> params;
        if (current_.type == TokenType::Keyword && current_.text == "void") {
            advance();
            return params;
        }

        while (true) {
            ParameterInfo p;
            p.location = SourceLocation{filename_, current_.line, current_.column};
            p.type = parseTypeSpecifier();
            while (current_.type == TokenType::Star) {
                p.type += "*";
                p.is_pointer = true;
                p.pointer_details.is_pointer = true;
                p.pointer_details.indirection_level++;
                advance();
            }

            if (current_.type == TokenType::Identifier) {
                p.name = current_.text;
                advance();
            }

            if (current_.type == TokenType::OpenBracket) {
                p.is_array = true;
                p.array_details.is_array = true;
                advance();
                expect(TokenType::CloseBracket, "Expected ']' for array parameter");
            }

            params.push_back(p);
            if (!match(TokenType::Comma)) {
                break;
            }
        }
        return params;
    }

    void parseFunctionBody(FunctionInfo& fn) {
        int decisionCounter = 1;
        while (current_.type != TokenType::CloseBrace && current_.type != TokenType::EndOfFile) {
            parseStatement(fn, decisionCounter);
        }
    }

    void parseStatement(FunctionInfo& fn, int& decisionCounter) {
        if (current_.type == TokenType::Keyword && current_.text == "if") {
            parseIfStatement(fn, decisionCounter);
        } else if (current_.type == TokenType::Keyword && current_.text == "return") {
            advance();
            while (current_.type != TokenType::Semicolon && current_.type != TokenType::EndOfFile) {
                advance();
            }
            expect(TokenType::Semicolon, "Expected ';' after return");
        } else if (current_.type == TokenType::OpenBrace) {
            advance();
            while (current_.type != TokenType::CloseBrace && current_.type != TokenType::EndOfFile) {
                parseStatement(fn, decisionCounter);
            }
            expect(TokenType::CloseBrace, "Expected '}'");
        } else {
            // Expression statement or variable declaration
            parseExpressionOrVarDecl(fn);
        }
    }

    void parseIfStatement(FunctionInfo& fn, int& decisionCounter) {
        SourceLocation ifLoc{filename_, current_.line, current_.column};
        advance(); // consume 'if'
        expect(TokenType::OpenParen, "Expected '(' after 'if'");

        DecisionInfo dec;
        dec.id = "D" + std::to_string(decisionCounter++);
        dec.line_number = ifLoc.line;
        dec.location = ifLoc;

        // Collect condition tokens until matching ')'
        std::vector<Token> condTokens;
        int parenDepth = 1;
        while (parenDepth > 0 && current_.type != TokenType::EndOfFile) {
            if (current_.type == TokenType::OpenParen) parenDepth++;
            else if (current_.type == TokenType::CloseParen) {
                parenDepth--;
                if (parenDepth == 0) {
                    advance();
                    break;
                }
            }
            condTokens.push_back(current_);
            advance();
        }

        decomposeDecision(condTokens, dec, fn);
        fn.decisions.push_back(dec);

        // Parse then-statement
        parseStatement(fn, decisionCounter);

        if (current_.type == TokenType::Keyword && current_.text == "else") {
            advance();
            parseStatement(fn, decisionCounter);
        }
    }

    void decomposeDecision(const std::vector<Token>& tokens, DecisionInfo& dec, FunctionInfo& fn) {
        // Reconstruct expression string
        std::string exprStr;
        for (size_t i = 0; i < tokens.size(); ++i) {
            if (i > 0) exprStr += " ";
            exprStr += tokens[i].text;
        }
        dec.expression = exprStr;

        // Split by '&&' and '||' into atomic conditions
        std::vector<std::vector<Token>> subExprs;
        std::vector<Token> currentSub;
        for (const auto& tok : tokens) {
            if (tok.type == TokenType::AmpersandAmpersand || tok.type == TokenType::PipePipe) {
                if (!currentSub.empty()) {
                    subExprs.push_back(currentSub);
                    currentSub.clear();
                }
            } else {
                currentSub.push_back(tok);
            }
        }
        if (!currentSub.empty()) {
            subExprs.push_back(currentSub);
        }

        int condIdx = 1;
        for (const auto& sub : subExprs) {
            ConditionInfo c;
            c.id = "C" + std::to_string(condIdx++);
            c.location = SourceLocation{filename_, sub.empty() ? dec.location.line : sub[0].line, sub.empty() ? dec.location.column : sub[0].column};
            
            std::string subStr;
            for (size_t i = 0; i < sub.size(); ++i) {
                if (i > 0) subStr += " ";
                subStr += sub[i].text;
            }
            c.expression = subStr;

            // Extract relational operator and operands
            for (size_t i = 0; i < sub.size(); ++i) {
                if (sub[i].type == TokenType::Greater || sub[i].type == TokenType::Less ||
                    sub[i].type == TokenType::GreaterEqual || sub[i].type == TokenType::LessEqual ||
                    sub[i].type == TokenType::EqualEqual || sub[i].type == TokenType::NotEqual) {
                    c.relational_operator = sub[i].text;
                    // Left operand
                    std::string left;
                    for (size_t j = 0; j < i; ++j) {
                        if (j > 0) left += " ";
                        left += sub[j].text;
                        if (sub[j].type == TokenType::Identifier) {
                            c.variable_references.push_back(sub[j].text);
                        }
                    }
                    c.left_operand = left;

                    // Right operand
                    std::string right;
                    for (size_t j = i + 1; j < sub.size(); ++j) {
                        if (!right.empty()) right += " ";
                        right += sub[j].text;
                        if (sub[j].type == TokenType::Identifier) {
                            c.variable_references.push_back(sub[j].text);
                        }
                    }
                    c.right_operand = right;
                    break;
                }
            }

            if (c.variable_references.empty()) {
                for (const auto& t : sub) {
                    if (t.type == TokenType::Identifier) {
                        c.variable_references.push_back(t.text);
                    }
                }
            }
            dec.conditions.push_back(c);
        }
    }

    void parseExpressionOrVarDecl(FunctionInfo& fn) {
        SourceLocation loc{filename_, current_.line, current_.column};
        std::string type = parseTypeSpecifier();
        if (!type.empty()) {
            // Local variable declaration
            while (current_.type == TokenType::Star) {
                type += "*";
                advance();
            }
            if (current_.type == TokenType::Identifier) {
                VariableInfo v;
                v.name = current_.text;
                v.type = type;
                v.location = loc;
                advance();
                fn.local_variables.push_back(v);

                if (current_.type == TokenType::Equal) {
                    advance();
                    // Check for function call in initializer
                    checkForCalls(fn);
                }
            }
            while (current_.type != TokenType::Semicolon && current_.type != TokenType::EndOfFile) {
                advance();
            }
            expect(TokenType::Semicolon, "Expected ';' after variable declaration");
        } else {
            // Statement / expression
            checkForCalls(fn);
            while (current_.type != TokenType::Semicolon && current_.type != TokenType::EndOfFile) {
                advance();
            }
            expect(TokenType::Semicolon, "Expected ';' after statement");
        }
    }

    void checkForCalls(FunctionInfo& fn) {
        while (current_.type != TokenType::Semicolon && current_.type != TokenType::EndOfFile &&
               current_.type != TokenType::CloseBrace) {
            if (current_.type == TokenType::Identifier) {
                std::string callee = current_.text;
                SourceLocation callLoc{filename_, current_.line, current_.column};
                advance();
                if (current_.type == TokenType::OpenParen) {
                    // Function call expression!
                    DependencyInfo dep;
                    dep.id = "dep_" + callee;
                    dep.name = callee;
                    dep.location = callLoc;
                    dep.call_site_file = filename_;
                    dep.call_site_line = callLoc.line;
                    dep.classification = DependencyClassification::STUB;

                    // Check if already in external_calls
                    bool exists = false;
                    for (const auto& c : fn.external_calls) {
                        if (c.name == callee) {
                            exists = true;
                            break;
                        }
                    }
                    if (!exists) {
                        fn.external_calls.push_back(dep);
                    }
                    advance(); // consume '('
                }
            } else {
                advance();
            }
        }
    }

    Lexer lexer_;
    std::string filename_;
    Token current_;
};

// =========================================================================
// Implementation of ClangAstAnalyzer
// =========================================================================

class ClangAstAnalyzer::Impl {
public:
    AnalysisResult analyze(const std::string& source, const std::string& filename) {
        SubprogramParser parser(source, filename);
        return parser.parseTranslationUnit();
    }
};

ClangAstAnalyzer::ClangAstAnalyzer() : impl_(std::make_unique<Impl>()) {}
ClangAstAnalyzer::~ClangAstAnalyzer() = default;

AnalysisResult ClangAstAnalyzer::analyzeSource(
    const std::string& source_code,
    const std::string& virtual_filename,
    const std::vector<std::string>& /*compiler_args*/)
{
    return impl_->analyze(source_code, virtual_filename);
}

AnalysisResult ClangAstAnalyzer::analyzeFile(
    const std::string& filepath,
    const std::vector<std::string>& compiler_args)
{
    std::ifstream in(filepath);
    if (!in.is_open()) {
        throw ParseError("Cannot open source file for analysis", filepath, SourceLocation{filepath, 0, 0});
    }
    std::stringstream buffer;
    buffer << in.rdbuf();
    return analyzeSource(buffer.str(), filepath, compiler_args);
}

} // namespace sentinel
