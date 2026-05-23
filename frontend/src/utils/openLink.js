/**
 * Open an external URL trying to honor the user's preferred browser on iOS.
 *
 * Background: on iOS, when a webpage calls `window.open('https://...', '_blank')`,
 * the OS frequently routes the navigation through an in-app SFSafariViewController
 * that LOOKS like Safari and ignores the user's "Default Browser" setting. This
 * is especially noticeable when the dashboard is opened from a PWA shortcut.
 *
 * Workaround: Chrome for iOS registers the custom schemes `googlechrome://` and
 * `googlechromes://` (https). Navigating to those schemes opens Chrome directly,
 * bypassing the in-app sheet entirely.
 *
 * Safety net: if Chrome is not installed, iOS just refuses the navigation —
 * we set a short timer to retry with the original https URL so the user still
 * lands somewhere. The timer fires only if the page is still visible after
 * the chrome attempt (i.e., Chrome didn't take over).
 *
 * Docs: https://developer.chrome.com/docs/multidevice/ios/links/
 */

function isIOS() {
  if (typeof navigator === 'undefined') return false
  // iPadOS 13+ reports as Mac in UA; check touch points as fallback.
  const ua = navigator.userAgent || ''
  if (/iPad|iPhone|iPod/.test(ua)) return true
  return navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1
}

function toChromeScheme(url) {
  if (url.startsWith('https://')) return 'googlechromes://' + url.slice(8)
  if (url.startsWith('http://')) return 'googlechrome://' + url.slice(7)
  return null
}

/**
 * Hostnames whose native app provides a strictly better experience than a browser
 * tab. When the URL matches one of these, we DO NOT convert to the Chrome scheme —
 * we let iOS Universal Links route the navigation to the installed app (and fall
 * back to SFSafariViewController if not installed; acceptable trade-off since
 * these sites all work fine in a browser too).
 *
 * Why hardcoded list and not heuristic: apps that register Universal Links are a
 * closed, slow-changing set. A hardcoded list is explicit, reviewable, and avoids
 * surprises (e.g., a random link to a personal blog suddenly opening a random app).
 */
const APP_PREFERRED_HOSTS = new Set([
  // YouTube — opens YouTube app (video playback in native player)
  'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be', 'music.youtube.com',
  // Spotify — opens Spotify app (audio playback, podcast episodes)
  'open.spotify.com',
  // Apple Podcasts — opens Podcasts app
  'podcasts.apple.com',
  // X/Twitter — opens X app (better thread UX, account context)
  'twitter.com', 'www.twitter.com', 'x.com', 'www.x.com', 'mobile.twitter.com',
  // WhatsApp — opens WhatsApp app (messaging, group invites, shortlinks)
  'wa.me', 'whatsapp.com', 'www.whatsapp.com', 'chat.whatsapp.com', 'api.whatsapp.com',
  // Things 3 — defensivo: usuario USA o app via deeplink `things:///add?...`
  // (que ja passa direto pelo fallback non-http, sem tocar no Chrome scheme),
  // mas adicionamos o dominio web por completude se algum link culturedcode
  // aparecer num card.
  'culturedcode.com', 'www.culturedcode.com',
])

// NOTA: deeplinks de app (`things://`, `whatsapp://`, `spotify://`, `tg://`,
// `mailto:`, `tel:`) NAO precisam estar em APP_PREFERRED_HOSTS — eles ja
// passam direto pelo `if (!chromeUrl)` fallback no openInBrowser, porque
// `toChromeScheme` so converte http(s) e retorna null pra outros esquemas.
// O iOS faz o roteamento pro app correspondente automaticamente.

function shouldPreferNativeApp(url) {
  try {
    return APP_PREFERRED_HOSTS.has(new URL(url).hostname.toLowerCase())
  } catch {
    return false
  }
}

/**
 * Open an external URL in the user's preferred browser when possible.
 *
 * @param {string} url - The URL to open.
 */
export function openInBrowser(url) {
  if (!url || typeof url !== 'string') return

  // Non-iOS: standard behavior is fine — default browser already wins.
  if (!isIOS()) {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }

  // Exception: domains with strong native apps (YouTube, Spotify, X, Apple
  // Podcasts) — let iOS Universal Links route to the installed app. If the app
  // isn't installed, iOS falls back to its in-app browser. We don't force
  // Chrome here because the native app experience is meaningfully better
  // (native video player, audio backgrounding, threaded UX, etc).
  if (shouldPreferNativeApp(url)) {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }

  const chromeUrl = toChromeScheme(url)
  if (!chromeUrl) {
    // Non-http(s) URL (mailto:, tel:, etc.) — pass through.
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }

  // Try Chrome first. If Chrome isn't installed, iOS silently refuses and
  // the page stays visible; we then fall back to the original URL so the
  // user still navigates somewhere.
  const start = Date.now()
  window.location.href = chromeUrl

  setTimeout(() => {
    // Only fall back if we're still here AND the page didn't go to background
    // (Chrome opening would have backgrounded this tab).
    if (Date.now() - start < 1500 && !document.hidden) {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }, 600)
}

/**
 * Click handler for `<a target="_blank" rel="noopener">` elements that need
 * to honor the user's preferred browser on iOS without losing native browser
 * behavior on other platforms (Ctrl+Click, middle-click, etc).
 *
 * Usage in a template:
 *   <a :href="url" target="_blank" rel="noopener noreferrer"
 *      @click.stop="handleExternalLinkClick($event, url)">
 *
 * On iOS: prevents the default <a> navigation (which would trigger
 * SFSafariViewController) and routes through openInBrowser to use Chrome.
 *
 * On other platforms: no-op — the browser's native target="_blank" handling
 * runs (which already respects modifier-key clicks and the default browser).
 *
 * @param {MouseEvent} event - The click event from the <a> element.
 * @param {string} url - The destination URL.
 */
export function handleExternalLinkClick(event, url) {
  if (!url) return
  if (!isIOS()) return // let the browser's native handling run
  if (event) event.preventDefault()
  openInBrowser(url)
}
