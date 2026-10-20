import { navigationPages } from '../app/navigation'
import type { Page } from '../app/navigation'
import type { User } from '../shared/api/types'
import './Header.css'

type HeaderProps = {
  selectedPage: Page
  onNavigate: (page: Page) => void
  user?: User
  onSignOut?: () => void
  signingOut?: boolean
}

export default function Header({ selectedPage, onNavigate, user, onSignOut, signingOut = false }: HeaderProps) {
  return (
    <header className="site-header">
      <div className="shell header-content">
        <div className="brand-lockup">
          <span className="brand">OurSJSU</span>
          <p className="brand-subtitle">"It's like MySJSU, but we do it <strong>better</strong>"</p>
        </div>
        <nav aria-label="Main navigation">
          {navigationPages.map(name => (
            <button key={name} type="button" disabled={!user || signingOut} aria-current={selectedPage === name ? 'page' : undefined} onClick={() => onNavigate(name)}>{name}</button>
          ))}
        </nav>
        <div className="auth-actions">
          {user ? (
            <button type="button" disabled={signingOut || !onSignOut} onClick={onSignOut}>{signingOut ? 'Logging out…' : 'Logout'}</button>
          ) : (
            <button type="button" disabled aria-current={selectedPage === 'Login' ? 'page' : undefined}>Sign in</button>
          )}
        </div>
      </div>
    </header>
  )
}
