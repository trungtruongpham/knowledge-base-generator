"""C# source file parser using tree-sitter."""

import logging
from pathlib import Path
from typing import Optional

try:
    from tree_sitter import Language, Parser, Node
    import tree_sitter_c_sharp as tscsharp
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logging.warning("tree-sitter not available, C# parsing will be limited")

from kb_generator.parsers.models import (
    ClassInfo,
    PropertyInfo,
    MethodInfo,
    ConstructorInfo,
    ParameterInfo,
)

logger = logging.getLogger(__name__)


class CSharpParser:
    """Parser for C# source files using tree-sitter."""
    
    def __init__(self):
        """Initialize the C# parser."""
        if not TREE_SITTER_AVAILABLE:
            raise RuntimeError("tree-sitter-c-sharp is not installed")
        
        self.parser = Parser(Language(tscsharp.language()))
    
    def parse_file(self, file_path: Path) -> list[ClassInfo]:
        """Parse a C# file and extract all class/record/struct/interface/enum definitions.
        
        Args:
            file_path: Path to .cs file
            
        Returns:
            List of ClassInfo objects
        """
        try:
            source_code = file_path.read_bytes()
            tree = self.parser.parse(source_code)
            
            # Extract namespace and usings first
            namespace = self._extract_namespace(tree.root_node, source_code)
            usings = self._extract_usings(tree.root_node, source_code)
            
            # Extract all type declarations
            classes = []
            for class_node in self._find_type_declarations(tree.root_node):
                class_info = self._parse_type_declaration(
                    class_node,
                    source_code,
                    namespace,
                    str(file_path),
                )
                if class_info:
                    class_info.using_directives = usings
                    classes.append(class_info)
            
            return classes
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []
    
    def _extract_namespace(self, root:Node, source: bytes) -> str:
        """Extract namespace from file."""
        # Try file-scoped namespace first (C# 10+)
        for child in root.children:
            if child.type == "file_scoped_namespace_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    return self._get_text(name_node, source)
        
        # Try block-scoped namespace
        for child in root.children:
            if child.type == "namespace_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    return self._get_text(name_node, source)
        
        return ""
    
    def _extract_usings(self, root: Node, source: bytes) -> list[str]:
        """Extract using directives."""
        usings = []
        for child in root.children:
            if child.type == "using_directive":
                # Get the namespace being used
                for subchild in child.children:
                    if subchild.type in ["qualified_name", "identifier"]:
                        usings.append(self._get_text(subchild, source))
        return usings
    
    def _find_type_declarations(self, node: Node) -> list[Node]:
        """Recursively find all type declarations (class, record, struct, interface, enum)."""
        type_kinds = {
            "class_declaration",
            "record_declaration",
            "struct_declaration",
            "interface_declaration",
            "enum_declaration",
        }
        
        declarations = []
        
        if node.type in type_kinds:
            declarations.append(node)
        
        # Recurse into children
        for child in node.children:
            declarations.extend(self._find_type_declarations(child))
        
        return declarations
    
    def _parse_type_declaration(
        self,
        node: Node,
        source: bytes,
        namespace: str,
        file_path: str,
    ) -> Optional[ClassInfo]:
        """Parse a type declaration node into ClassInfo."""
        try:
            # Map node type to class kind
            kind_map = {
                "class_declaration": "class",
                "record_declaration": "record",
                "struct_declaration": "struct",
                "interface_declaration": "interface",
                "enum_declaration": "enum",
            }
            class_kind = kind_map.get(node.type, "class")
            
            # Extract name
            name_node = node.child_by_field_name("name")
            if not name_node:
                return None
            name = self._get_text(name_node, source)
            
            # Extract type parameters (generics)
            type_params = []
            type_param_list = node.child_by_field_name("type_parameters")
            if type_param_list:
                for param in type_param_list.children:
                    if param.type == "type_parameter":
                        type_params.append(self._get_text(param, source))
            
            # Extract base types (base class + interfaces)
            base_classes = []
            interfaces = []
            base_list = node.child_by_field_name("bases")
            if base_list:
                for base in base_list.children:
                    if base.type in ["base_type", "generic_name", "identifier", "qualified_name", "predefined_type"]:
                        base_name = self._get_text(base, source)
                        # Heuristic: if it starts with 'I' and is CamelCase, it's likely an interface
                        if base_name.startswith("I") and len(base_name) > 1 and base_name[1].isupper():
                            interfaces.append(base_name)
                        else:
                            base_classes.append(base_name)
            
            # Extract attributes
            attributes = self._extract_attributes(node, source)
            
            class_info = ClassInfo(
                name=name,
                namespace=namespace,
                file_path=file_path,
                class_kind=class_kind,
                base_classes=base_classes,
                interfaces=interfaces,
                generic_params=type_params,
                attributes=attributes,
            )
            
            # Extract members
            body = node.child_by_field_name("body")
            if body:
                for member in body.children:
                    if member.type == "property_declaration":
                        prop = self._parse_property(member, source)
                        if prop:
                            class_info.properties.append(prop)
                    elif member.type == "method_declaration":
                        method = self._parse_method(member, source)
                        if method:
                            class_info.methods.append(method)
                    elif member.type == "constructor_declaration":
                        ctor = self._parse_constructor(member, source)
                        if ctor:
                            class_info.constructors.append(ctor)
            
            # Check for primary constructor (C# 12)
            param_list = node.child_by_field_name("parameters")
            if param_list and class_kind in ["class", "record", "struct"]:
                params = self._parse_parameter_list(param_list, source)
                if params:
                    class_info.constructors.append(
                        ConstructorInfo(parameters=params, is_primary=True)
                    )
            
            return class_info
            
        except Exception as e:
            logger.warning(f"Failed to parse type declaration: {e}")
            return None
    
    def _parse_property(self, node: Node, source: bytes) -> Optional[PropertyInfo]:
        """Parse a property declaration."""
        try:
            name_node = node.child_by_field_name("name")
            type_node = node.child_by_field_name("type")
            
            if not name_node or not type_node:
                return None
            
            name = self._get_text(name_node, source)
            type_name = self._get_text(type_node, source)
            
            # Extract accessors
            accessors = "get; set;"  # Default
            accessor_list = None
            for child in node.children:
                if child.type == "accessor_list":
                    accessor_list = child
                    break
            
            if accessor_list:
                accessor_parts = []
                for accessor in accessor_list.children:
                    if accessor.type == "get_accessor_declaration":
                        # Check for private
                        mods = [c for c in accessor.children if c.type in ["private", "protected", "internal"]]
                        if mods:
                            accessor_parts.append(f"{self._get_text(mods[0], source)} get")
                        else:
                            accessor_parts.append("get")
                    elif accessor.type == "set_accessor_declaration":
                        mods = [c for c in accessor.children if c.type in ["private", "protected", "internal"]]
                        if mods:
                            accessor_parts.append(f"{self._get_text(mods[0], source)} set")
                        else:
                            accessor_parts.append("set")
                    elif accessor.type == "init_accessor_declaration":
                        accessor_parts.append("init")
                
                if accessor_parts:
                    accessors = "; ".join(accessor_parts) + ";"
            
            attributes = self._extract_attributes(node, source)
            
            return PropertyInfo(
                name=name,
                type_name=type_name,
                accessors=accessors,
                attributes=attributes,
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse property: {e}")
            return None
    
    def _parse_method(self, node: Node, source: bytes) -> Optional[MethodInfo]:
        """Parse a method declaration."""
        try:
            name_node = node.child_by_field_name("name")
            type_node = node.child_by_field_name("type")
            
            if not name_node:
                return None
            
            name = self._get_text(name_node, source)
            return_type = self._get_text(type_node, source) if type_node else "void"
            
            # Extract parameters
            parameters = []
            param_list = node.child_by_field_name("parameters")
            if param_list:
                parameters = self._parse_parameter_list(param_list, source)
            
            # Extract modifiers
            modifiers = []
            for child in node.children:
                if child.type in ["public", "private", "protected", "internal", "static", "virtual", "override", "abstract", "async"]:
                    modifiers.append(child.type)
            
            is_async = "async" in modifiers
            
            return MethodInfo(
                name=name,
                return_type=return_type,
                parameters=parameters,
                modifiers=modifiers,
                is_async=is_async,
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse method: {e}")
            return None
    
    def _parse_constructor(self, node: Node, source: bytes) -> Optional[ConstructorInfo]:
        """Parse a constructor declaration."""
        try:
            parameters = []
            param_list = node.child_by_field_name("parameters")
            if param_list:
                parameters = self._parse_parameter_list(param_list, source)
            
            return ConstructorInfo(parameters=parameters, is_primary=False)
            
        except Exception as e:
            logger.warning(f"Failed to parse constructor: {e}")
            return None
    
    def _parse_parameter_list(self, param_list_node: Node, source: bytes) -> list[ParameterInfo]:
        """Parse a parameter list."""
        parameters = []
        for child in param_list_node.children:
            if child.type == "parameter":
                name_node = child.child_by_field_name("name")
                type_node = child.child_by_field_name("type")
                
                if name_node and type_node:
                    parameters.append(
                        ParameterInfo(
                            name=self._get_text(name_node, source),
                            type_name=self._get_text(type_node, source),
                        )
                    )
        return parameters
    
    def _extract_attributes(self, node: Node, source: bytes) -> list[str]:
        """Extract attribute annotations from a node."""
        attributes = []
        for child in node.children:
            if child.type == "attribute_list":
                for attr in child.children:
                    if attr.type == "attribute":
                        # Get the attribute name
                        for subchild in attr.children:
                            if subchild.type in ["identifier", "qualified_name"]:
                                attributes.append(self._get_text(subchild, source))
        return attributes
    
    def _get_text(self, node: Node, source: bytes) -> str:
        """Extract text from a node."""
        return source[node.start_byte:node.end_byte].decode("utf-8")


# Convenience function
def parse_csharp_file(file_path: Path) -> list[ClassInfo]:
    """Parse a C# file and return all classes/types found.
    
    Args:
        file_path: Path to .cs file
        
    Returns:
        List of ClassInfo objects
    """
    if not TREE_SITTER_AVAILABLE:
        logger.warning(f"tree-sitter not available, skipping {file_path}")
        return []
    
    parser = CSharpParser()
    return parser.parse_file(file_path)
