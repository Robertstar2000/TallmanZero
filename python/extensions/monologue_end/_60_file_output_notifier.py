"""
TallmanZero - File Output Detection Extension (monologue_end)

Runs after every agent response cycle. Detects files created/written during
the monologue and emits a 'file_output' log event so the download modal shows.

Detection strategy (multi-layer):
  1. Scan code_exe log items for bash output-redirect patterns (> file, tee file, etc.)
  2. Scan all log items for absolute paths mentioned
  3. Filesystem scan: find files modified in the last N minutes in key dirs

All three sources are merged and deduplicated before emitting the event.
"""
import os
import re
import time
from pathlib import Path
from python.helpers.extension import Extension

# ── Extensions to consider "user output" files ──────────────────────────────
OUTPUT_EXTENSIONS = {
    # Documents
    'pdf', 'docx', 'doc', 'odt', 'rtf', 'txt', 'md', 'rst', 'tex',
    # Spreadsheets & Data
    'csv', 'xlsx', 'xls', 'ods', 'json', 'yaml', 'yml', 'xml', 'toml',
    # Code
    'py', 'js', 'ts', 'jsx', 'tsx', 'sh', 'bash', 'zsh', 'html', 'css',
    'java', 'c', 'cpp', 'h', 'hpp', 'go', 'rs', 'rb', 'php', 'cs', 'swift',
    'r', 'ipynb', 'sql',
    # Archives
    'zip', 'tar', 'gz', 'bz2', 'rar', '7z',
    # Config / misc
    'log', 'cfg', 'ini', 'conf', 'env', 'dockerfile',
}

# ── Directories to watch for recently-modified files ─────────────────────────
FS_SCAN_DIRS = ['/', '/a0', '/tmp', '/root', '/home', '/work', '/output']

# ── Skip these subtrees (agent internals, system paths) ──────────────────────
FS_SKIP_DIRS = {
    '__pycache__', 'node_modules', '.git', 'venv', '.venv',
    'site-packages', 'lib', 'bin', 'sbin', 'proc', 'sys', 'dev',
}
FS_SKIP_PATHS = [
    '/a0/python', '/a0/webui', '/a0/docker', '/a0/vendor',
    '/proc', '/sys', '/dev', '/run',
]

# ── How recently a file must have been modified (seconds) ────────────────────
FS_RECENCY_WINDOW = 90   # 1.5 minutes

# ── Bash output-redirect patterns to detect from terminal content ─────────────
BASH_REDIRECT_RE = [
    # absolute: > /path/to/file.ext or >> /path/to/file.ext
    re.compile(r'>{1,2}\s+(/[^\s\'"`;|&>]+\.[A-Za-z0-9]{1,10})', re.MULTILINE),
    # relative: > filename.ext  or >> filename.ext (starts with word char, not /)
    re.compile(r'>{1,2}\s+([A-Za-z0-9_./-][^\s\'"`;|&>]*\.[A-Za-z0-9]{1,10})', re.MULTILINE),
    # tee [–a] file
    re.compile(r'\btee\s+(?:-a\s+)?([^\s\'"`;|&>]+\.[A-Za-z0-9]{1,10})', re.MULTILINE),
    # cat > file (heredoc-style)
    re.compile(r'\bcat\s+>{1,2}\s+([^\s\'"`;|&>]+\.[A-Za-z0-9]{1,10})', re.MULTILINE),
    # cp source dest
    re.compile(r'\bcp\s+\S+\s+([^\s\'"`;|&>]+\.[A-Za-z0-9]{1,10})', re.MULTILINE),
    # mv source dest
    re.compile(r'\bmv\s+\S+\s+([^\s\'"`;|&>]+\.[A-Za-z0-9]{1,10})', re.MULTILINE),
    # curl -o / wget -O
    re.compile(r'(?:curl\s.*-o|wget\s.*-O)\s+([^\s\'"`;|&>]+\.[A-Za-z0-9]{1,10})', re.MULTILINE),
    # python / pip writes "Saved to" or "Written to"
    re.compile(r'(?:saved?|written?)\s+to\s+[\'"]?([^\s\'"`;|&>]+\.[A-Za-z0-9]{1,10})[\'"]?', re.IGNORECASE | re.MULTILINE),
]

# ── Absolute-path patterns for scanning all log text ─────────────────────────
ABS_PATH_RE = re.compile(
    r'(/(?:a0|tmp|root|home|work|output|files|data|var|run|srv)'
    r'/[^\s\'"`;,\)\]>]{2,}/[^\s\'"`;,\)\]>]{1,}\.[A-Za-z0-9]{1,10})',
    re.MULTILINE
)

