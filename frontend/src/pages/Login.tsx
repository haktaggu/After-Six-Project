import { useState } from 'react'
import type { PageProps } from '../shared/api/types'
import { ErrorNotice } from '../components/Feedback'

export default function Login({ onSignIn, onSignUp }: PageProps) {
  const [creatingAccount, setCreatingAccount] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  async function submit() {
    if (creatingAccount ? !onSignUp : !onSignIn) return
    setPending(true)
    setError(null)
    try {
      if (creatingAccount) await onSignUp?.({ full_name: name, email, password })
      else await onSignIn?.({ email, password })
    } catch (err) { setError(err) }
    finally { setPending(false) }
  }
  return <section className="login-page">
    <div><h1>OurSJSU</h1><p>Search class sections, check prerequisites, and track open seats.</p></div>
    <form className="login-form" onSubmit={e => { e.preventDefault(); void submit() }}>
      <h2>{creatingAccount ? 'Create an account' : 'Sign in'}</h2>
      {creatingAccount && <label>Name<input name="full_name" autoComplete="name" required maxLength={120} value={name} onChange={e => setName(e.target.value)} /></label>}
      <label>Email<input name="email" type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} /></label>
      <label>Password<input name="password" type="password" autoComplete={creatingAccount ? 'new-password' : 'current-password'} minLength={creatingAccount ? 8 : undefined} maxLength={creatingAccount ? 128 : undefined} required value={password} onChange={e => setPassword(e.target.value)} /></label>
      <div className="actions">
        <button className="primary" disabled={pending || (creatingAccount ? !onSignUp : !onSignIn)}>
          {creatingAccount ? (pending ? 'Creating account…' : 'Create account') : (pending ? 'Signing in…' : 'Sign in')}
        </button>
        <button type="button" disabled={pending} onClick={() => {
          setCreatingAccount(!creatingAccount)
          setPassword('')
          setError(null)
        }}>{creatingAccount ? 'Back to sign in' : 'Create an account'}</button>
      </div>
      <ErrorNotice error={error} />
    </form>
  </section>
}
