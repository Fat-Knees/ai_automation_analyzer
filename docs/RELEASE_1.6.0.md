# AI Automation Suggester 1.6.0

Release date: 2026-09-05

## Highlights

- **MiniMax support:** Configure a MiniMax API key, global or China endpoint, model, and temperature. The default is `MiniMax-M3`, with `MiniMax-M2.7` also in the catalog. Thanks @octo-patch for PR #178.
- **LiteLLM model sensor:** The sensor now displays the configured model instead of `Unknown Model Key`, without the repeated warning. Thanks @mjacobs for PR #186, fixing #185.
- **Ollama native thinking control:** The existing Disable Think option now sends `think: false`, addressing slow or empty responses from models that ignore the `/no_think` prompt hint (#188). The option remains opt-in.
- **Current provider defaults:** New Google entries use `gemini-3.5-flash` (#184). New Groq entries use `openai/gpt-oss-120b`, with migration warnings for retired Llama IDs and a preview label for `qwen/qwen3.6-27b` (#187).
- **Long local requests:** Setup and options now accept request timeouts above 1800 seconds (#182). The default remains 900 seconds, the minimum remains 10 seconds, and zero does not disable the timeout.
- **Nested YAML wrappers:** Complete Markdown YAML fences inside structured suggestion fields are removed before validation. Newlines and four-space indentation are preserved, including in best-effort recovered JSON. This fixes a reproducible wrapper case investigated for #172.

## Upgrade

1. Update through HACS and restart Home Assistant. No config-entry or stored-history migration is required.
2. Existing model selections are preserved. If an older Google or Groq model returns a model-not-found error, select a current model in the integration options. Groq's Llama retirement affects free/developer accounts, not every enterprise account.
3. For Ollama models affected by #188, enable Disable Think. For long-running local models, set a suitable timeout, such as 7200 seconds for two hours.
4. Existing token budgets are unchanged. For reasoning models or truncated YAML, start with 16000 input tokens and 4096 output tokens, a small entity limit, and no automation/script YAML reading. Higher budgets can increase actual usage and cost. Check the provider's usage dashboard.

## Diagnostics and Follow-Up

- `initializing` is not evidence of an API outage. Startup does not run inference. Run `generate_suggestions` with `all_entities: true` and inspect the action result and provider sensor error attributes. Report #177 still needs an explicit generation result.
- The existing `reasoning_content`/`reasoning` fallback for empty OpenAI-compatible responses is covered by new tests (#127). A completely empty response remains an explicit error.
- Reports #127 and #172 remain open for retesting and raw-response evidence. YAML whose newlines are already missing cannot be safely reconstructed by guessing indentation.
- Claude Pro/Max subscription authentication is not implemented (#179). The Anthropic provider continues to use supported API key authentication.

## Validation

- 89 automated tests pass in clean Python 3.11 and 3.12 environments.
- Repository-wide Ruff checks pass.
- Release checks include Python compilation, dashboard JavaScript syntax, integration JSON/YAML parsing, HACS, and hassfest.
- Provider HTTP behavior is tested with mocks. No live paid-provider inference was performed for this release.

## Contributors

Thanks @octo-patch and @mjacobs for the merged provider contributions, and the issue reporters for their reproduction details.