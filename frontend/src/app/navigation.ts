export const navigationPages = ['Dashboard', 'Search', 'Roadmap', 'Watchlist'] as const

export type Page = (typeof navigationPages)[number] | 'Login' | 'SignUp'
