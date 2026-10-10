import { test, expect } from '@playwright/test';

// Browser UI tests use intercepted, explicitly fake backend HTTP responses.
// They are not evidence of an OpenAI account, MT5 installation or live prices.
test.beforeEach(async ({ page }) => {
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const fake = path.endsWith('/health')
      ? { ok: true, trading_enabled: false }
      : path.endsWith('/providers')
      ? { providers: ['openai', 'anthropic', 'gemini'].map(provider => ({provider, configured: false})) }
      : path.endsWith('/chat')
      ? { answer: 'Browser test response from a simulated provider — not live.' }
      : path.endsWith('/terminals')
      ? { terminals: [], selected: '' }
      : path.endsWith('/terminal')
      ? { detail: 'No real MT5 terminal in browser test' }
      : path.endsWith('/providers/openai/test')
      ? { detail: 'No real provider key configured in browser test' }
      : { detail: 'Test-only endpoint is not available' };
    const status = 'detail' in fake ? 503 : 200;
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(fake) });
  });
  await page.goto('/');
  await expect(page.getByRole('heading', {name:'What would you like to do?'})).toBeVisible();
});

test('empty chat is a compact workspace with anchored composer', async ({page}) => {
  const composer = page.getByRole('textbox', {name:'Message to AI Trading Agent'});
  await expect(composer).toBeVisible();
  const geometry = await page.evaluate(() => ({
    docHeight: document.documentElement.scrollHeight,
    viewport: window.innerHeight,
    composeBottom: document.querySelector('.composer')?.getBoundingClientRect().bottom,
  }));
  expect(geometry.docHeight).toBeLessThanOrEqual(geometry.viewport + 2);
  expect(geometry.composeBottom).toBeGreaterThan(geometry.viewport - 95);
  await page.screenshot({path:'test-results/empty-chat.png',fullPage:false});
});

test('model/provider connection dialog can be opened and closed by keyboard', async ({page}) => {
  await page.getByRole('button', {name:'AI Provider'}).click();
  await page.getByRole('menuitem', {name:'Connections and API keys'}).click();
  const dialog=page.getByRole('dialog', {name:'AI connections'});
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', {name:/OpenAI/})).toBeVisible();
  await expect(dialog.getByText('Not connected').first()).toBeVisible();
  await page.screenshot({path:'test-results/providers.png',fullPage:false});
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
});

test('chat submission shows a labelled simulated result and new chat clears it', async ({page}) => {
  await page.getByRole('textbox', {name:'Message to AI Trading Agent'}).fill('Explain the available tools');
  await page.getByRole('button', {name:'Send message'}).click();
  await expect(page.getByText('Browser test response from a simulated provider — not live.')).toBeVisible();
  await page.screenshot({path:'test-results/populated-chat.png',fullPage:false});
  await page.getByRole('button', {name:'New conversation'}).click();
  await expect(page.getByRole('heading', {name:'What would you like to do?'})).toBeVisible();
});

test('MT5 discovery accurately reports missing installation', async ({page}) => {
  await page.getByRole('button', {name:'MetaTrader connections'}).click();
  const dialog=page.getByRole('dialog',{name:'MetaTrader terminals'});
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('No MT5 installation discovered')).toBeVisible();
});

test('appearance dialog offers working theme selection', async ({page}) => {
  await page.getByRole('button',{name:'View'}).click();
  await page.getByRole('menuitem',{name:'Appearance and accessibility'}).click();
  await page.getByRole('button',{name:'Dark'}).click();
  await expect(page.getByRole('button',{name:'Dark'})).toHaveAttribute('aria-pressed','true');
  await page.screenshot({path:'test-results/dark-theme.png',fullPage:false});
});
