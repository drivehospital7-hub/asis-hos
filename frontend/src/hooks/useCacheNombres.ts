import { useState, useEffect, useCallback } from "react";

export interface CacheItem {
  nombre_normalizado: string;
  gender: string;
  gender_short: string;
  probability: number | null;
  count: number | null;
}

export interface CacheAlerts {
  collisions: { normalized_key: string; raw_keys: string[]; genders: (string | null)[]; same_value: boolean }[];
  cleaned_keys: string[];
  invalid_genders: { key: string; gender: string }[];
  recovered_nulls: number;
  total_collisions: number;
}

interface CacheListResponse {
  status: string;
  data?: {
    items: CacheItem[];
    total: number;
    page: number;
    page_size: number;
    by_gender: Record<string, number>;
  };
  errors?: string[];
}

interface CacheAlertsResponse {
  status: string;
  data?: CacheAlerts;
  errors?: string[];
}

export interface UseCacheNombresReturn {
  search: string;
  setSearch: (v: string) => void;
  gender: string;
  setGender: (v: string) => void;
  page: number;
  setPage: (v: number) => void;
  pageSize: number;
  setPageSize: (v: number) => void;
  items: CacheItem[];
  total: number;
  byGender: Record<string, number>;
  alerts: CacheAlerts | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useCacheNombres(): UseCacheNombresReturn {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [gender, setGender] = useState("All");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const [items, setItems] = useState<CacheItem[]>([]);
  const [total, setTotal] = useState(0);
  const [byGender, setByGender] = useState<Record<string, number>>({});
  const [alerts, setAlerts] = useState<CacheAlerts | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(id);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, gender, pageSize]);

  useEffect(() => {
    let cancelled = false;
    async function fetchList() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          gender,
          page: String(page),
          page_size: String(pageSize),
        });
        if (debouncedSearch) params.set("search", debouncedSearch);
        const res = await fetch(`/api/import/cache-list?${params.toString()}`);
        const data: CacheListResponse = await res.json();
        if (cancelled) return;
        if (data.status === "success" && data.data) {
          setItems(data.data.items);
          setTotal(data.data.total);
          setByGender(data.data.by_gender ?? {});
        } else {
          setError(data.errors?.join(", ") ?? "Error al cargar cache");
          setItems([]);
          setTotal(0);
        }
      } catch (err) {
        if (!cancelled) setError("Error de conexión: " + (err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchList();
    return () => {
      cancelled = true;
    };
  }, [debouncedSearch, gender, page, pageSize, tick]);

  useEffect(() => {
    let cancelled = false;
    async function fetchAlerts() {
      try {
        const res = await fetch("/api/import/cache-alerts");
        const data: CacheAlertsResponse = await res.json();
        if (cancelled) return;
        if (data.status === "success" && data.data) setAlerts(data.data);
      } catch {
        // silent — alerts are secondary
      }
    }
    fetchAlerts();
    return () => {
      cancelled = true;
    };
  }, [tick]);

  return {
    search,
    setSearch,
    gender,
    setGender,
    page,
    setPage,
    pageSize,
    setPageSize,
    items,
    total,
    byGender,
    alerts,
    loading,
    error,
    refetch,
  };
}
