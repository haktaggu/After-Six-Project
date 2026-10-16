import Header from '../components/Header'
import Footer from '../components/Footer'
import type { Page } from './navigation'
import { useState } from 'react'
import { useApiHealth } from '../shared/hooks/useApiHealth'
import Login from '../pages/Login'
import SignUp from '../pages/SignUp'
import Dashboard from '../pages/Dashboard'
import Search from '../pages/Search'
import Roadmap from '../pages/Roadmap'
import Watchlist from '../pages/Watchlist'

const pages = { Dashboard, Search, Roadmap, Watchlist, Login, SignUp }

export default function App() {
  useApiHealth()
  const [page, setPage] = useState<Page>('Dashboard')
  const CurrentPage = pages[page]

  return (
    <>
      <Header selectedPage={page} onNavigate={setPage} />
      <div className="shell">
        <main id="main-content" key={page}><CurrentPage /></main>
      </div>
      <Footer />
    </>
  )
}
