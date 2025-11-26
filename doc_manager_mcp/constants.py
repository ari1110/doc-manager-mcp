"""Constants and enums for doc-manager MCP server."""

import re
from enum import Enum

# Code reference patterns (shared between dependencies.py and validation_helpers.py)
FUNCTION_PATTERN = re.compile(r'^(([A-Z][a-zA-Z0-9]*\.)?([a-z_][a-zA-Z0-9_]*)\(\))$')
CLASS_PATTERN = re.compile(r'^([A-Z][a-zA-Z0-9]+)$')

# Common words to exclude from class matching (acronyms, not actual classes)
CLASS_EXCLUDES = {
    'API', 'CLI', 'HTTP', 'HTTPS', 'URL', 'JSON', 'XML', 'HTML', 'CSS',
    'SQL', 'REST', 'YAML', 'TOML', 'UUID', 'UTF', 'ASCII', 'ISO'
}

# Response size limit
CHARACTER_LIMIT = 25000  # Maximum response size in characters

# Resource limits (FR-019, FR-020, FR-021)
MAX_FILES = 10_000  # Maximum files to process per operation
MAX_RECURSION_DEPTH = 100  # Maximum symlink resolution depth
OPERATION_TIMEOUT = 60  # Operation timeout in seconds

# Supported documentation platforms
SUPPORTED_PLATFORMS = ["hugo", "docusaurus", "mkdocs", "sphinx", "vitepress", "jekyll", "gitbook"]

# Platform detection markers (configurable)
PLATFORM_MARKERS = {
    "hugo": {
        "root_configs": ["hugo.toml", "hugo.yaml", "config.toml"],
        "subdir_configs": ["hugo.yaml", "hugo.toml", "config.toml"],
        "dependencies": {"go.mod": ["hugo"]},
    },
    "docusaurus": {
        "root_configs": ["docusaurus.config.js", "docusaurus.config.ts"],
        "subdir_configs": ["docusaurus.config.js", "docusaurus.config.ts"],
        "dependencies": {"package.json": ["docusaurus", "@docusaurus/core"]},
    },
    "mkdocs": {
        "root_configs": ["mkdocs.yml"],
        "subdir_configs": ["mkdocs.yml"],
        "dependencies": {"requirements.txt": ["mkdocs"]},
    },
    "sphinx": {
        "root_configs": ["docs/conf.py", "doc/conf.py"],
        "subdir_configs": ["conf.py"],
        "dependencies": {"requirements.txt": ["sphinx"], "setup.py": ["sphinx", "setuptools"]},
    },
    "vitepress": {
        "root_configs": [".vitepress/config.js", ".vitepress/config.ts"],
        "subdir_configs": [".vitepress/config.js", ".vitepress/config.ts"],
        "dependencies": {"package.json": ["vitepress"]},
    },
    "jekyll": {
        "root_configs": ["_config.yml"],
        "subdir_configs": ["_config.yml"],
        "dependencies": {},
    },
}

# Common documentation directories to search
DOC_DIRECTORIES = ["docsite", "docs", "documentation", "website", "site"]

# Language-based platform recommendations
LANGUAGE_PLATFORM_RECOMMENDATIONS = {
    "Go": ("hugo", "Hugo is written in Go and popular in Go ecosystem"),
    "JavaScript/TypeScript": ("docusaurus", "Docusaurus is React-based and popular in JavaScript ecosystem"),
    "Node.js": ("docusaurus", "Docusaurus is React-based and popular in JavaScript ecosystem"),
    "Python": ("mkdocs", "MkDocs is Python-based and popular in Python ecosystem"),
}

# Default platform recommendation
DEFAULT_PLATFORM_RECOMMENDATION = ("hugo", "Hugo is fast, language-agnostic, and widely adopted")

# Quality assessment criteria
QUALITY_CRITERIA = [
    "relevance", "accuracy", "purposefulness", "uniqueness",
    "consistency", "clarity", "structure"
]

