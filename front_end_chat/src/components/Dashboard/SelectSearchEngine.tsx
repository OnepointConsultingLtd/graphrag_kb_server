import { useShallow } from "zustand/shallow";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import { SearchType } from "../../model/projectCategory";

export default function SelectSearchEngine() {
  const { searchType, setSearchType } = useProjectSelectionStore(
    useShallow((state) => ({
      searchType: state.searchType,
      setSearchType: state.setSearchType,
    })),
  );

  return (
    <div>
      <select
        className="select select-primary w-full bg-gray-700"
        value={searchType}
        onChange={(e) => setSearchType(e.target.value as SearchType)}
      >
        {Object.values(SearchType).map((value, index) => (
          <option key={`${index}-${value}`} value={value}>
            {value}
          </option>
        ))}
      </select>
      <p className="text-xs text-gray-500 mt-1">
        The type of engine used to run the RAG system.
      </p>
    </div>
  );
}
