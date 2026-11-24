import type { ComponentType } from 'react'
import type { PageProps } from '../shared/api/types'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { navigationPages, type Page } from './navigation'
import { useEffect, useRef, useState } from 'react'
import { useApiHealth } from '../shared/hooks/useApiHealth'
import { useSession } from '../shared/hooks/useSession'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import AddCourse from '../pages/AddCourse'
import Search from '../pages/Search'
import Roadmap from '../pages/Roadmap'
import Watchlist from '../pages/Watchlist'
import CourseHistory from '../pages/CourseHistory'
import Profile from '../pages/Profile'

const pages: Record<Page, ComponentType<PageProps>> = {
  Dashboard,
  'Add Course': AddCourse,
  Search,
  Roadmap,
  Watchlist,
  Profile,
  'Course History': CourseHistory,
  Login,
}

const allPages: Page[] = [...navigationPages, 'Profile', 'Course History', 'Add Course']

function pageFromHash(): Page | undefined {
  const hash = window.location.hash.split('?')[0].replace('#', '').toLowerCase().replace(/[-_]/g, ' ')
  return allPages.find(p => p.toLowerCase() === hash)
}

function targetFromHash() {
  return new URLSearchParams(window.location.hash.split('?')[1]).get('target') ?? undefined
}

function pageHash(page: Page, target?: string) {
  return '#' + page.toLowerCase().replace(/\s+/g, '-') + (target ? '?target=' + encodeURIComponent(target) : '')
}

export default function App() {
  useApiHealth()
  const { state, refreshSession, signIn, signUp, signOut } = useSession()
  const [page, setPage] = useState<Page>(() => pageFromHash() ?? 'Dashboard')
  const [target, setTarget] = useState(targetFromHash)
  const [notice, setNotice] = useState('')
  const [signingOut, setSigningOut] = useState(false)
  const user = state.status === 'authenticated' ? state.session.user : undefined
  const currentPage = user
    ? (page === 'Login' ? 'Dashboard' : page)
    : 'Login'
  const CurrentPage = pages[currentPage]
  const mainRef = useRef<HTMLElement>(null)
  const previousPage = useRef(currentPage)
  const previousSessionStatus = useRef(state.status)

  useEffect(() => {
    if (previousPage.current !== currentPage && previousSessionStatus.current !== 'loading') {
      focusMainContent()
    }
    previousPage.current = currentPage
    previousSessionStatus.current = state.status
  }, [currentPage, state.status])

  function focusMainContent() {
    const main = mainRef.current
    if (!main) return
    main.scrollIntoView({ block: 'start' })
    main.focus({ preventScroll: true })
  }

  useEffect(() => {
    const handleHash = () => {
      const requestedPage = pageFromHash()
      if (requestedPage) {
        setPage(requestedPage)
        setTarget(targetFromHash())
      }
      if (state.status === 'anonymous' && window.location.hash !== '#main-content') {
        window.history.replaceState(null, '', '#login')
      }
    }
    window.addEventListener('hashchange', handleHash)
    return () => window.removeEventListener('hashchange', handleHash)
  }, [state.status])

  useEffect(() => {
    if (window.location.hash === '#main-content') return
    if (state.status === 'anonymous') {
      window.history.replaceState(null, '', '#login')
    } else if (state.status === 'authenticated' && window.location.hash === '#login') {
      window.history.replaceState(null, '', pageHash(currentPage, target))
    }
  }, [state.status, currentPage, target])

  function navigate(next: Page, nextTarget?: string) {
    setPage(next)
    setTarget(nextTarget)
    window.location.hash = pageHash(next, nextTarget)
  }

  function handleSignOut() {
    setNotice('')
    setSigningOut(true)
    void signOut()
      .then(() => {
        window.history.replaceState(null, '', '#login')
        setPage('Dashboard')
        setTarget(undefined)
      })
      .catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Unable to log out'))
      .finally(() => setSigningOut(false))
  }

  return (
    <>
      <a className="skip-link" href="#main-content" onClick={event => {
        event.preventDefault()
        focusMainContent()
      }}>Skip to main content</a>
      {user ? (
        <Header selectedPage={currentPage} onNavigate={navigate} user={user} onSignOut={handleSignOut} signingOut={signingOut} />
      ) : (
        <div className="top-accent-line" />
      )}
      <div className="shell">
        <main id="main-content" ref={mainRef} tabIndex={-1}>
          {notice && <p role="alert">{notice}</p>}
          {state.status === 'unavailable' && <div role="alert">
            <p>{state.error}</p>
            <button type="button" onClick={() => { void refreshSession() }}>Retry login check</button>
          </div>}
          {state.status === 'loading'
            ? <p role="status">Checking your login…</p>
            : <CurrentPage key={`${user?.id ?? 'anonymous'}:${currentPage}:${target ?? ''}`} target={target} onSignIn={signIn} onSignUp={signUp} onNavigate={navigate} onSessionChanged={() => { void refreshSession() }} />}
        </main>
      </div>
      <Footer />
    </>
  )
}
