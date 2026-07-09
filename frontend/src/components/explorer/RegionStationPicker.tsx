import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Input } from "../common/Input";
import { strings } from "../../lib/strings";
import { RUSSIAN_REGIONS } from "../../lib/russianRegions";
import { searchStations, type StationSearchResult } from "../../api/endpoints/regions";
import { CloseIcon } from "../common/Icons";

export type ExplorerMode = "region" | "station";

interface RegionStationPickerProps {
  mode: ExplorerMode;
  onModeChange: (mode: ExplorerMode) => void;
  selected: string[];
  onChange: (selected: string[]) => void;
}

const SEARCH_DEBOUNCE_MS = 275;

function regionName(id: string): string {
  return RUSSIAN_REGIONS.find((r) => r.id === id)?.name ?? id;
}

export function RegionStationPicker({ mode, onModeChange, selected, onChange }: RegionStationPickerProps) {
  const [draft, setDraft] = useState("");
  const [regionMatches, setRegionMatches] = useState<typeof RUSSIAN_REGIONS>([]);
  const [stationMatches, setStationMatches] = useState<StationSearchResult[]>([]);
  const [stationNamesById, setStationNamesById] = useState<Record<string, string>>({});
  const requestIdRef = useRef(0);

  useEffect(() => {
    setDraft("");
    setRegionMatches([]);
    setStationMatches([]);
  }, [mode]);

  useEffect(() => {
    if (mode !== "region") return;
    const query = draft.trim().toLowerCase();
    if (!query) {
      setRegionMatches([]);
      return;
    }
    setRegionMatches(RUSSIAN_REGIONS.filter((r) => r.name.toLowerCase().includes(query)));
  }, [draft, mode]);

  useEffect(() => {
    if (mode !== "station") return;
    const query = draft.trim();
    if (!query) {
      setStationMatches([]);
      return;
    }
    const myId = ++requestIdRef.current;
    const timer = setTimeout(() => {
      searchStations(query)
        .then((results) => {
          if (requestIdRef.current === myId) setStationMatches(results);
        })
        .catch(() => {
          if (requestIdRef.current === myId) setStationMatches([]);
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [draft, mode]);

  function addRegion(id: string) {
    if (!selected.includes(id)) onChange([...selected, id]);
    setDraft("");
    setRegionMatches([]);
  }

  function addStation(result: StationSearchResult) {
    if (!selected.includes(result.wmo_index)) onChange([...selected, result.wmo_index]);
    setStationNamesById((prev) => ({ ...prev, [result.wmo_index]: result.name }));
    setDraft("");
    setStationMatches([]);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (mode === "region" && regionMatches.length > 0) addRegion(regionMatches[0].id);
    else if (mode === "station" && stationMatches.length > 0) addStation(stationMatches[0]);
  }

  const matches = mode === "region" ? regionMatches : stationMatches;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-1 rounded-sm border border-border p-1 font-mono text-xs uppercase tracking-wide">
        <button
          onClick={() => onModeChange("region")}
          className={`flex-1 rounded-sm px-3 py-1.5 ${mode === "region" ? "bg-accent/15 text-accent" : "text-ink-secondary"}`}
        >
          {strings.explorer.regions}
        </button>
        <button
          onClick={() => onModeChange("station")}
          className={`flex-1 rounded-sm px-3 py-1.5 ${mode === "station" ? "bg-accent/15 text-accent" : "text-ink-secondary"}`}
        >
          {strings.explorer.stations}
        </button>
      </div>

      <div className="relative">
        <Input
          placeholder={mode === "station" ? strings.explorer.searchStation : strings.explorer.searchRegion}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        {matches.length > 0 && (
          <ul className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-sm border border-border bg-surface shadow-lg">
            {mode === "region"
              ? regionMatches.map((r) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      onClick={() => addRegion(r.id)}
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-accent/10"
                    >
                      {r.name}
                    </button>
                  </li>
                ))
              : stationMatches.map((s) => (
                  <li key={s.wmo_index}>
                    <button
                      type="button"
                      onClick={() => addStation(s)}
                      className="block w-full px-3 py-2 text-left text-sm font-mono hover:bg-accent/10"
                    >
                      {s.name} ({s.wmo_index})
                    </button>
                  </li>
                ))}
          </ul>
        )}
      </div>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selected.map((item) => (
            <span
              key={item}
              className="flex items-center gap-1.5 border-l-2 border-accent bg-accent/5 py-1 pl-2.5 pr-2 font-mono text-xs text-accent"
            >
              {mode === "region"
                ? regionName(item)
                : stationNamesById[item]
                  ? `${stationNamesById[item]} (${item})`
                  : item}
              <button onClick={() => onChange(selected.filter((s) => s !== item))} aria-label={strings.common.close}>
                <CloseIcon width={12} height={12} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
