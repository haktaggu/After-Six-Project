import { useCallback, useId, useState } from 'react'
import { getPreferences, updatePreferences } from '../shared/api/notifications'
import type { NotificationPreferences as Preferences } from '../shared/api/types'
import { useLoad } from '../shared/hooks/useLoad'
import { ErrorNotice } from './Feedback'
import './NotificationPreferences.css'

export default function NotificationPreferences() {
  const { data, error, loading, reload } = useLoad(useCallback(() => getPreferences(), []))
  const webhookId = useId()
  const [saved, setSaved] = useState<Preferences | null>(null)
  const [webhookDraft, setWebhookDraft] = useState<string | null>(null)
  const [showWebhook, setShowWebhook] = useState(false)
  const [pendingEnabled, setPendingEnabled] = useState<boolean | null>(null)
  const [saveError, setSaveError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const preferences = saved ?? data
  const pending = pendingEnabled !== null
  const enabled = pendingEnabled ?? preferences?.enabled ?? false
  const webhookUrl = webhookDraft ?? preferences?.webhook_url ?? ''

  async function save(nextEnabled: boolean) {
    setPendingEnabled(nextEnabled)
    setSaveError(null)
    setNotice('')
    try {
      const updated = await updatePreferences({ enabled: nextEnabled, webhook_url: webhookUrl || null })
      setSaved(updated)
      setWebhookDraft(null)
      setNotice(updated.enabled ? 'Discord alerts enabled.' : 'Discord preferences saved.')
    } catch (err) {
      setSaveError(err)
    } finally {
      setPendingEnabled(null)
    }
  }

  return (
    <section className="notification-preferences">
      <h2>Discord alerts</h2>
      {loading && <p role="status">Checking alert preferences…</p>}
      <ErrorNotice error={error} />
      <ErrorNotice error={saveError} />
      {preferences && (
        <form
          className="preferences-form"
          onSubmit={e => {
            e.preventDefault()
            void save(enabled)
          }}
        >
          <label htmlFor={webhookId}>Webhook URL</label>
          <div className="webhook-input-group">
            <input
              id={webhookId}
              name="webhook_url"
              type={showWebhook ? 'text' : 'password'}
              placeholder="https://discord.com/api/webhooks/..."
              value={webhookUrl}
              disabled={pending || loading}
              onChange={e => setWebhookDraft(e.target.value)}
            />
            <button
              type="button"
              className="toggle-visibility"
              onClick={() => setShowWebhook(prev => !prev)}
              aria-label={showWebhook ? 'Hide webhook URL' : 'Show webhook URL'}
            >
              {showWebhook ? 'Hide' : 'Show'}
            </button>
          </div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={enabled}
              disabled={pending || loading || (!preferences.available && !enabled)}
              onChange={e => { void save(e.target.checked) }}
            />
            {pending ? 'Saving preference…' : 'Send me Discord alerts'}
          </label>
          <button className="primary small" type="submit" disabled={pending || loading}>
            {pending ? 'Saving…' : 'Save webhook'}
          </button>
          {!preferences.available && <p className="help">Discord notifications are unavailable.</p>}
          <p className="help">
            Paste a Discord webhook URL (from your Discord channel settings &gt; Integrations &gt; Webhooks) to receive seat alerts.
          </p>
        </form>
      )}
      {notice && <p role="status">{notice}</p>}
      {Boolean(error) && <button onClick={reload}>Retry preferences</button>}
    </section>
  )
}
