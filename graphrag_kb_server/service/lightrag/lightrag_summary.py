from pathlib import Path
import json

from graphrag_kb_server.utils.cache import GenericProjectSimpleCache

lightrag_summary_cache = GenericProjectSimpleCache[dict](timeout=3600 * 24)
SUMMARY_FILE_NAME = "onepoint_lightrag_summary.json"


def get_summary(project_dir: Path, file_path: str) -> str | None:
    cached_data = lightrag_summary_cache.get(project_dir)
    if cached_data is not None:
        return cached_data.get(file_path)
    summary_file_path = project_dir / SUMMARY_FILE_NAME
    if summary_file_path.exists():
        with open(summary_file_path, "r", encoding="utf-8") as f:
            summary_dict = json.load(f)
            return summary_dict.get(file_path)
    kv_store_doc_status_path = project_dir / "lightrag/kv_store_doc_status.json"
    if not kv_store_doc_status_path.exists():
        return None
    doc_summary_dict = {}
    with open(kv_store_doc_status_path, "r", encoding="utf-8") as f:
        kv_store_doc_status = json.load(f)
        for _, v in kv_store_doc_status.items():
            doc_summary_dict[v["file_path"]] = v["content_summary"]
    lightrag_summary_cache.set(project_dir, doc_summary_dict)

    with open(summary_file_path, "w", encoding="utf-8") as f:
        json.dump(doc_summary_dict, f, indent=4)
    return doc_summary_dict.get(file_path)


if __name__ == "__main__":
    project_dir = Path(__file__).parent.parent.parent.parent / "data"
    assert project_dir.exists()
    summary = get_summary(
        project_dir,
        "/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full/input/clustre/Articles and PoVs/AI_or_Die_-_Generic.txt",
    )
    assert isinstance(summary, str)
    assert summary is not None, "Cannot find summary"
