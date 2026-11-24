export const navigationPages = ['Dashboard', 'Roadmap', 'Search', 'Watchlist'] as const

export type Page = (typeof navigationPages)[number] | 'Profile' | 'Course History' | 'Add Course' | 'Login'
