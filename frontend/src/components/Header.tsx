import { navigationPages } from '../app/navigation'
import type { Page } from '../app/navigation'
import './Header.css'

type HeaderProps = {
  selectedPage: Page
  onNavigate: (page: Page) => void
}

export default function Header({ selectedPage, onNavigate }: HeaderProps) {
  return (
    <header className="site-header">
      <div className="shell header-content">
        <div className="brand-lockup">
          <span className="brand">OurSJSU</span>
          <p className="brand-subtitle">"It's like MySJSU, but we do it <strong>better</strong>"</p>
        </div>
        <nav aria-label="Main navigation">
          {navigationPages.map(name => (
            <button key={name} type="button" aria-current={selectedPage === name ? 'page' : undefined} onClick={() => onNavigate(name)}>{name}</button>
          ))}
        </nav>
        <div className="auth-actions">
          <button className="signup-button" type="button" aria-current={selectedPage === 'SignUp' ? 'page' : undefined} onClick={() => onNavigate('SignUp')}>Sign up</button>
          <button type="button" aria-current={selectedPage === 'Login' ? 'page' : undefined} onClick={() => onNavigate('Login')}>Login</button>
        </div>
      </div>
    </header>
  )
}