# Bases to resolve relative paths against (in priority order)
RELATIVE_BASES = ['/', '/a0', '/tmp', '/root', '/home']


class FileOutputNotifier(Extension):

    async def execute(self, **kwargs):
        try:
            found: dict[str, dict] = {}   # path -> file_info

            # ── Collect all log item text from this monologue ─────────────
            log = self.agent.context.log
            items = log.logs if hasattr(log, 'logs') else []
            all_text = ""
            bash_text = ""

            for item in items:
                c = (item.content or "")
                h = (item.heading or "")
                all_text += " " + h + " " + c
                # Bash terminal content for redirect detection
                if getattr(item, 'type', '') == 'code_exe':
                    bash_text += " " + c + " " + h

            # ── Strategy 1: Bash redirect patterns ───────────────────────
            if bash_text:
                for pattern in BASH_REDIRECT_RE:
                    for m in pattern.finditer(bash_text):
                        raw = m.group(1).strip().rstrip('.,;)')
                        self._try_resolve(raw, found)

            # ── Strategy 2: Absolute paths in all log text ───────────────
            for m in ABS_PATH_RE.finditer(all_text):
                raw = m.group(1).strip().rstrip('.,;)')
                self._try_resolve(raw, found)

            # ── Strategy 3: Filesystem scan for recently modified files ───
            since = time.time() - FS_RECENCY_WINDOW
            self._fs_scan(since, found)

            if not found:
                return

            downloadable = list(found.values())

            # Emit the file_output log event (picked up by the JS poller)
            # Store files in kvps so they survive serialization as structured data
            self.agent.context.log.log(
                type="file_output",
                heading="📥 Files Ready for Download",
                content=f"{len(downloadable)} file(s) ready to download",
                temp=False,
                files=downloadable,  # stored in kvps as 'files' key
            )


        except Exception as e:
            from python.helpers.print_style import PrintStyle
            PrintStyle.error(f"FileOutputNotifier error: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _try_resolve(self, raw: str, found: dict):
        """Resolve a raw path string (absolute or relative) to an existing file."""
        ext = raw.rsplit('.', 1)[-1].lower() if '.' in raw else ''
        if ext not in OUTPUT_EXTENSIONS:
            return
        # Absolute path — check directly
        if raw.startswith('/'):
            self._register_if_file(raw, found)
        else:
            # Relative — try multiple bases
            for base in RELATIVE_BASES:
                candidate = os.path.join(base, raw)
                if self._register_if_file(candidate, found):
                    break

    def _register_if_file(self, path: str, found: dict) -> bool:
        """If path is an existing file with a useful extension, add to found. Returns True if added."""
        try:
            path = str(Path(path).resolve())
        except Exception:
            return False
        if path in found:
            return True
        if not os.path.isfile(path):
            return False
        ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
        if ext not in OUTPUT_EXTENSIONS:
            return False
        # Skip agent source/system files
        if any(path.startswith(skip) for skip in FS_SKIP_PATHS):
            return False
        try:
            size = os.path.getsize(path)
        except OSError:
            return False
        found[path] = {
            "path": path,
            "name": os.path.basename(path),
            "size": size,
            "ext": ext,
        }
        return True

    def _fs_scan(self, since_ts: float, found: dict):
        """Walk key directories to find files modified after since_ts."""
        visited = set()
        for base in FS_SCAN_DIRS:
            if not os.path.isdir(base):
                continue
            try:
                for root, dirs, files in os.walk(base, topdown=True, followlinks=False):
                    # Prune skip directories
                    dirs[:] = [
                        d for d in dirs
                        if d not in FS_SKIP_DIRS
                        and not os.path.join(root, d) in visited
                        and not any(os.path.join(root, d).startswith(s) for s in FS_SKIP_PATHS)
                    ]
                    # Don't re-scan subdirectories already covered by another base
                    if root in visited:
                        dirs[:] = []
                        continue
                    visited.add(root)

                    for fname in files:
                        full = os.path.join(root, fname)
                        if full in found:
                            continue
                        try:
                            st = os.stat(full)
                            if st.st_mtime < since_ts:
                                continue
                            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                            if ext not in OUTPUT_EXTENSIONS:
                                continue
                            if any(full.startswith(s) for s in FS_SKIP_PATHS):
                                continue
                            found[full] = {
                                "path": full,
                                "name": fname,
                                "size": st.st_size,
                                "ext": ext,
                            }
                        except OSError:
                            pass
            except PermissionError:
                pass
