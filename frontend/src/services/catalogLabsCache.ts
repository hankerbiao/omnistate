import { api } from './api';
import type { CatalogLab } from '../types';

type ListCatalogLabsParams = { active_only?: boolean };

function cacheKey(params: ListCatalogLabsParams): string {
  return params.active_only ? 'active_only' : 'all';
}

const resolved = new Map<string, CatalogLab[]>();
const inflight = new Map<string, Promise<CatalogLab[]>>();

/** Session-scoped cache; dedupes concurrent and repeat GET /catalog/labs calls. */
export async function getCatalogLabs(
  params: ListCatalogLabsParams = {},
): Promise<CatalogLab[]> {
  const key = cacheKey(params);
  const hit = resolved.get(key);
  if (hit) return hit;

  let pending = inflight.get(key);
  if (!pending) {
    pending = api.listCatalogLabs(params).then(resp => {
      const items = resp.data ?? [];
      resolved.set(key, items);
      inflight.delete(key);
      return items;
    });
    inflight.set(key, pending);
  }
  return pending;
}

export function invalidateCatalogLabsCache(): void {
  resolved.clear();
  inflight.clear();
}
