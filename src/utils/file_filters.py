import re
from pathlib import Path

def _should_skip_directory(dir_name: str) -> bool:
    """Skip common directories that don't contain services."""

    # Skip all hidden directories (starting with .)
    if dir_name.startswith('.'):
        return True

    # Build and dependency directories
    build_dirs = {
        'target', 'build', 'dist', 'out', 'bin', 'obj', 'generated',
        'output', 'release', 'debug', 'artifacts'
    }

    # Package manager dependency directories
    dependency_dirs = {
        'node_modules', 'vendor', 'deps', '_build', 'packages',
        'bower_components', 'jspm_packages', 'typings'
    }

    # Python-specific directories
    python_dirs = {
        '__pycache__', '.pytest_cache', '.mypy_cache', '.tox',
        'venv', '.venv', 'env', '.env', 'virtualenv', '.virtualenv',
        'site-packages', 'pip-cache', '.coverage'
    }

    # IDE and editor directories
    ide_dirs = {
        '.idea', '.vscode', '.vs', '.eclipse', '.settings',
        '.project', '.classpath', '.gradle'
    }

    # Testing and documentation directories
    test_dirs = {
        'test', 'tests', 'spec', 'specs', '__tests__', 'e2e',
        'integration', 'unit', 'coverage'
    }

    # Documentation and example directories
    doc_dirs = {
        'docs', 'documentation', 'doc', 'examples', 'example',
        'demo', 'demos', 'samples', 'sample'
    }

    # Temporary and cache directories
    temp_dirs = {
        'tmp', 'temp', 'cache', '.cache', 'logs', 'log'
    }

    # OS-specific directories
    os_dirs = {
        'System Volume Information', '$RECYCLE.BIN', '.Trash',
        '.DS_Store', 'Thumbs.db', 'desktop.ini'
    }

    # Combine all skip sets
    all_skip_dirs = (
        build_dirs | dependency_dirs | python_dirs | ide_dirs |
        test_dirs | doc_dirs | temp_dirs | os_dirs
    )

    return dir_name in all_skip_dirs


def _is_binary_file(filename: str) -> bool:
    """Check if file is likely a binary file based on extension."""
    file_path = Path(filename)
    extension = file_path.suffix.lower()

    # Archive and compressed files
    archive_extensions = {
        '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar', '.xz',
        '.tgz', '.tbz', '.tbz2', '.tar.gz', '.tar.bz2'
    }

    # Executable and library files
    executable_extensions = {
        '.exe', '.dll', '.so', '.dylib', '.a', '.lib', '.o', '.obj',
        '.jar', '.war', '.ear', '.class', '.pyc', '.pyo', '.pyd'
    }

    # Media files
    media_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm',
        '.wav', '.ogg', '.m4a', '.aac'
    }

    # Document files
    document_extensions = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.odt', '.ods', '.odp', '.rtf'
    }

    # Font files
    font_extensions = {
        '.ttf', '.otf', '.woff', '.woff2', '.eot'
    }

    # Database and data files
    data_extensions = {
        '.db', '.sqlite', '.sqlite3', '.mdb', '.accdb', '.dbf'
    }

    # Image and design files
    design_extensions = {
        '.psd', '.ai', '.sketch', '.fig', '.xd'
    }

    # Combine all binary extensions
    all_binary_extensions = (
        archive_extensions | executable_extensions | media_extensions |
        document_extensions | font_extensions | data_extensions |
        design_extensions
    )

    # Check against known binary extensions
    if extension in all_binary_extensions:
        return True

    # Additional heuristics for files without extensions
    if not extension:
        binary_patterns = ['binary', 'executable', '.bin', '.dat']
        if any(pattern in filename.lower() for pattern in binary_patterns):
            return True

    return False


def _is_generated_or_derived_directory(dir_path: Path) -> bool:
    """
    Check if directory appears to be generated or derived from source code.
    This is a heuristic-based approach.
    """
    dir_name = dir_path.name.lower()

    # Common patterns for generated directories - use more specific matching
    generated_exact_patterns = [
        'generated', 'autogen', 'codegen', 'gen',
        'compile', 'compiled', 'transpiled', 'processed'
    ]

    # Patterns that should match as whole words or at word boundaries
    generated_word_patterns = [
        'auto'  # Should match 'auto' but not 'automations'
    ]

    # Check for exact matches or patterns at the start/end of directory name
    for pattern in generated_exact_patterns:
        if pattern in dir_name:
            return True

    # Check for word boundary patterns - 'auto' should match 'auto', 'auto-generated',
    # but not 'automations'
    for pattern in generated_word_patterns:
        # Match if pattern is the whole name, starts with pattern-, or ends with -pattern
        if (dir_name == pattern or
            dir_name.startswith(f"{pattern}-") or
            dir_name.endswith(f"-{pattern}") or
            f"-{pattern}-" in dir_name):
            return True

    # Check for version-specific directories (like node_modules/@types/...)
    if dir_name.startswith('@') or dir_name.startswith('_'):
        return True

    # Check for directories with build timestamps or hashes
    if re.match(r'^[a-f0-9]{8,}$', dir_name):  # Looks like a hash
        return True

    if re.match(r'^\d{4}-\d{2}-\d{2}', dir_name):  # Starts with date
        return True

    return False
