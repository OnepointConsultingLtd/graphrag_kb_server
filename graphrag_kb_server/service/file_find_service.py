import re
import copy
from pathlib import Path

from graphrag_kb_server.logger import logger
from graphrag_kb_server.utils.cache import GenericProjectSimpleCache


ORIGINAL_INPUT_FOLDER = "original_input"
INPUT_FOLDER = "input"

file_conversion_cache = GenericProjectSimpleCache[dict[Path, Path]]()


def convert_file_name(file: Path) -> str:
    return re.sub(r"\s+", "_", file.stem)


def create_conversion_map(project_dir: Path) -> dict[str, str]:
    original_file_path = project_dir / ORIGINAL_INPUT_FOLDER
    if not original_file_path.exists():
        return {}
    conversion_map = {}
    for original_file in original_file_path.glob("**/*"):
        if (
            original_file.is_file()
            and original_file.suffix != ".txt"
            and original_file.suffix != ".md"
        ):
            copy_path = copy.copy(original_file)
            copy_path = copy_path.parent / f"{convert_file_name(copy_path)}.txt"
            file_splits = (
                copy_path.as_posix().replace(project_dir.as_posix(), "").split("/")
            )
            file_splits[1] = INPUT_FOLDER
            copy_path = project_dir / Path(*file_splits)
            if copy_path.exists():
                conversion_map[copy_path.as_posix()] = original_file
            else:
                logger.warning(f"File {copy_path} does not exist")
    return conversion_map


def find_original_file(project_dir: Path, file_path: Path) -> Path | None:
    conversion_map = file_conversion_cache.get(project_dir)
    if conversion_map is None:
        conversion_map = create_conversion_map(project_dir)
        file_conversion_cache.set(project_dir, conversion_map)

    return conversion_map.get(file_path.as_posix())


if __name__ == "__main__":
    project_dir = Path("C:/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full")
    sample_file = Path(
        "C:/var/graphrag/tennants/gil_fernandes/lightrag/clustre_full/input/clustre/Articles and PoVs"
    )
    find_original_file(project_dir, sample_file)
