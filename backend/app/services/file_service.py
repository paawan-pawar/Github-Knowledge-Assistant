from __future__ import annotations

from app.models.schemas import TreeNode
from app.services.repo_store import IndexedFile

MAX_TREE_ENTRIES = 3000


def build_tree(files: list[IndexedFile], root_name: str) -> TreeNode:
    root = TreeNode(name=root_name, path="", type="dir", children=[])
    dir_index: dict[str, TreeNode] = {"": root}

    for f in files[:MAX_TREE_ENTRIES]:
        parts = f.path.split("/")
        parent_path = ""
        for depth, part in enumerate(parts):
            is_file = depth == len(parts) - 1
            current_path = f"{parent_path}/{part}" if parent_path else part
            if is_file:
                parent = dir_index[parent_path]
                parent.children.append(
                    TreeNode(name=part, path=f.path, type="file", language=f.language, size=f.size)
                )
            else:
                if current_path not in dir_index:
                    node = TreeNode(name=part, path=current_path, type="dir", children=[])
                    dir_index[current_path] = node
                    dir_index[parent_path].children.append(node)
                parent_path = current_path

    _sort_tree(root)
    return root


def _sort_tree(node: TreeNode) -> None:
    if not node.children:
        return
    node.children.sort(key=lambda n: (n.type != "dir", n.name.lower()))
    for child in node.children:
        if child.type == "dir":
            _sort_tree(child)


def fuzzy_search(files: list[IndexedFile], query: str, limit: int = 30) -> list[tuple[str, float]]:
    q = query.strip().lower()
    if not q:
        return []
    scored: list[tuple[str, float]] = []
    for f in files:
        path_lower = f.path.lower()
        filename = path_lower.rsplit("/", 1)[-1]
        score = _score_match(q, path_lower, filename)
        if score > 0:
            scored.append((f.path, score))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:limit]


def _score_match(q: str, path_lower: str, filename: str) -> float:
    if filename == q:
        return 100.0
    if filename.startswith(q):
        return 90.0
    if q in filename:
        return 75.0
    if path_lower.startswith(q):
        return 60.0
    if q in path_lower:
        return 45.0
    # Subsequence fuzzy match on the filename (e.g. "authtok" -> "auth_token.py")
    it = iter(filename)
    if all(ch in it for ch in q):
        return 20.0
    return 0.0
