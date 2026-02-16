"""Data models for parsed .NET code elements."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParameterInfo:
    """Represents a method/constructor parameter."""
    name: str
    type_name: str
    default_value: Optional[str] = None


@dataclass
class PropertyInfo:
    """Represents a class property."""
    name: str
    type_name: str
    accessors: str  # "get; set;", "get; private set;", etc.
    attributes: list[str] = field(default_factory=list)
    xml_doc: Optional[str] = None


@dataclass
class MethodInfo:
    """Represents a class method."""
    name: str
    return_type: str
    parameters: list[ParameterInfo] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)  # async, virtual, override, static
    xml_doc: Optional[str] = None
    is_async: bool = False


@dataclass
class ConstructorInfo:
    """Represents a class constructor."""
    parameters: list[ParameterInfo] = field(default_factory=list)
    is_primary: bool = False  # C# 12 primary constructor
    xml_doc: Optional[str] = None


@dataclass
class ClassInfo:
    """Represents a class, record, struct, interface, or enum."""
    name: str
    namespace: str
    file_path: str
    class_kind: str = "class"  # "class", "record", "struct", "enum", "interface"
    base_classes: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    properties: list[PropertyInfo] = field(default_factory=list)
    methods: list[MethodInfo] = field(default_factory=list)
    constructors: list[ConstructorInfo] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)  # e.g., [ApiController], [Authorize]
    generic_params: list[str] = field(default_factory=list)
    xml_doc: Optional[str] = None
    using_directives: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Get fully qualified name."""
        return f"{self.namespace}.{self.name}" if self.namespace else self.name

    @property
    def is_abstract(self) -> bool:
        """Check if class is abstract."""
        return "abstract" in [attr.lower() for attr in self.attributes]


@dataclass
class PackageRef:
    """Represents a NuGet package reference."""
    name: str
    version: Optional[str] = None


@dataclass
class ProjectInfo:
    """Represents a .NET project (.csproj)."""
    name: str
    path: str
    sdk: str = "Microsoft.NET.Sdk"  # e.g., "Microsoft.NET.Sdk.Web"
    target_framework: str = ""
    project_references: list[str] = field(default_factory=list)
    package_references: list[PackageRef] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)

    @property
    def is_test_project(self) -> bool:
        """Check if this is a test project."""
        test_packages = {"xunit", "nunit", "mstest", "xunit.core"}
        return any(
            pkg.name.lower() in test_packages or "test" in pkg.name.lower()
            for pkg in self.package_references
        )

    @property
    def is_web_project(self) -> bool:
        """Check if this is a web project."""
        return "Web" in self.sdk or any(
            pkg.name in ["Microsoft.AspNetCore.App", "FastEndpoints"]
            for pkg in self.package_references
        )


@dataclass
class SolutionInfo:
    """Represents a .NET solution (.sln/.slnx)."""
    name: str
    path: str
    projects: list[ProjectInfo] = field(default_factory=list)


# Analyzed domain models (combining parsed data with detected patterns)

@dataclass
class DomainAggregate:
    """Represents a detected DDD Aggregate."""
    root_entity: ClassInfo
    value_objects: list[ClassInfo] = field(default_factory=list)
    domain_events: list[ClassInfo] = field(default_factory=list)
    specifications: list[ClassInfo] = field(default_factory=list)
    event_handlers: list[ClassInfo] = field(default_factory=list)


@dataclass
class UseCaseInfo:
    """Represents a CQRS use case (command/query + handler)."""
    command_or_query: ClassInfo
    handler: ClassInfo
    pattern: str  # "Command" or "Query"
    dependencies: list[str] = field(default_factory=list)  # Constructor-injected types


@dataclass
class EndpointInfo:
    """Represents an API endpoint."""
    route: str
    http_method: str
    handler_class: str
    request_type: Optional[str] = None
    response_type: Optional[str] = None
    file_path: str = ""


# ──────────────────────────────────────────────────────────────────
# Phase 8-9: Deep Analysis & Impact Models
# ──────────────────────────────────────────────────────────────────

@dataclass
class GraphNode:
    """A node in the class dependency graph."""
    class_info: ClassInfo
    role: str = "other"       # endpoint, command, query, handler, repository, entity, service, config, dto, other
    project: str = ""         # Which project this class belongs to
    layer: str = ""           # Web, Application, Core, Infrastructure, Test

    @property
    def full_name(self) -> str:
        return self.class_info.full_name


@dataclass
class GraphEdge:
    """A directed edge in the dependency graph."""
    source: str              # Source class full_name
    target: str              # Target class full_name
    edge_type: str           # injects, inherits, implements, uses, sends, handles
    label: str = ""          # Human-readable label


@dataclass
class FlowStep:
    """A single step in a request flow."""
    class_name: str          # Full class name
    role: str                # endpoint, command, handler, repository, entity, service
    action: str              # Human-readable: "receives HTTP POST", "handles command", etc.
    file_path: str = ""
    project: str = ""
    layer: str = ""


@dataclass
class RequestFlow:
    """A complete request flow from entry point to data layer."""
    name: str                     # Auto-generated: "Create Contributor"
    entry_point: str              # "POST /api/Contributors"
    http_method: str              # POST, GET, PUT, DELETE
    steps: list[FlowStep] = field(default_factory=list)
    command_or_query: str = ""    # The CQRS message type name
    aggregate: Optional[str] = None  # Target aggregate root
    side_effects: list[str] = field(default_factory=list)
    cross_cutting: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        """URL-safe slug for file naming."""
        return self.name.lower().replace(" ", "-")


@dataclass
class ImpactedItem:
    """A single item affected by a change."""
    name: str
    item_type: str           # class, flow, kb_doc, test, endpoint
    impact_level: str        # direct, indirect, transitive
    reason: str              # Why this is impacted
    file_path: str = ""


@dataclass
class ImpactReport:
    """Complete impact analysis for a set of changed files."""
    changed_files: list[str] = field(default_factory=list)
    timestamp: str = ""
    affected_classes: list[ImpactedItem] = field(default_factory=list)
    affected_flows: list[ImpactedItem] = field(default_factory=list)
    affected_kb_docs: list[ImpactedItem] = field(default_factory=list)
    affected_tests: list[ImpactedItem] = field(default_factory=list)
    affected_endpoints: list[ImpactedItem] = field(default_factory=list)

    @property
    def total_impact_count(self) -> int:
        return (len(self.affected_classes) + len(self.affected_flows) +
                len(self.affected_kb_docs) + len(self.affected_tests) +
                len(self.affected_endpoints))

    @property
    def risk_level(self) -> str:
        """Compute risk level based on impact counts."""
        flow_count = len(self.affected_flows)
        if flow_count >= 5:
            return "critical"
        elif flow_count >= 3:
            return "high"
        elif flow_count >= 1:
            return "medium"
        return "low"
