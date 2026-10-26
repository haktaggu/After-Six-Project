import type { Page, PaginationQuery } from './types'

export async function allPages<T>(fetchPage: (query: PaginationQuery) => Promise<Page<T>>): Promise<T[]> {
  const items: T[] = []
  let total = 1
  while (items.length < total) {
    const page = await fetchPage({ limit: 100, offset: items.length })
    items.push(...page.items)
    total = page.total
    if (!page.items.length) break
  }
  return items
}
