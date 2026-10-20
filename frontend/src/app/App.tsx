import Header from '../components/Header'
import Footer from '../components/Footer'
import type { Page } from './navigation'
import { useState } from 'react'
import { useApiHealth } from '../shared/hooks/useApiHealth'
import { useSession } from '../shared/hooks/useSession'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Search from '../pages/Search'
import Roadmap from '../pages/Roadmap'
import Watchlist from '../pages/Watchlist'

const pages = { Dashboard, Search, Roadmap, Watchlist, Login }

export default function App() {
  useApiHealth()
  const { state, refreshSession, signOut } = useSession()
  const [page, setPage] = useState<Page>('Dashboard')
  const [notice, setNotice] = useState('')
  const [signingOut, setSigningOut] = useState(false)
  const user = state.status === 'authenticated' ? state.session.user : undefined
  const currentPage = user
    ? (page === 'Login' ? 'Dashboard' : page)
    : 'Login'
  const CurrentPage = pages[currentPage]

  function handleSignOut() {
    setNotice('')
    setSigningOut(true)
    void signOut()
      .then(() => setPage('Login'))
      .catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Unable to log out'))
      .finally(() => setSigningOut(false))
  }

  return (
    <>
      <Header selectedPage={currentPage} onNavigate={setPage} user={user} onSignOut={handleSignOut} signingOut={signingOut} />
      <div className="shell">
        <main id="main-content" key={`${user?.id ?? 'anonymous'}:${currentPage}`}>
          {notice && <p role="alert">{notice}</p>}
          {state.status === 'unavailable' && <div role="alert">
            <p>{state.error}</p>
            <button type="button" onClick={() => { void refreshSession() }}>Retry login check</button>
          </div>}
          {state.status === 'loading'
            ? <p role="status">Checking your login…</p>
            : <CurrentPage onNavigate={setPage} onSessionChanged={() => { void refreshSession() }} />}
        </main>
      </div>
      <Footer />
    </>
  )
}
