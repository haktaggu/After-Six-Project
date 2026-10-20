import { useState } from 'react'
import type { NotificationPreferences as Preferences, PreferencesUpdate } from '../shared/api/types'

// - shared/api/notifications.getPreferences() returns {enabled: boolean, available: boolean}.
// - Render one Discord toggle. If unavailable, explain that the backend destination is missing;
//   allow turning alerts off, but do not offer a destination field or enable unavailable alerts.
async function loadPreferences(): Promise<Preferences> {
  throw new Error('loadPreferences is not implemented')
}

// - shared/api/notifications.updatePreferences({enabled}) returns saved {enabled,available}.
// - Keep the old toggle state on failure; show pending while saving and explain 503
//   CHANNEL_UNAVAILABLE. Refresh availability after an error; never show a failed save as success.
async function savePreferences(body: PreferencesUpdate): Promise<Preferences> {
  void body
  throw new Error('savePreferences is not implemented')
}

const actions = { loadPreferences, savePreferences }

export default function NotificationPreferences() {
  const [notice, setNotice] = useState('')
  return <section>
    <h2>Discord alerts</h2>
    <button type="button" disabled onClick={() => {
      void actions.loadPreferences().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Request failed'))
    }}>Refresh</button>
    {notice && <p role="alert">{notice}</p>}
  </section>
}
