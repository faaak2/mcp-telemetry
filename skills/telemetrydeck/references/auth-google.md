# Capture a TelemetryDeck bearer token via Google sign-in

Use this flow when `mcp__telemetrydeck__login(email, password)` returned 401 or a "no password set" error — the account is Google-signup-only.

## 1. Check that chrome-devtools MCP is installed

Look for tools with the prefix `mcp__chrome-devtools__` (e.g. `mcp__chrome-devtools__new_page`).

- **Not present** → tell the user to run, in their terminal:

  ```bash
  claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest
  ```

  Then restart Claude Code and re-ask the original question. The skill will fire again.

- **Present** → continue.

## 2. Open the TelemetryDeck dashboard

Call `mcp__chrome-devtools__new_page("https://dashboard.telemetrydeck.com")`. This opens a browser tab the user can interact with.

## 3. Have the user sign in

Tell the user: "Sign in via Google in the browser tab that just opened, then say 'done'."

Wait for their confirmation. Don't proceed until they confirm sign-in is complete.

## 4. Capture the bearer token from network traffic

Once the dashboard loads after sign-in, it makes authenticated API calls to `api.telemetrydeck.com`. Each carries an `Authorization: Bearer <token>` header. Extract the token:

1. Call `mcp__chrome-devtools__list_network_requests()` to list recent requests.
2. Find any request whose URL is on `api.telemetrydeck.com`.
3. Call `mcp__chrome-devtools__get_network_request(<id-of-that-request>)` to get full details, including headers.
4. Read the `Authorization` header — looks like `Bearer eyJhbGciOi...`. Take the part after `Bearer ` — that's the token.

If no `api.telemetrydeck.com` requests appear in the list, ask the user to click around the dashboard (e.g. open one of their apps) so the page makes API calls, then re-run step 1.

## 5. Verify the token works

Call `mcp__telemetrydeck__list_apps()` (no token needed) and then a small `mcp__telemetrydeck__run_query(...)` using the captured token. If `run_query` returns data, the token is valid. If it returns 401, the capture went wrong — repeat from step 4.

## 6. Hand back to the query flow

The token is now valid for this conversation. Reply only with "Logged in ✓" — do NOT echo the token back to the user. Proceed with their original query.

## Security note

- Never write the token to a file, commit, or visible message.
- Never paste it into any output to the user beyond a brief confirmation.
- On 401 from any later query, restart this capture flow.
