import { useCallback, useState } from 'react'
import { getPreferences, updatePreferences } from '../shared/api/notifications'
import { useLoad } from '../shared/hooks/useLoad'
import { ErrorNotice } from './Feedback'

export default function NotificationPreferences() {
  const { data, error, loading, reload } = useLoad(useCallback(() => getPreferences(), []))
  const [pending, setPending] = useState(false)
  const [saveError, setSaveError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')

  async function change(enabled: boolean) {
    setPending(true); setSaveError(null); setNotice('')
    try {
      await updatePreferences({ enabled });
      setNotice(enabled ? 'Discord alerts enabled.' : 'Discord alerts disabled.')
    }
    catch (err) { setSaveError(err) }
    finally { setPending(false); reload() }
  }

  return <section className="notification-preferences"><h2>Discord alerts</h2>
    {loading && <p role="status">Checking alert preferences…</p>}
    <ErrorNotice error={error} />
    <ErrorNotice error={saveError} />

    {data && <>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={data.enabled}
          /* 既然确认后端没配置，如果 data.available 为 false，就直接禁用 */
          disabled={pending || loading || !data.available}
          onChange={e => { void change(e.target.checked) }}
        />
        {pending ? 'Saving preference…' : 'Send me Discord alerts'}
      </label>

      {!data.available && (
        <p className="help">
          Discord alerts are not configured by the server administrator yet. You can still save watches.
        </p>
      )}
    </>}

    {notice && <p role="status">{notice}</p>}
    {Boolean(error) && <button onClick={reload}>Retry preferences</button>}
  </section>
}