"""Pattern detector for identifying .NET architectural patterns."""

import logging
from typing import Optional

from kb_generator.parsers.models import ClassInfo, DomainAggregate, UseCaseInfo

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detects common .NET architectural patterns in code."""
    
    def detect_aggregate_root(self, class_info: ClassInfo) -> bool:
        """Check if a class is a DDD Aggregate Root.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is an aggregate root
        """
        # Look for IAggregateRoot interface
        if "IAggregateRoot" in class_info.interfaces:
            return True
        
        # Look for marker attribute
        if any("AggregateRoot" in attr for attr in class_info.attributes):
            return True
        
        return False
    
    def detect_value_object(self, class_info: ClassInfo) -> bool:
        """Check if a class is a Value Object.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is a value object
        """
        # Vogen-generated value objects
        if any("ValueObject" in attr or "Vogen" in attr for attr in class_info.attributes):
            return True
        
        # Extends ValueObject base class
        if any("ValueObject" in base for base in class_info.base_classes):
            return True
        
        # Records are often value objects
        if class_info.class_kind == "record" and not class_info.methods:
            return True
        
        return False
    
    def detect_domain_event(self, class_info: ClassInfo) -> bool:
        """Check if a class is a Domain Event.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is a domain event
        """
        # Name ends with "Event"
        if class_info.name.endswith("Event"):
            return True
        
        # Implements event interface
        interfaces = [i.lower() for i in class_info.interfaces]
        if any("event" in i or "domainevent" in i for i in interfaces):
            return True
        
        # Extends event base class
        bases = [b.lower() for b in class_info.base_classes]
        if any("event" in b or "domainevent" in b for b in bases):
            return True
        
        return False
    
    def detect_event_handler(self, class_info: ClassInfo) -> bool:
        """Check if a class is a Domain Event Handler.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is an event handler
        """
        # Implements INotificationHandler or similar
        for interface in class_info.interfaces:
            if "NotificationHandler" in interface or "EventHandler" in interface or "DomainEventHandler" in interface:
                return True
        
        return False
    
    def detect_specification(self, class_info: ClassInfo) -> bool:
        """Check if a class is a Specification pattern.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is a specification
        """
        # Name ends with "Spec" or "Specification"
        if class_info.name.endswith("Spec") or class_info.name.endswith("Specification"):
            return True
        
        # Extends Specification base class
        if any("Specification" in base for base in class_info.base_classes):
            return True
        
        return False
    
    def detect_command(self, class_info: ClassInfo) -> bool:
        """Check if a class is a CQRS Command.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is a command
        """
        # Name ends with "Command"
        if class_info.name.endswith("Command"):
            return True
        
        # Implements ICommand or IRequest
        for interface in class_info.interfaces:
            if "ICommand" in interface or ("IRequest" in interface and "Command" in class_info.name):
                return True
        
        return False
    
    def detect_query(self, class_info: ClassInfo) -> bool:
        """Check if a class is a CQRS Query.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is a query
        """
        # Name ends with "Query"
        if class_info.name.endswith("Query"):
            return True
        
        # Implements IQuery or IRequest
        for interface in class_info.interfaces:
            if "IQuery" in interface or ("IRequest" in interface and "Query" in class_info.name):
                return True
        
        return False
    
    def detect_handler(self, class_info: ClassInfo) -> bool:
        """Check if a class is a Command/Query Handler.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is a handler
        """
        # Name ends with "Handler"
        if class_info.name.endswith("Handler"):
            return True
        
        # Implements handler interface
        for interface in class_info.interfaces:
            if "Handler" in interface and ("Command" in interface or "Query" in interface or "Request" in interface):
                return True
        
        return False
    
    def detect_repository(self, class_info: ClassInfo) -> bool:
        """Check if a class is a Repository.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is a repository
        """
        # Implements IRepository
        if any("IRepository" in interface for interface in class_info.interfaces):
            return True
        
        # Extends repository base
        if any("Repository" in base for base in class_info.base_classes):
            return True
        
        # Name contains "Repository"
        if "Repository" in class_info.name:
            return True
        
        return False
    
    def detect_endpoint(self, class_info: ClassInfo) -> bool:
        """Check if a class is a FastEndpoint or API Controller.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is an API endpoint
        """
        # FastEndpoints
        if any("Endpoint" in base for base in class_info.base_classes):
            return True
        
        # Controllers
        if "[ApiController]" in class_info.attributes or "ApiController" in class_info.attributes:
            return True
        
        if any("Controller" in base for base in class_info.base_classes):
            return True
        
        return False
    
    def detect_ef_configuration(self, class_info: ClassInfo) -> bool:
        """Check if a class is an Entity Framework configuration.
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is an EF configuration
        """
        return any("IEntityTypeConfiguration" in interface for interface in class_info.interfaces)
    
    def detect_dto(self, class_info: ClassInfo) -> bool:
        """Check if a class is a DTO (Data Transfer Object).
        
        Args:
            class_info: Class to check
            
        Returns:
            True if this is likely a DTO
        """
        # Records with only properties
        if class_info.class_kind == "record" and not class_info.methods and class_info.properties:
            return True
        
        # Name ends with DTO or Request or Response
        if any(class_info.name.endswith(suffix) for suffix in ["DTO", "Dto", "Request", "Response", "Model"]):
            return True
        
        return False
    
    def find_aggregate(self, classes: list[ClassInfo], root: ClassInfo) -> DomainAggregate:
        """Build a domain aggregate from a root entity.
        
        Args:
            classes: All classes in the codebase
            root: Aggregate root entity
            
        Returns:
            DomainAggregate with all related objects
        """
        aggregate = DomainAggregate(root_entity=root)
        
        # Find related classes in the same namespace or nested namespace
        root_namespace = root.namespace
        
        for cls in classes:
            if not cls.namespace.startswith(root_namespace):
                continue
            
            if cls.full_name == root.full_name:
                continue
            
            # Categorize related classes
            if self.detect_value_object(cls):
                aggregate.value_objects.append(cls)
            elif self.detect_domain_event(cls):
                aggregate.domain_events.append(cls)
            elif self.detect_specification(cls):
                aggregate.specifications.append(cls)
            elif self.detect_event_handler(cls):
                aggregate.event_handlers.append(cls)
        
        return aggregate
    
    def find_use_case(self, classes: list[ClassInfo], command_or_query: ClassInfo) -> Optional[UseCaseInfo]:
        """Find the use case (command/query + handler) for a command or query.
        
        Args:
            classes: All classes in the codebase
            command_or_query: Command or query class
            
        Returns:
            UseCaseInfo or None if handler not found
        """
        # Look for matching handler
        expected_handler_name = command_or_query.name + "Handler"
        pattern = "Command" if self.detect_command(command_or_query) else "Query"
        
        for cls in classes:
            if cls.name == expected_handler_name and self.detect_handler(cls):
                # Extract constructor dependencies
                dependencies = []
                for ctor in cls.constructors:
                    for param in ctor.parameters:
                        dependencies.append(param.type_name)
                
                return UseCaseInfo(
                    command_or_query=command_or_query,
                    handler=cls,
                    pattern=pattern,
                    dependencies=dependencies,
                )
        
        return None
