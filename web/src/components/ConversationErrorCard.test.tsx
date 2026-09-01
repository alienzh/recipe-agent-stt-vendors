import { describe, expect, test } from 'bun:test'
import { renderToStaticMarkup } from 'react-dom/server'

import { ConversationErrorCard } from './ConversationErrorCard'

describe('ConversationErrorCard', () => {
  test('shows the original message for an unrecognized engine error', () => {
    const html = renderToStaticMarkup(
      <ConversationErrorCard
        issue={{
          id: 'asr-error',
          source: 'agent',
          agentUserId: '38485837',
          code: 1000,
          message: 'asr: models/gemini-3.7-transcribe-live is not supported for bidiGenerateContent',
          timestamp: 0,
        }}
      />,
    )

    expect(html).toContain('asr: models/gemini-3.7-transcribe-live is not supported for bidiGenerateContent')
  })
})