# Default exclude patterns for memory baseline (always applied)
# Comprehensive list covering all major languages and build systems
DEFAULT_EXCLUDE_PATTERNS = [
    # Version Control
    "**/.git", "**/.git/**",
    "**/.svn", "**/.svn/**",
    "**/.hg", "**/.hg/**",
    "**/.bzr", "**/.bzr/**",

    # Python
    "**/__pycache__", "**/__pycache__/**",
    "**/*.pyc", "**/*.pyo", "**/*.pyd",
    "**/.pytest_cache", "**/.pytest_cache/**",
    "**/.mypy_cache", "**/.mypy_cache/**",
    "**/.ruff_cache", "**/.ruff_cache/**",
    "**/.tox", "**/.tox/**",
    "**/.nox", "**/.nox/**",
    "**/venv", "**/venv/**",
    "**/.venv", "**/.venv/**",
    "**/env", "**/env/**",
    "**/.virtualenv", "**/.virtualenv/**",
    "**/*.egg-info", "**/*.egg-info/**",
    "**/.eggs", "**/.eggs/**",
    "**/dist", "**/dist/**",
    "**/build", "**/build/**",
    "**/.coverage", "**/htmlcov", "**/htmlcov/**",
    "**/.hypothesis", "**/.hypothesis/**",

    # Node.js/JavaScript
    "**/node_modules", "**/node_modules/**",
    "**/.npm", "**/.npm/**",
    "**/.yarn", "**/.yarn/**",
    "**/.pnp", "**/.pnp/**",
    "**/.pnp.js",
    "**/coverage", "**/coverage/**",
    "**/.next", "**/.next/**",
    "**/.nuxt", "**/.nuxt/**",
    "**/.output", "**/.output/**",
    "**/.turbo", "**/.turbo/**",
    "**/out", "**/out/**",

    # Go
    "**/vendor", "**/vendor/**",
    "**/bin", "**/bin/**",  # Note: May be too broad (excludes utility scripts in some projects)
    "**/pkg", "**/pkg/**",

    # Rust
    "**/target", "**/target/**",
    # Note: Cargo.lock is intentionally NOT excluded (lock file for reproducible builds)

    # Java/JVM
    "**/.gradle", "**/.gradle/**",
    "**/.mvn", "**/.mvn/**",
    "**/.idea", "**/.idea/**",
    "**/out", "**/out/**",

    # C/C++
    "**/cmake-build-*", "**/cmake-build-*/**",
    "**/.vs", "**/.vs/**",
    "**/Debug", "**/Debug/**",
    "**/Release", "**/Release/**",
    "**/x64", "**/x64/**",
    "**/x86", "**/x86/**",
    "**/*.o", "**/*.so", "**/*.dylib", "**/*.dll",

    # Ruby
    "**/.bundle", "**/.bundle/**",
    "**/vendor/bundle", "**/vendor/bundle/**",

    # .NET
    "**/obj", "**/obj/**",
    "**/packages", "**/packages/**",

    # IDEs/Editors
    "**/.vscode", "**/.vscode/**",
    "**/*.swp", "**/*.swo", "**/*~",
    "**/.vs", "**/.vs/**",
    "**/.idea", "**/.idea/**",

    # OS
    "**/.DS_Store",
    "**/Thumbs.db",
    "**/desktop.ini",
    "**/.Spotlight-V100",
    "**/.Trashes",

    # PHP (Composer)
    # Note: vendor also covered in general section above
    "**/composer.lock",

    # Elixir (Mix)
    "**/deps", "**/deps/**",
    "**/.elixir_ls", "**/.elixir_ls/**",

    # Dart & Flutter
    "**/.dart_tool", "**/.dart_tool/**",
    "**/.flutter-plugins",
    "**/.flutter-plugins-dependencies",
    "**/pubspec.lock",

    # Swift (Xcode & Swift Package Manager)
    "**/.build", "**/.build/**",
    "**/DerivedData", "**/DerivedData/**",
    "**/*.xcodeproj", "**/*.xcodeproj/**",
    "**/.swiftpm", "**/.swiftpm/**",

    # Haskell (Stack/Cabal)
    "**/.stack-work", "**/.stack-work/**",
    "**/dist-newstyle", "**/dist-newstyle/**",

    # Terraform
    "**/.terraform", "**/.terraform/**",
    "**/.terraform.lock.hcl",
    "**/*.tfstate",
    "**/*.tfstate.backup",

    # Cloud & Serverless Frameworks
    "**/.serverless", "**/.serverless/**",
    "**/.aws-sam", "**/.aws-sam/**",

    # Docker
    "**/docker-compose.override.yml",

    # More IDEs/Editors
    "**/.project",              # Eclipse
    "**/.classpath",            # Eclipse
    "**/.settings", "**/.settings/**",  # Eclipse
    "**/nbproject", "**/nbproject/**",  # NetBeans
    "**/*.sublime-workspace",   # Sublime Text
    "**/*.sublime-project",     # Sublime Text
    "**/*.iml",                 # JetBrains module files

    # Secrets and Credentials (sensitive files)
    "**/*.env",
    "**/.env.*",
    "**/*.pem",
    "**/*.key",
    "**/secrets.json",
    "**/secrets.yml",
    "**/credentials.json",
    "**/credentials.yml",

    # Logs and Temp
    "**/*.log",
    "**/*.tmp",
    "**/*.bak",
    "**/*.old",
    "**/*.orig",
    "**/*.patch",
    "**/*.diff",
    "**/*.local",
    "**/tmp", "**/tmp/**",
    "**/temp", "**/temp/**",
    "**/logs", "**/logs/**",

    # Documentation Build Outputs
    "**/_build", "**/_build/**",
    "**/.docusaurus", "**/.docusaurus/**",
    "**/public", "**/public/**",  # Note: May be too broad (excludes source assets in Rails/Laravel)
    "**/.vitepress/dist", "**/.vitepress/dist/**",
    "**/site", "**/site/**",

    # Our own state
    "**/.doc-manager", "**/.doc-manager/**",
]

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
