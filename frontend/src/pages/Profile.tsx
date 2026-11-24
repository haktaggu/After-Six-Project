import { useCallback, useId, useState } from 'react'
import { getProfile, updateProfile } from '../shared/api/accounts'
import { listMajors } from '../shared/api/planning'
import { allPages } from '../shared/api/lookups'
import { useLoad } from '../shared/hooks/useLoad'
import type { PageProps, ProfileResponse } from '../shared/api/types'
import { ErrorNotice } from '../components/Feedback'
import NotificationPreferences from '../components/NotificationPreferences'
import './Profile.css'

export default function Profile({ onNavigate }: PageProps) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const recommendationHintId = useId()

  const load = useCallback(async () => {
    const [profile, majors] = await Promise.all([
      getProfile(),
      allPages(listMajors),
    ])
    return { profile, majors }
  }, [])

  const { data, error: loadError, loading, reload } = useLoad(load)

  async function saveProfile(form: HTMLFormElement) {
    setSaving(true)
    setError(null)
    setNotice('')
    const fields = new FormData(form)
    try {
      await updateProfile({
        major_code: String(fields.get('major_code') || '') || null,
        recommendation_limit: Number(fields.get('recommendation_limit')),
      })
      setNotice('Profile saved.')
      reload()
    } catch (err) {
      setError(err)
    } finally {
      setSaving(false)
    }
  }

  const profile: ProfileResponse | undefined = data?.profile

  return (
    <section className="profile-page">
      <div className="page-heading">
        <div>
          <h1>Profile</h1>
        </div>
        <div className="profile-actions">
          <button onClick={() => onNavigate?.('Course History')}>Course history</button>
          <button disabled={loading} onClick={reload}>Refresh</button>
        </div>
      </div>
      <ErrorNotice error={loadError} />
      {loading && <p role="status">Loading profile…</p>}
      {profile && data && (
        <div className="profile-grid">
          <section className="profile-section">
            <h2>{profile.user.full_name}</h2>
            <p>{profile.user.email}</p>
            <form
              key={JSON.stringify(profile.profile)}
              onSubmit={e => {
                e.preventDefault()
                void saveProfile(e.currentTarget)
              }}
            >
              <div className="form-grid">
                <label>
                  Major
                  <select name="major_code" defaultValue={profile.profile.major_code ?? ''} disabled={saving}>
                    <option value="">Not selected</option>
                    {data.majors.map(m => (
                      <option key={m.major_code} value={m.major_code}>
                        {m.title} {m.degree_type}
                      </option>
                    ))}
                  </select>
                </label>
                <div>
                  <label>
                    Number of course suggestions
                    <select
                      name="recommendation_limit"
                      defaultValue={profile.profile.recommendation_limit}
                      aria-describedby={recommendationHintId}
                      disabled={saving}
                    >
                      {[1, 2, 3, 4, 5].map(limit => <option key={limit} value={limit}>{limit}</option>)}
                    </select>
                  </label>
                  <p className="help" id={recommendationHintId}>Sets the target for Dashboard and Roadmap.</p>
                </div>
              </div>
              <button className="primary" disabled={saving}>
                {saving ? 'Saving…' : 'Save profile'}
              </button>
              <ErrorNotice error={error} />
              {notice && <p className="notice" role="status">{notice}</p>}
            </form>
          </section>

          <section className="profile-settings-card">
            <NotificationPreferences />
          </section>
        </div>
      )}
    </section>
  )
}
