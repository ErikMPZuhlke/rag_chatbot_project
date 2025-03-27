import os
from tree_sitter import Language, Parser
import tree_sitter_c_sharp as tscsharp

class CSharpASTProcessor:
    def __init__(self):
        # Compile the C# language for Tree-sitter
        self.CSHARP_LANGUAGE = Language(tscsharp.language())
        self.parser = Parser(self.CSHARP_LANGUAGE)

        # Tree-sitter queries for C# namespaces, classes, and methods
        self.namespace_query = self.CSHARP_LANGUAGE.query("""
            (namespace_declaration
                name: [(identifier) (qualified_name)] @namespace.name
            ) @namespace.def
        """)

        self.class_query = self.CSHARP_LANGUAGE.query("""
            (class_declaration
                name: (identifier) @class.name
            ) @class.def
        """)

        self.struct_query = self.CSHARP_LANGUAGE.query("""
            (struct_declaration
                name: (identifier) @struct.name
            ) @struct.def
        """)

        self.method_query = self.CSHARP_LANGUAGE.query("""
            (method_declaration
                name: (identifier) @method.name
            ) @method.def
        """)

    def process_source_dir(self, source_dir):
        """Iterate over .cs files in the source directory and extract data"""
        results = {'namespaces': [], 'classes': [], 'methods': []}
        for root, _, files in os.walk(os.path.normpath(os.path.abspath(source_dir))):
            for file in files:
                if file.endswith(".cs"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()

                    print(f"\nProcessing file: {file_path}")
                    file_results = self._parse_abstract_syntax_tree(file_path, code)
                    results['namespaces'].extend(file_results['namespaces'])
                    results['classes'].extend(file_results['classes'])
                    results['methods'].extend(file_results['methods'])

        return results

    def _parse_abstract_syntax_tree(self, filename, code):
        """Parse C# code and extract namespace definitions"""
        tree = self.parser.parse(code.encode('utf8'))
        root_node = tree.root_node
        results = {'namespaces': [], 'classes': [], 'methods': []}

        for _, match in self.namespace_query.matches(root_node):
            captures = {name: node[0] for name, node in match.items()}
            namespace_name = captures['namespace.name'].text.decode('utf8')
            results['namespaces'].append({
                'name': namespace_name,
            })
            self._extract_classes(filename, captures['namespace.def'], results)

        return results

    def _extract_classes(self, filename, namespaceNode, results):
        """Extract class definitions from a namespace node"""
        for _, match in self.class_query.matches(namespaceNode) + self.struct_query.matches(namespaceNode):
            captures = {name: node[0] for name, node in match.items()}
            if 'class.name' in captures:
                class_name = captures['class.name'].text.decode('utf8')
                node_def = captures['class.def']
            elif 'struct.name' in captures:
                class_name = captures['struct.name'].text.decode('utf8')
                node_def = captures['struct.def']
            else:
                continue
            results['classes'].append({
                'name': class_name,
                'filename': filename,
                'docstring': self._extract_docstring(node_def),
                'namespace': namespaceNode.children_by_field_name('name')[0].text.decode('utf8')
            })
            self._extract_methods(filename, class_name, node_def, results)

    def _extract_methods(self, filename, className, classNode, results):
        """Extract method definitions from a class node"""
        for _, match in self.method_query.matches(classNode):
            captures = {name: node[0] for name, node in match.items()}
            method_name = captures['method.name'].text.decode('utf8')
            method_code = captures['method.def'].text.decode('utf8')
            results['methods'].append({
                'name': method_name,
                'docstring': self._extract_docstring(captures['method.def']),
                'class': className,
                'code': method_code
            })

    def _extract_docstring(self, node):
        """Extracts comments above a method as docstring."""
        if node.prev_sibling and node.prev_sibling.type == "comment":
            return node.prev_sibling.text.decode("utf-8")
        return ""