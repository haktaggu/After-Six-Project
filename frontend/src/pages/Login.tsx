import { useState } from 'react'
import type { LoginRequest, PageProps, SessionResponse } from '../shared/api/types'

// - Use the seeded demo account email/password; shared/api/accounts.login(body)->SessionResponse sets the
//   cookie. Obtain CSRF through shared/api/accounts.fetchCsrf() first; pass its csrf_token
//   to shared/api/client.setCsrfToken before login. Save the login response's csrf_token too.
// - Startup creates demo@oursjsu.test with password oursjsu-demo-password and major CMPE.
// - Use PageProps.onSessionChanged after login, then onNavigate("Dashboard"). Show field errors
//   and generic failures without clearing the entered email.
// - Check invalid credentials, expiry and a provider/database outage. Never ask for university
//   credentials.
// - LoginRequest: {email: string, password: string}.
// - SessionResponse: {user: User, csrf_token: string, expires_at: string}.
async function handleSubmit(body: LoginRequest): Promise<SessionResponse> {
  void [body]
  throw new Error('handleSubmit is not implemented')
}

const actions = { handleSubmit }

export default function Login(props: PageProps = {}) {
  const [notice, setNotice] = useState('')
  return (
    <section>
      <h1>Login</h1>
      <p>Use the demo student account.</p>
      <form onSubmit={event => {
        event.preventDefault()
        const fields = new FormData(event.currentTarget)
        void actions.handleSubmit({ email: String(fields.get('email') ?? ''), password: String(fields.get('password') ?? '') })
          .then(() => { props.onSessionChanged?.(); props.onNavigate?.('Dashboard') })
          .catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Request failed'))
      }}>
        <label>Email <input name="email" type="email" disabled /></label>
        <label>Password <input name="password" type="password" disabled /></label>
        <button type="submit" disabled>Login</button>
      </form>
      {notice && <p role="alert">{notice}</p>}
    </section>
  )
}
