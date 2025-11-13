"""Constants and enums for doc-manager MCP server."""

from enum import Enum

# Response size limit
CHARACTER_LIMIT = 25000  # Maximum response size in characters

# Supported documentation platforms
SUPPORTED_PLATFORMS = ["hugo", "docusaurus", "mkdocs", "sphinx", "vitepress", "jekyll", "gitbook"]

# Quality assessment criteria
QUALITY_CRITERIA = ["relevance", "accuracy", "purposefulness", "uniqueness", "consistency", "clarity", "structure"]

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"

class DocumentationPlatform(str, Enum):
    """Supported documentation platforms."""
    HUGO = "hugo"
    DOCUSAURUS = "docusaurus"
    MKDOCS = "mkdocs"
    SPHINX = "sphinx"
    VITEPRESS = "vitepress"
    JEKYLL = "jekyll"
    GITBOOK = "gitbook"
    UNKNOWN = "unknown"

class QualityCriterion(str, Enum):
    """Quality assessment criteria."""
    RELEVANCE = "relevance"
    ACCURACY = "accuracy"
    PURPOSEFULNESS = "purposefulness"
    UNIQUENESS = "uniqueness"
    CONSISTENCY = "consistency"
    CLARITY = "clarity"
    STRUCTURE = "structure"

class ChangeDetectionMode(str, Enum):
    """Change detection modes."""
    CHECKSUM = "checksum"
    GIT_DIFF = "git_diff"

# Alias for backward compatibility
Platform = DocumentationPlatform
